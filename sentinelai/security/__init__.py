"""Sentinel Voice - Security, Rate Limiting & Hardening Package."""

from sentinelai.security.auth_abuse import (
    AccountTemporarilyThrottledError,
    AuthAbuseTracker,
    get_auth_abuse_tracker,
)
from sentinelai.security.config_validator import (
    ConfigurationSecurityError,
    validate_runtime_configuration,
)
from sentinelai.security.rate_limiter import (
    InMemoryRateLimiterBackend,
    RateLimitExceededError,
    RateLimiter,
    RateLimiterBackend,
    RedisRateLimiterBackend,
    get_rate_limiter_backend,
    get_trusted_client_ip,
    parse_rate_limit,
    set_rate_limiter_backend,
)

__all__ = [
    "RateLimiter",
    "RateLimitExceededError",
    "RateLimiterBackend",
    "InMemoryRateLimiterBackend",
    "RedisRateLimiterBackend",
    "get_rate_limiter_backend",
    "set_rate_limiter_backend",
    "parse_rate_limit",
    "get_trusted_client_ip",
    "AuthAbuseTracker",
    "AccountTemporarilyThrottledError",
    "get_auth_abuse_tracker",
    "ConfigurationSecurityError",
    "validate_runtime_configuration",
]

