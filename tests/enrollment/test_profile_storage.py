"""Unit tests for the profile storage abstraction layer."""

from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest

from sentinelai.enrollment.schemas import ProfileStatus, SpeakerProfile
from sentinelai.enrollment.storage import LocalFileProfileStorage


def make_sample_profile(profile_id: str, user_id: str, status: ProfileStatus = ProfileStatus.ACTIVE) -> SpeakerProfile:
    """Helper to generate a test SpeakerProfile."""
    ref_emb = np.random.randn(192).astype(np.float32)
    ref_emb /= np.linalg.norm(ref_emb)
    now = datetime.now(timezone.utc)
    return SpeakerProfile(
        profile_id=profile_id,
        user_id=user_id,
        reference_embedding=ref_emb,
        individual_embeddings=[ref_emb],
        embedding_dimension=192,
        model_name="speechbrain/spkrec-ecapa-voxceleb",
        enrollment_sample_count=3,
        created_at=now,
        updated_at=now,
        consent_status=True,
        profile_status=status,
    )


class TestProfileStorage:
    """Test suite for LocalFileProfileStorage."""

    def test_save_and_retrieve_profile(self, tmp_path: Path) -> None:
        """Requirement: Persist profile and retrieve it without data loss."""
        storage = LocalFileProfileStorage(storage_dir=tmp_path / "profiles")
        profile = make_sample_profile("prof_001", "alice_test")

        storage.save_profile(profile)

        retrieved = storage.get_profile_by_id("prof_001")
        assert retrieved is not None
        assert retrieved.profile_id == "prof_001"
        assert retrieved.user_id == "alice_test"
        assert retrieved.embedding_dimension == 192
        assert retrieved.is_active is True
        assert retrieved.reference_embedding is not None
        np.testing.assert_allclose(retrieved.reference_embedding, profile.reference_embedding, atol=1e-6)

    def test_storage_does_not_use_pickle(self, tmp_path: Path) -> None:
        """Requirement: Safe numerical format, never use pickle."""
        storage = LocalFileProfileStorage(storage_dir=tmp_path / "profiles")
        profile = make_sample_profile("prof_safe", "safe_user")
        storage.save_profile(profile)

        # Inspect disk files: must be .meta.json and .emb.npz
        meta_file = storage.storage_dir / "prof_safe.meta.json"
        emb_file = storage.storage_dir / "prof_safe.emb.npz"

        assert meta_file.exists()
        assert emb_file.exists()

        # Read JSON file to verify it is valid human-readable JSON
        content = meta_file.read_text(encoding="utf-8")
        assert '"profile_id": "prof_safe"' in content

    def test_get_active_profile_by_user_id(self, tmp_path: Path) -> None:
        """Requirement: Query active profile for a specific user ID."""
        storage = LocalFileProfileStorage(storage_dir=tmp_path / "profiles")
        p1 = make_sample_profile("p_revoked", "bob", status=ProfileStatus.REVOKED)
        p2 = make_sample_profile("p_active", "bob", status=ProfileStatus.ACTIVE)

        storage.save_profile(p1)
        storage.save_profile(p2)

        active = storage.get_active_profile_by_user_id("bob")
        assert active is not None
        assert active.profile_id == "p_active"

    def test_get_profiles_by_user_id(self, tmp_path: Path) -> None:
        """Verify retrieving all profiles (active and historical) for a user."""
        storage = LocalFileProfileStorage(storage_dir=tmp_path / "profiles")
        p1 = make_sample_profile("p1", "charlie", status=ProfileStatus.REVOKED)
        p2 = make_sample_profile("p2", "charlie", status=ProfileStatus.ACTIVE)

        storage.save_profile(p1)
        storage.save_profile(p2)

        all_charlie = storage.get_profiles_by_user_id("charlie")
        assert len(all_charlie) == 2

    def test_update_profile(self, tmp_path: Path) -> None:
        """Verify updating profile state."""
        storage = LocalFileProfileStorage(storage_dir=tmp_path / "profiles")
        p = make_sample_profile("p_update", "dave")
        storage.save_profile(p)

        p.metadata["notes"] = "updated_test"
        storage.update_profile(p)

        updated = storage.get_profile_by_id("p_update")
        assert updated is not None
        assert updated.metadata.get("notes") == "updated_test"

    def test_delete_profile(self, tmp_path: Path) -> None:
        """Verify permanent profile deletion."""
        storage = LocalFileProfileStorage(storage_dir=tmp_path / "profiles")
        p = make_sample_profile("p_del", "eve")
        storage.save_profile(p)

        assert storage.delete_profile("p_del") is True
        assert storage.get_profile_by_id("p_del") is None

    def test_nonexistent_profile_returns_none(self, tmp_path: Path) -> None:
        """Verify non-existent ID queries return None without throwing."""
        storage = LocalFileProfileStorage(storage_dir=tmp_path / "profiles")
        assert storage.get_profile_by_id("missing_id") is None
        assert storage.get_active_profile_by_user_id("missing_user") is None

