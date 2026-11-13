"""Security, Privacy, and Biometric Protection tests for Speaker Verification."""

from fastapi.testclient import TestClient
import numpy as np
import pytest

from sentinelai.verification.audit import AuditRecord, JsonLinesAuditLogger
from sentinelai.verification.exceptions import AuditLoggingError, ProfileRevokedError
from sentinelai.verification.schemas import VerificationResponse, VerificationStatus
from sentinelai.verification.service import SpeakerVerificationService


class TestVerificationSecurity:
    """Rigorous tests ensuring biometric data privacy and operational security."""

    def test_no_embeddings_in_verification_response_schema(self) -> None:
        """The public VerificationResponse schema must never define fields for biometric arrays."""
        fields = VerificationResponse.model_fields.keys()
        for forbidden in ("embedding", "reference_embedding", "tensor", "vector", "audio", "waveform"):
            assert forbidden not in fields, f"Forbidden field '{forbidden}' found in VerificationResponse!"

    def test_audit_logger_rejects_biometric_payloads(self, tmp_path) -> None:
        """JsonLinesAuditLogger must proactively reject records containing biometric data."""
        logger = JsonLinesAuditLogger(log_path=tmp_path / "audit.jsonl")

        # Attempt to pass an embedding inside metadata
        compromised_record = AuditRecord(
            verification_id="v_123",
            user_id="alice",
            profile_id="p_456",
            status="MATCH",
            verified=True,
            threshold_version="v1.0",
            model_name="ecapa",
            timestamp="2026-11-11T00:00:00Z",
            processing_time_ms=12.5,
            metadata={"embedding": [0.1, 0.2, 0.3]},
        )

        with pytest.raises(AuditLoggingError, match="Biometric privacy violation"):
            logger.log_verification(compromised_record)

    def test_revoked_profiles_strictly_blocked_from_verification(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Revoked profiles must be rejected before feature extraction occurs."""
        with pytest.raises(ProfileRevokedError, match="is REVOKED"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                profile_id="profile_charlie_003",
            )

    def test_client_cannot_inject_arbitrary_reference_embeddings(
        self,
        client_with_mock_verification: TestClient,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """API client attempting to supply arbitrary reference embeddings must have them ignored or rejected."""
        files = {"audio_file": ("test_voice.wav", valid_candidate_audio_sample, "audio/wav")}
        data = {
            "user_id": "user_alice",
            "reference_embedding": "[1.0, 0.0, 0.0]",  # Malicious attempt to inject reference
        }

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        # Endpoint should process correctly using the stored profile and not crash or accept injected vector
        assert response.status_code == 200
        payload = response.json()
        assert "reference_embedding" not in payload

    def test_no_internal_file_paths_leaked_in_api_errors(
        self,
        client_with_mock_verification: TestClient,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """API error messages must not leak internal storage file paths (.npz, .meta.json, drive letters)."""
        files = {"audio_file": ("test_voice.wav", valid_candidate_audio_sample, "audio/wav")}
        data = {"user_id": "user_unknown"}

        response = client_with_mock_verification.post("/verification/verify", data=data, files=files)
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert ".meta.json" not in detail
        assert ".npz" not in detail
        assert "E:\\" not in detail
        assert "C:\\" not in detail

