"""Integration and API tests for the FastAPI enrollment endpoints."""

from typing import List
from fastapi.testclient import TestClient
import pytest

from sentinelai.enrollment.api import get_enrollment_service
from sentinelai.enrollment.service import EnrollmentService
from sentinelai.main import app


@pytest.fixture
def client_with_mock_enrollment(enrollment_service: EnrollmentService) -> TestClient:
    """Provide a TestClient with the isolated, mocked enrollment service injected."""
    app.dependency_overrides[get_enrollment_service] = lambda: enrollment_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestEnrollmentAPI:
    """Test suite for FastAPI enrollment HTTP routes."""

    def test_api_register_success(
        self,
        client_with_mock_enrollment: TestClient,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: POST /enrollment/register creates a profile and returns 201 Created."""
        files = [
            ("files", (f"sample_{i}.wav", data, "audio/wav"))
            for i, data in enumerate(valid_enrollment_audio_samples)
        ]
        data = {
            "user_id": "api_user_01",
            "consent": "true",
        }

        response = client_with_mock_enrollment.post("/enrollment/register", data=data, files=files)
        assert response.status_code == 201

        payload = response.json()
        assert payload["success"] is True
        assert payload["user_id"] == "api_user_01"
        assert payload["sample_count"] == 3
        assert payload["embedding_dimension"] == 192
        assert "profile_id" in payload

        # Security check: Biometric embedding vector MUST NOT be exposed in response
        assert "reference_embedding" not in payload
        assert "embedding" not in payload

    def test_api_register_missing_consent(
        self,
        client_with_mock_enrollment: TestClient,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Consent validation via API returns HTTP 400."""
        files = [
            ("files", (f"sample_{i}.wav", data, "audio/wav"))
            for i, data in enumerate(valid_enrollment_audio_samples)
        ]
        data = {
            "user_id": "no_consent_user",
            "consent": "false",
        }

        response = client_with_mock_enrollment.post("/enrollment/register", data=data, files=files)
        assert response.status_code == 400
        assert "consent" in response.json()["detail"].lower()

    def test_api_register_insufficient_recordings(
        self,
        client_with_mock_enrollment: TestClient,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Submitting fewer than min_recordings returns HTTP 400."""
        # Only 2 files
        files = [
            ("files", (f"sample_{i}.wav", data, "audio/wav"))
            for i, data in enumerate(valid_enrollment_audio_samples[:2])
        ]
        data = {
            "user_id": "short_user",
            "consent": "true",
        }

        response = client_with_mock_enrollment.post("/enrollment/register", data=data, files=files)
        assert response.status_code == 400
        assert "at least 3" in response.json()["detail"]

    def test_api_register_duplicate_user_conflict(
        self,
        client_with_mock_enrollment: TestClient,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Enrolling already-active user returns HTTP 409 Conflict."""
        files1 = [("files", (f"s_{i}.wav", d, "audio/wav")) for i, d in enumerate(valid_enrollment_audio_samples)]
        client_with_mock_enrollment.post("/enrollment/register", data={"user_id": "dup_user", "consent": "true"}, files=files1)

        # Attempt second enrollment for same user
        files2 = [("files", (f"s_{i}.wav", d, "audio/wav")) for i, d in enumerate(valid_enrollment_audio_samples)]
        response = client_with_mock_enrollment.post("/enrollment/register", data={"user_id": "dup_user", "consent": "true"}, files=files2)
        assert response.status_code == 409
        assert "already has an active voice profile" in response.json()["detail"]

    def test_api_get_profile_and_status(
        self,
        client_with_mock_enrollment: TestClient,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Query public profile metadata and enrollment status."""
        files = [("files", (f"s_{i}.wav", d, "audio/wav")) for i, d in enumerate(valid_enrollment_audio_samples)]
        reg_res = client_with_mock_enrollment.post("/enrollment/register", data={"user_id": "query_user", "consent": "true"}, files=files)
        profile_id = reg_res.json()["profile_id"]

        # GET /enrollment/profile/{profile_id}
        prof_res = client_with_mock_enrollment.get(f"/enrollment/profile/{profile_id}")
        assert prof_res.status_code == 200
        prof_data = prof_res.json()
        assert prof_data["profile_id"] == profile_id
        assert prof_data["user_id"] == "query_user"
        assert prof_data["status"] == "ACTIVE"
        # Biometric embeddings MUST NOT be present
        assert "reference_embedding" not in prof_data

        # GET /enrollment/status/{user_id}
        stat_res = client_with_mock_enrollment.get("/enrollment/status/query_user")
        assert stat_res.status_code == 200
        stat_data = stat_res.json()
        assert stat_data["status"] == "ACTIVE"
        assert stat_data["profile_id"] == profile_id

    def test_api_reenroll(
        self,
        client_with_mock_enrollment: TestClient,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: POST /enrollment/reenroll updates voiceprint and supersedes old profile."""
        files1 = [("files", (f"s_{i}.wav", d, "audio/wav")) for i, d in enumerate(valid_enrollment_audio_samples)]
        client_with_mock_enrollment.post("/enrollment/register", data={"user_id": "re_user", "consent": "true"}, files=files1)

        files2 = [("files", (f"new_{i}.wav", d, "audio/wav")) for i, d in enumerate(valid_enrollment_audio_samples)]
        re_res = client_with_mock_enrollment.post("/enrollment/reenroll", data={"user_id": "re_user", "consent": "true"}, files=files2)
        assert re_res.status_code == 200
        re_data = re_res.json()
        assert re_data["success"] is True
        assert re_data["profile_id"] != re_data["previous_profile_id"]

    def test_api_revoke_profile(
        self,
        client_with_mock_enrollment: TestClient,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: DELETE /enrollment/profile/{profile_id} revokes profile."""
        files = [("files", (f"s_{i}.wav", d, "audio/wav")) for i, d in enumerate(valid_enrollment_audio_samples)]
        reg_res = client_with_mock_enrollment.post("/enrollment/register", data={"user_id": "del_user", "consent": "true"}, files=files)
        profile_id = reg_res.json()["profile_id"]

        del_res = client_with_mock_enrollment.delete(
            f"/enrollment/profile/{profile_id}",
            params={"reason": "User opt-out"},
        )
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert del_data["status"] == "REVOKED"

        # Check status now reports REVOKED
        stat_res = client_with_mock_enrollment.get("/enrollment/status/del_user")
        assert stat_res.json()["status"] == "REVOKED"
