"""Tests for Sentinel Voice Authentication Abuse and Brute-Force Defense.

Validates account-level and IP-level throttling, lockouts, counter resets on success,
and safe non-disclosing error messages.
"""

import time
import pytest
from httpx import ASGITransport, AsyncClient

from sentinelai.config import Settings, get_settings
from sentinelai.main import create_app
from sentinelai.security.auth_abuse import AuthAbuseTracker, get_auth_abuse_tracker


def test_auth_abuse_tracker_account_lockout():
    """Verify that exceeding max failed logins triggers temporary account throttling."""
    settings = Settings(auth_max_failed_logins=3, auth_lockout_duration_seconds=300)
    tracker = AuthAbuseTracker(settings=settings)

    test_email = "victim@example.com"
    test_ip = "192.0.2.1"

    # Initial state: not throttled
    throttled, _ = tracker.check_throttled(test_email, test_ip)
    assert throttled is False

    # Record 2 failures (threshold is 3)
    tracker.record_failure(test_email, test_ip)
    tracker.record_failure(test_email, test_ip)
    throttled, _ = tracker.check_throttled(test_email, test_ip)
    assert throttled is False

    # 3rd failure triggers lockout
    tracker.record_failure(test_email, test_ip)
    throttled, retry_after = tracker.check_throttled(test_email, test_ip)
    assert throttled is True
    assert 0 < retry_after <= 300

    # Successful login resets account tracker
    tracker.record_success(test_email, test_ip)
    throttled, _ = tracker.check_throttled(test_email, test_ip)
    assert throttled is False


def test_auth_abuse_tracker_ip_lockout():
    """Verify that excessive failed attempts across different accounts from one IP triggers IP throttling."""
    settings = Settings(
        auth_max_failed_logins=5,
        auth_ip_max_failed_attempts=3,
        auth_ip_lockout_duration_seconds=600,
    )
    tracker = AuthAbuseTracker(settings=settings)
    attacker_ip = "203.0.113.88"

    # Attacker targets 3 different accounts with 1 failure each
    tracker.record_failure("user1@example.com", attacker_ip)
    tracker.record_failure("user2@example.com", attacker_ip)
    throttled, _ = tracker.check_throttled("user3@example.com", attacker_ip)
    assert throttled is False

    # 3rd failure from this IP triggers IP-level lockout
    tracker.record_failure("user3@example.com", attacker_ip)
    throttled, retry_after = tracker.check_throttled("user4@example.com", attacker_ip)
    assert throttled is True
    assert 0 < retry_after <= 600


def test_auth_abuse_tracker_hashes_identifiers():
    """Verify raw emails are never retained in tracker memory keys."""
    tracker = AuthAbuseTracker()
    raw_email = "sensitive_officer@agency.gov"
    tracker.record_failure(raw_email, "127.0.0.1")

    # The tracker keys should be hex digests, never containing the raw string
    for stored_hash in tracker._account_failures.keys():
        assert raw_email not in stored_hash
        assert len(stored_hash) == 64  # SHA-256 hex digest length


@pytest.mark.asyncio
async def test_auth_abuse_http_lockout_flow(async_client: AsyncClient, seeded_user):
    """Verify repeated failed HTTP login attempts result in HTTP 429 and Retry-After."""
    tracker = get_auth_abuse_tracker()
    tracker.clear()

    settings = get_settings()
    original_max = settings.auth_max_failed_logins
    settings.auth_max_failed_logins = 3
    settings.auth_lockout_duration_seconds = 120

    try:
        # Submit 3 bad password attempts
        for i in range(3):
            res = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "testuser@sentinelvoice.io", "password": "WrongPassword999!"},
            )
            assert res.status_code == 401

        # 4th attempt should be blocked by abuse protection before password check
        throttled_res = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
        )
        assert throttled_res.status_code == 429
        body = throttled_res.json()
        assert "Too many failed login attempts" in body.get("detail", body.get("message", ""))
        assert "Retry-After" in throttled_res.headers
        assert int(throttled_res.headers["Retry-After"]) > 0

    finally:
        settings.auth_max_failed_logins = original_max
        tracker.clear()
