"""Storage Abstraction Layer for Speaker Profiles and Biometric Embeddings.

Provides an abstract base interface and a secure local filesystem storage backend
using structured JSON metadata and NumPy binary .npz containers.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
from threading import Lock
from typing import Any, Dict, List, Optional
import numpy as np

from sentinelai.enrollment.exceptions import StorageError
from sentinelai.enrollment.schemas import ProfileStatus, SpeakerProfile


class ProfileStorageBackend(ABC):
    """Abstract interface defining operations for persisting and retrieving speaker profiles."""

    @abstractmethod
    def save_profile(self, profile: SpeakerProfile) -> None:
        """Persist a new speaker profile and its biometric embeddings."""
        pass

    @abstractmethod
    def get_profile_by_id(self, profile_id: str) -> Optional[SpeakerProfile]:
        """Retrieve a profile by its unique profile ID."""
        pass

    @abstractmethod
    def get_active_profile_by_user_id(self, user_id: str) -> Optional[SpeakerProfile]:
        """Retrieve the currently active profile for a given user ID."""
        pass

    @abstractmethod
    def get_profiles_by_user_id(self, user_id: str) -> List[SpeakerProfile]:
        """Retrieve all profiles (active and revoked) belonging to a user ID."""
        pass

    @abstractmethod
    def update_profile(self, profile: SpeakerProfile) -> None:
        """Update an existing speaker profile metadata and state."""
        pass

    @abstractmethod
    def delete_profile(self, profile_id: str) -> bool:
        """Permanently delete a profile record and associated vectors."""
        pass

    @abstractmethod
    def list_profiles(self, status: Optional[ProfileStatus] = None) -> List[SpeakerProfile]:
        """List all profiles, optionally filtered by operational status."""
        pass


class LocalFileProfileStorage(ProfileStorageBackend):
    """Secure local filesystem storage backend for speaker profiles.

    Storage Design:
        - Metadata: Stored in structured JSON files (<profile_id>.meta.json).
        - Biometric Embeddings: Stored in NumPy compressed containers (<profile_id>.emb.npz).
        - Security: NEVER uses Python pickle. Uses atomic file writes (write-then-rename)
          and restricts file permissions to owner read/write (0o600) on supported OS platforms.
        - Privacy: When a profile is revoked, the biometric embedding file is purged from disk.
    """

    def __init__(self, storage_dir: Path) -> None:
        """Initialize the storage backend.

        Args:
            storage_dir: Path to directory for profile records.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _meta_path(self, profile_id: str) -> Path:
        """Path to JSON metadata file."""
        return self.storage_dir / f"{profile_id}.meta.json"

    def _emb_path(self, profile_id: str) -> Path:
        """Path to NPZ embedding container."""
        return self.storage_dir / f"{profile_id}.emb.npz"

    @staticmethod
    def _apply_file_permissions(file_path: Path) -> None:
        """Set owner-only read/write permissions (0o600) where supported by the OS."""
        try:
            if hasattr(os, "chmod") and os.name != "nt":
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def _write_atomic_json(self, target_path: Path, data: Dict[str, Any]) -> None:
        """Write JSON data atomically using a temporary file."""
        temp_path = target_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._apply_file_permissions(temp_path)
            temp_path.replace(target_path)
        except Exception as exc:
            if temp_path.exists():
                temp_path.unlink()
            raise StorageError(f"Failed to write metadata file '{target_path}': {exc}") from exc

    def _load_profile_from_disk(self, profile_id: str) -> Optional[SpeakerProfile]:
        """Internal helper to load profile and optional embeddings without acquiring lock."""
        meta_file = self._meta_path(profile_id)
        if not meta_file.exists():
            return None

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as exc:
            raise StorageError(f"Corrupted metadata file '{meta_file}': {exc}") from exc

        ref_embedding: Optional[np.ndarray] = None
        individual_embeddings: Optional[List[np.ndarray]] = None

        emb_file = self._emb_path(profile_id)
        if emb_file.exists():
            try:
                with np.load(emb_file) as npz:
                    if "reference_embedding" in npz:
                        ref_embedding = npz["reference_embedding"].astype(np.float32)
                    if "individual_embeddings" in npz:
                        stacked = npz["individual_embeddings"]
                        individual_embeddings = [stacked[i].astype(np.float32) for i in range(stacked.shape[0])]
            except Exception as exc:
                raise StorageError(f"Failed to load embedding container '{emb_file}': {exc}") from exc

        return SpeakerProfile(
            profile_id=meta["profile_id"],
            user_id=meta["user_id"],
            reference_embedding=ref_embedding,
            individual_embeddings=individual_embeddings,
            embedding_dimension=meta["embedding_dimension"],
            model_name=meta["model_name"],
            model_version=meta.get("model_version"),
            enrollment_sample_count=meta["enrollment_sample_count"],
            created_at=datetime.fromisoformat(meta["created_at"]),
            updated_at=datetime.fromisoformat(meta["updated_at"]),
            consent_status=meta["consent_status"],
            profile_status=ProfileStatus(meta["profile_status"]),
            revoked_at=datetime.fromisoformat(meta["revoked_at"]) if meta.get("revoked_at") else None,
            revocation_reason=meta.get("revocation_reason"),
            metadata=meta.get("metadata", {}),
        )

    def save_profile(self, profile: SpeakerProfile) -> None:
        """Persist a new speaker profile and its biometric embeddings."""
        with self._lock:
            meta_path = self._meta_path(profile.profile_id)
            emb_path = self._emb_path(profile.profile_id)

            if meta_path.exists():
                raise StorageError(f"Profile with ID '{profile.profile_id}' already exists in storage.")

            # Step 1: Save embeddings to .npz container if present
            if profile.reference_embedding is not None:
                save_dict: Dict[str, np.ndarray] = {"reference_embedding": profile.reference_embedding}
                if profile.individual_embeddings:
                    save_dict["individual_embeddings"] = np.vstack(profile.individual_embeddings)

                temp_emb = emb_path.with_suffix(".tmp")
                try:
                    np.savez_compressed(temp_emb, **save_dict)
                    self._apply_file_permissions(temp_emb)
                    # On Windows, np.savez adds .npz if not present
                    actual_temp = temp_emb if temp_emb.exists() else temp_emb.with_suffix(".tmp.npz")
                    actual_temp.replace(emb_path)
                except Exception as exc:
                    if temp_emb.exists():
                        temp_emb.unlink()
                    raise StorageError(f"Failed to persist biometric embeddings to '{emb_path}': {exc}") from exc

            # Step 2: Save metadata to JSON
            meta_data = {
                "profile_id": profile.profile_id,
                "user_id": profile.user_id,
                "embedding_dimension": profile.embedding_dimension,
                "model_name": profile.model_name,
                "model_version": profile.model_version,
                "enrollment_sample_count": profile.enrollment_sample_count,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
                "consent_status": profile.consent_status,
                "profile_status": profile.profile_status.value,
                "revoked_at": profile.revoked_at.isoformat() if profile.revoked_at else None,
                "revocation_reason": profile.revocation_reason,
                "metadata": profile.metadata,
            }
            self._write_atomic_json(meta_path, meta_data)

    def get_profile_by_id(self, profile_id: str) -> Optional[SpeakerProfile]:
        """Retrieve a profile by its unique profile ID."""
        with self._lock:
            return self._load_profile_from_disk(profile_id)

    def get_active_profile_by_user_id(self, user_id: str) -> Optional[SpeakerProfile]:
        """Retrieve the active profile for a user ID."""
        with self._lock:
            for meta_file in self.storage_dir.glob("*.meta.json"):
                profile_id = meta_file.name.replace(".meta.json", "")
                profile = self._load_profile_from_disk(profile_id)
                if profile and profile.user_id == user_id and profile.is_active:
                    return profile
            return None

    def get_profiles_by_user_id(self, user_id: str) -> List[SpeakerProfile]:
        """Retrieve all profiles (active and revoked) for a user ID."""
        results: List[SpeakerProfile] = []
        with self._lock:
            for meta_file in self.storage_dir.glob("*.meta.json"):
                profile_id = meta_file.name.replace(".meta.json", "")
                profile = self._load_profile_from_disk(profile_id)
                if profile and profile.user_id == user_id:
                    results.append(profile)
        # Sort by created_at descending
        results.sort(key=lambda p: p.created_at, reverse=True)
        return results

    def update_profile(self, profile: SpeakerProfile) -> None:
        """Update an existing profile's metadata and state.

        If profile is REVOKED, purges the biometric embedding file from disk.
        """
        with self._lock:
            meta_path = self._meta_path(profile.profile_id)
            if not meta_path.exists():
                raise StorageError(f"Cannot update non-existent profile '{profile.profile_id}'.")

            # Privacy safeguard: If profile is revoked, erase the biometric embedding file
            if profile.profile_status == ProfileStatus.REVOKED:
                emb_path = self._emb_path(profile.profile_id)
                if emb_path.exists():
                    try:
                        emb_path.unlink()
                    except OSError as exc:
                        raise StorageError(f"Failed to purge biometric embedding file '{emb_path}': {exc}") from exc

            meta_data = {
                "profile_id": profile.profile_id,
                "user_id": profile.user_id,
                "embedding_dimension": profile.embedding_dimension,
                "model_name": profile.model_name,
                "model_version": profile.model_version,
                "enrollment_sample_count": profile.enrollment_sample_count,
                "created_at": profile.created_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "consent_status": profile.consent_status,
                "profile_status": profile.profile_status.value,
                "revoked_at": profile.revoked_at.isoformat() if profile.revoked_at else None,
                "revocation_reason": profile.revocation_reason,
                "metadata": profile.metadata,
            }
            self._write_atomic_json(meta_path, meta_data)

    def delete_profile(self, profile_id: str) -> bool:
        """Permanently delete profile metadata and embeddings."""
        with self._lock:
            meta_path = self._meta_path(profile_id)
            emb_path = self._emb_path(profile_id)
            deleted = False

            if meta_path.exists():
                meta_path.unlink()
                deleted = True
            if emb_path.exists():
                emb_path.unlink()
                deleted = True

            return deleted

    def list_profiles(self, status: Optional[ProfileStatus] = None) -> List[SpeakerProfile]:
        """List all profiles matching the optional status filter."""
        results: List[SpeakerProfile] = []
        with self._lock:
            for meta_file in self.storage_dir.glob("*.meta.json"):
                profile_id = meta_file.name.replace(".meta.json", "")
                profile = self._load_profile_from_disk(profile_id)
                if profile:
                    if status is None or profile.profile_status == status:
                        results.append(profile)
        results.sort(key=lambda p: p.created_at, reverse=True)
        return results

