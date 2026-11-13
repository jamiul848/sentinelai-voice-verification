"""Sentinel Voice - API Rate Limiting & Abuse Defense Engine.

Features:
1. Multi-backend architecture: Redis sliding-window for distributed production,
   thread-safe in-memory sliding-window for local development.
2. Anti-spoofing client IP resolution with trusted reverse proxy traversal.
3. Configurable rate limits driven dynamically by application settings and environment variables.
4. FastAPI dependency injection providing HTTP 429 Too Many Requests and Retry-After headers.
5. Zero storage of passwords, tokens, or biometric vectors in rate limit cache keys.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
import logging
import math
import re
import threading
import time
from typing import Callable, Dict, List, Literal, Optional, Tuple, Union
import uuid

from fastapi import HTTPException, Request, Response, status

from sentinelai.auth.exceptions import AuthError
from sentinelai.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Duration conversion mapping in seconds
TIME_UNIT_FACTORS = {
    "s": 1,
    "sec": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
}

RATE_LIMIT_REGEX = re.compile(r"^(\d+)\s*/\s*(\d*)\s*([a-zA-Z]+)$")


class RateLimitExceededError(AuthError):
    """Raised when an API endpoint rate limit quota has been exhausted."""

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        retry_after: int = 60,
    ) -> None:
        super().__init__(message=message, error_code="RATE_LIMIT_EXCEEDED")
        self.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        self.retry_after = retry_after


def parse_rate_limit(expression: str) -> Tuple[int, int]:
    """Parse limit expression (e.g. '5/hour', '5/15minute', '100/minute').

    Args:
        expression: String limit expression.

    Returns:
        Tuple of (max_requests: int, window_seconds: int).

    Raises:
        ValueError: If expression format is malformed or time unit unknown.
    """
    clean_expr = expression.strip().lower()
    match = RATE_LIMIT_REGEX.match(clean_expr)
    if not match:
        raise ValueError(f"Malformed rate limit expression '{expression}'. Expected format like '5/hour' or '10/15min'.")

    count_str, multiplier_str, unit_str = match.groups()
    max_requests = int(count_str)
    multiplier = int(multiplier_str) if multiplier_str else 1

    unit_factor = TIME_UNIT_FACTORS.get(unit_str)
    if not unit_factor:
        raise ValueError(f"Unknown time unit '{unit_str}' in rate limit expression '{expression}'.")

    window_seconds = multiplier * unit_factor
    return max_requests, window_seconds


def get_trusted_client_ip(request: Request, trusted_proxies: Optional[List[str]] = None) -> str:
    """Extract authenticated client IP address, defending against header spoofing.

    If request originates from a configured trusted proxy, parses X-Forwarded-For
    from right to left, selecting the first non-trusted upstream IP address.

    Args:
        request: FastAPI Request instance.
        trusted_proxies: List of trusted reverse proxy IP strings.

    Returns:
        Resolved client IP address string.
    """
    remote_ip = request.client.host if request.client else "127.0.0.1"
    proxies = set(trusted_proxies or get_settings().trusted_proxies)

    # If the direct peer is not a trusted proxy, ignore X-Forwarded-For entirely
    if remote_ip not in proxies:
        return remote_ip

    xff_header = request.headers.get("x-forwarded-for")
    if not xff_header:
        return remote_ip

    raw_ips = [ip.strip() for ip in xff_header.split(",") if ip.strip()]
    if not raw_ips:
        return remote_ip

    # Traverse from right to left through the proxy chain
    for ip in reversed(raw_ips):
        if ip not in proxies:
            return ip

    return raw_ips[0]


class RateLimiterBackend(ABC):
    """Abstract interface for rate limiter storage backends."""

    @abstractmethod
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """Check quota and record request.

        Returns:
            Tuple of (is_allowed: bool, remaining_requests: int, retry_after_seconds: int).
        """
        pass

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset quota for key."""
        pass


