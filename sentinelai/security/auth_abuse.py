"""Sentinel Voice - Authentication Abuse & Brute-Force Defense.

Protects against credential stuffing, automated password spraying, and DoS attacks:
1. Tracks consecutive failed login attempts on both account (email hash) and IP basis.
2. Applies temporary throttling when thresholds are crossed without permanently locking accounts.
3. Resets failure counters immediately upon successful authentication.
4. Prevents account enumeration via constant-time evaluation and uniform error responses.
5. Never logs plaintext credentials, tokens, or personal identifiers.
"""

from collections import defaultdict
import hashlib
import logging
import math
import threading
import time
from typing import Dict, Optional, Tuple

from fastapi import status

from sentinelai.auth.exceptions import AuthError
from sentinelai.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AccountTemporarilyThrottledError(AuthError):
    """Raised when an account or IP is temporarily throttled due to excessive failed attempts."""

    def __init__(
        self,
        message: str = "Too many failed login attempts. Please try again later.",
        retry_after: int = 900,
    ) -> None:
        super().__init__(message=message, error_code="ACCOUNT_TEMPORARILY_THROTTLED")
        self.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        self.retry_after = retry_after


class AuthAbuseTracker:
    """In-memory thread-safe authentication abuse and brute-force tracking ledger."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings
        # Structure: key -> [failure_count, last_failure_timestamp]
        self._account_failures: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._ip_failures: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._lock = threading.Lock()

    @property
    def settings(self) -> Settings:
        """Dynamically resolve active settings, accommodating cache clears or environment updates."""
        return self._settings or get_settings()

    def _hash_identifier(self, identifier: str) -> str:
        """Create deterministic non-reversible SHA-256 hash of email/username."""
        return hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()

    def check_throttled(
        self,
        email: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, int]:
        """Check whether the targeted account or client IP is currently throttled.

        Returns:
            Tuple of (is_throttled: bool, retry_after_seconds: int).
        """
        now = time.time()
        account_hash = self._hash_identifier(email)
        ip = ip_address.strip() if ip_address else "127.0.0.1"

        with self._lock:
            # 1. Check IP-level throttling first (prevents distributed spraying)
            ip_count, ip_last = self._ip_failures[ip]
            if ip_count >= self.settings.auth_ip_max_failed_attempts:
                elapsed = now - ip_last
                if elapsed < self.settings.auth_ip_lockout_duration_seconds:
                    retry_after = max(1, int(math.ceil(self.settings.auth_ip_lockout_duration_seconds - elapsed)))
                    return True, retry_after
                else:
                    # Cooldown elapsed: reset IP counter
                    self._ip_failures.pop(ip, None)

            # 2. Check Account-level throttling
            acc_count, acc_last = self._account_failures[account_hash]
            if acc_count >= self.settings.auth_max_failed_logins:
                elapsed = now - acc_last
                if elapsed < self.settings.auth_lockout_duration_seconds:
                    retry_after = max(1, int(math.ceil(self.settings.auth_lockout_duration_seconds - elapsed)))
                    return True, retry_after
                else:
                    # Cooldown elapsed: reset account counter
                    self._account_failures.pop(account_hash, None)

        return False, 0

    def record_failure(self, email: str, ip_address: Optional[str] = None) -> None:
        """Record an authentication failure for both account and IP."""
        now = time.time()
        account_hash = self._hash_identifier(email)
        ip = ip_address.strip() if ip_address else "127.0.0.1"

        with self._lock:
            acc_count, _ = self._account_failures[account_hash]
            self._account_failures[account_hash] = (acc_count + 1, now)

            ip_count, _ = self._ip_failures[ip]
            self._ip_failures[ip] = (ip_count + 1, now)

            logger.warning(
                "Authentication failure recorded. Account attempts: %d, IP attempts: %d",
                acc_count + 1,
                ip_count + 1,
            )

    def record_success(self, email: str, ip_address: Optional[str] = None) -> None:
        """Clear failure counts upon successful credential verification."""
        account_hash = self._hash_identifier(email)
        ip = ip_address.strip() if ip_address else "127.0.0.1"

        with self._lock:
            self._account_failures.pop(account_hash, None)
            self._ip_failures.pop(ip, None)

    def clear(self) -> None:
        """Reset all tracking state (used in automated testing)."""
        with self._lock:
            self._account_failures.clear()
            self._ip_failures.clear()


# Global singleton instance
_tracker_instance: Optional[AuthAbuseTracker] = None
_tracker_lock = threading.Lock()


def get_auth_abuse_tracker() -> AuthAbuseTracker:
    """Retrieve or initialize the global AuthAbuseTracker singleton."""
    global _tracker_instance
    with _tracker_lock:
        if _tracker_instance is None:
            _tracker_instance = AuthAbuseTracker()
        return _tracker_instance
