"""Integration and API tests for the FastAPI verification endpoints."""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import numpy as np
import pytest
import torch

from sentinelai.main import app
from sentinelai.speaker.embedding import SpeakerEmbeddingResult
from sentinelai.verification.api import get_verification_service
from sentinelai.verification.service import SpeakerVerificationService


class TestVerificationAPI:
    """API endpoint tests for /verification/verify and /verification/health."""

    def test_api_verification_match_success(
        self,
        client_with_mock_verification: TestClient,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Requirement: POST /verification/verify returns 200 OK with MATCH when embeddings match."""
        aligned_vec = np.zeros(192, dtype=np.float32)
        aligned_vec[:10] = 1.0
        aligned_vec = aligned_vec / np.linalg.norm(aligned_vec)

        mock_result = SpeakerEmbeddingResult(
            embedding=aligned_vec,
            embedding_tensor=torch.from_numpy(aligned_vec),
            dimension=192,
            model_id="speechbrain/spkrec-ecapa-voxceleb",
            device="cpu",
            audio_duration_sec=1.5,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        verification_service.extractor.extract = MagicMock(return_value=mock_result)

        files = {"audio_file": ("test_voice.wav", valid_candidate_audio_sample, "audio/wav")}
        data = {"user_id": "user_alice"}

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        assert response.status_code == 200

        payload = response.json()
        assert payload["status"] == "MATCH"
        assert payload["verified"] is True
        assert payload["user_id"] == "user_alice"
        assert payload["profile_id"] == "profile_alice_001"
        assert payload["similarity_score"] is not None
        assert payload["similarity_score"] >= 0.65
        assert payload["processing_time_ms"] >= 0.0

        # CRITICAL PRIVACY INVARIANT: Ensure no embeddings or tensors are returned
        assert "embedding" not in payload
        assert "reference_embedding" not in payload
        assert "audio_bytes" not in payload

    def test_api_verification_no_match(
        self,
        client_with_mock_verification: TestClient,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """POST /verification/verify returns 200 OK with NO_MATCH when embeddings diverge."""
        orthogonal_vec = np.zeros(192, dtype=np.float32)
        orthogonal_vec[50:60] = 1.0
        orthogonal_vec = orthogonal_vec / np.linalg.norm(orthogonal_vec)

        mock_result = SpeakerEmbeddingResult(
            embedding=orthogonal_vec,
            embedding_tensor=torch.from_numpy(orthogonal_vec),
            dimension=192,
            model_id="speechbrain/spkrec-ecapa-voxceleb",
            device="cpu",
            audio_duration_sec=1.5,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        verification_service.extractor.extract = MagicMock(return_value=mock_result)

        files = {"audio_file": ("test_voice.wav", valid_candidate_audio_sample, "audio/wav")}
        data = {"user_id": "user_alice"}

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        assert response.status_code == 200

        payload = response.json()
        assert payload["status"] == "NO_MATCH"
        assert payload["verified"] is False
        assert payload["similarity_score"] is not None
        assert payload["similarity_score"] < 0.65

    def test_api_verification_profile_not_found(
        self,
        client_with_mock_verification: TestClient,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """POST /verification/verify returns 404 Not Found for unregistered user/profile."""
        files = {"audio_file": ("test_voice.wav", valid_candidate_audio_sample, "audio/wav")}
        data = {"user_id": "user_unknown"}

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        assert response.status_code == 404
        assert "No active enrolled speaker profile found" in response.json()["detail"]

    def test_api_verification_profile_revoked(
        self,
        client_with_mock_verification: TestClient,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """POST /verification/verify returns 403 Forbidden when attempting to verify against revoked profile."""
        files = {"audio_file": ("test_voice.wav", valid_candidate_audio_sample, "audio/wav")}
        data = {"profile_id": "profile_charlie_003"}

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        assert response.status_code == 403
        assert "is REVOKED" in response.json()["detail"]

    def test_api_verification_missing_identifiers(
        self,
        client_with_mock_verification: TestClient,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """POST /verification/verify returns 400 Bad Request when neither user_id nor profile_id is provided."""
        files = {"audio_file": ("test_voice.wav", valid_candidate_audio_sample, "audio/wav")}

        response = client_with_mock_verification.post("/verification/verify", data={}, files=files)
        assert response.status_code == 400
        assert "At least one of 'user_id' or 'profile_id' must be provided" in response.json()["detail"]

    def test_api_verification_empty_audio_file(
        self,
        client_with_mock_verification: TestClient,
    ) -> None:
        """POST /verification/verify returns 400 Bad Request when uploaded file is 0 bytes."""
        files = {"audio_file": ("empty.wav", b"", "audio/wav")}
        data = {"user_id": "user_alice"}

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        assert response.status_code == 400
        assert "empty (0 bytes)" in response.json()["detail"]

    def test_api_verification_excessive_file_size(
        self,
        client_with_mock_verification: TestClient,
        verification_service: SpeakerVerificationService,
    ) -> None:
        """POST /verification/verify returns 413 Payload Too Large when audio exceeds limit."""
        verification_service.config.max_audio_size_bytes = 100
        files = {"audio_file": ("large.wav", b"x" * 200, "audio/wav")}
        data = {"user_id": "user_alice"}

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        assert response.status_code == 413
        assert "exceeds maximum allowed upload size" in response.json()["detail"]

    def test_api_verification_health_endpoint(
        self,
        client_with_mock_verification: TestClient,
    ) -> None:
        """GET /verification/health returns 200 OK with service status."""
        response = client_with_mock_verification.get("/verification/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["service"] == "SentinelAI Speaker Verification Engine"
        assert "threshold_version" in payload
        assert "device" in payload