class InMemoryRateLimiterBackend(RateLimiterBackend):
    """Thread-safe, sliding-window in-memory rate limiter backend for local environments.

    NOTE: Applies strictly per-worker process. Does not provide distributed protection
    across multi-worker or multi-container deployments; use Redis in production.
    """

    def __init__(self) -> None:
        self._store: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._store[key]
            # Prune timestamps outside current sliding window
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_requests:
                oldest_timestamp = valid_timestamps[0]
                retry_after = max(1, int(math.ceil(oldest_timestamp + window_seconds - now)))
                self._store[key] = valid_timestamps
                return False, 0, retry_after

            # Allow request and record timestamp
            valid_timestamps.append(now)
            self._store[key] = valid_timestamps
            remaining = max(0, max_requests - len(valid_timestamps))
            return True, remaining, 0

    async def reset(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all stored state (primarily for automated testing)."""
        with self._lock:
            self._store.clear()


class RedisRateLimiterBackend(RateLimiterBackend):
    """Distributed sliding-window rate limiter powered by Redis sorted sets (ZSET)."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._fallback = InMemoryRateLimiterBackend()
        self._client = None
        self._init_error_logged = False

    async def _get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(
                    self.redis_url,
                    socket_connect_timeout=2.0,
                    decode_responses=True,
                )
            except Exception as err:
                if not self._init_error_logged:
                    logger.warning("Redis rate limiter client initialization failed: %s. Using in-memory fallback.", err)
                    self._init_error_logged = True
                return None
        return self._client

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        client = await self._get_client()
        if client is None:
            return await self._fallback.check_rate_limit(key, max_requests, window_seconds)

        now = time.time()
        cutoff = now - window_seconds
        redis_key = f"sentinel:rl:{key}"

        try:
            # Atomic sliding window pipeline
            async with client.pipeline(transaction=True) as pipe:
                # 1. Prune expired entries
                pipe.zremrangebyscore(redis_key, 0, cutoff)
                # 2. Count current entries in window
                pipe.zcard(redis_key)
                # 3. Add current request token
                pipe.zadd(redis_key, {f"{now}_{uuid.uuid4().hex[:6]}": now})
                # 4. Set expiry buffer
                pipe.expire(redis_key, window_seconds + 10)
                results = await pipe.execute()

            current_count = results[1]
            if current_count >= max_requests:
                # Over quota: calculate retry-after from oldest entry
                oldest_entries = await client.zrange(redis_key, 0, 0, withscores=True)
                retry_after = window_seconds
                if oldest_entries:
                    oldest_ts = oldest_entries[0][1]
                    retry_after = max(1, int(math.ceil(oldest_ts + window_seconds - now)))
                return False, 0, retry_after

            remaining = max(0, max_requests - current_count - 1)
            return True, remaining, 0

        except Exception as err:
            logger.warning("Redis operation failed in rate limiter (%s). Falling back to in-memory.", err)
            return await self._fallback.check_rate_limit(key, max_requests, window_seconds)

    async def reset(self, key: str) -> None:
        client = await self._get_client()
        if client:
            try:
                await client.delete(f"sentinel:rl:{key}")
            except Exception:
                pass
        await self._fallback.reset(key)


# Global singleton backend instance
_backend_instance: Optional[RateLimiterBackend] = None
_backend_lock = threading.Lock()


def get_rate_limiter_backend(settings: Optional[Settings] = None) -> RateLimiterBackend:
    """Obtain or initialize the global rate limiter storage backend."""
    global _backend_instance
    with _backend_lock:
        if _backend_instance is not None:
            return _backend_instance

        active_settings = settings or get_settings()
        storage_type = active_settings.rate_limit_storage

        if storage_type in ("redis", "auto") and active_settings.redis_url:
            _backend_instance = RedisRateLimiterBackend(active_settings.redis_url)
            logger.info("Configured Redis distributed rate limiter backend.")
        else:
            _backend_instance = InMemoryRateLimiterBackend()
            logger.info("Configured In-Memory rate limiter backend (local process only).")

        return _backend_instance


def set_rate_limiter_backend(backend: Optional[RateLimiterBackend]) -> None:
    """Explicitly set or reset the backend singleton (used in test fixtures)."""
    global _backend_instance
    with _backend_lock:
        _backend_instance = backend


class RateLimiter:
    """FastAPI route dependency enforcing configurable rate limits."""

    def __init__(
        self,
        endpoint_name: str,
        default_limit: Optional[str] = None,
        key_type: Literal["ip", "user", "user_or_ip"] = "user_or_ip",
    ) -> None:
        self.endpoint_name = endpoint_name
        self.default_limit = default_limit
        self.key_type = key_type

    def _resolve_limit_expression(self, settings: Settings) -> str:
        """Resolve the effective rate limit expression from settings."""
        setting_key = f"rate_limit_{self.endpoint_name.lower().replace('-', '_')}"
        configured = getattr(settings, setting_key, None)
        if configured:
            return str(configured)
        return self.default_limit or settings.rate_limit_general

    async def __call__(self, request: Request, response: Response) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        limit_expr = self._resolve_limit_expression(settings)
        max_requests, window_seconds = parse_rate_limit(limit_expr)

        client_ip = get_trusted_client_ip(request, settings.trusted_proxies)

        # Resolve subject identifier for key
        subject = client_ip
        if self.key_type in ("user", "user_or_ip"):
            # Check if user object was attached to request state by auth dependency
            user = getattr(request.state, "user", None)
            if user and hasattr(user, "id"):
                subject = f"user:{user.id}"
            else:
                subject = f"ip:{client_ip}"
        else:
            subject = f"ip:{client_ip}"

        cache_key = f"{self.endpoint_name}:{subject}"
        backend = get_rate_limiter_backend(settings)

        is_allowed, remaining, retry_after = await backend.check_rate_limit(
            key=cache_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        # Attach standard rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(retry_after if not is_allowed else window_seconds)

        if not is_allowed:
            response.headers["Retry-After"] = str(retry_after)
            raise RateLimitExceededError(
                message=f"Rate limit exceeded for {self.endpoint_name}. Please retry in {retry_after} seconds.",
                retry_after=retry_after,
            )

