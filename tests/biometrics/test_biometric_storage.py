"""Unit tests for BiometricStorageManager and envelope encryption."""

import io
from pathlib import Path
import uuid
import numpy as np
import pytest

from sentinelai.auth.crypto import encrypt_embedding_array
from sentinelai.biometrics.exceptions import (
    BiometricStorageError,
    DirectoryTraversalError,
    VectorTamperedError,
)
from sentinelai.biometrics.storage import MAGIC_HEADER, BiometricStorageManager


def test_save_and_load_envelope_vector(temp_storage: BiometricStorageManager):
    """Verify that 192D embeddings are envelope-encrypted with DEK and decrypted faithfully."""
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    original_vector = np.random.randn(192).astype(np.float32)
    original_vector /= np.linalg.norm(original_vector)

    path_str, sha256_hash = temp_storage.save_profile_vector(
        user_id=user_id,
        profile_id=profile_id,
        embedding=original_vector,
    )

    path = Path(path_str)
    assert path.exists()

    # Verify file begins with V2 magic bytes
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == MAGIC_HEADER

    # Load and authenticate vector
    loaded_vector = temp_storage.load_profile_vector(
        user_id=user_id,
        profile_id=profile_id,
        expected_sha256=sha256_hash,
    )

    assert loaded_vector.shape == (192,)
    assert loaded_vector.dtype == np.float32
    np.testing.assert_allclose(loaded_vector, original_vector, rtol=1e-5, atol=1e-6)


def test_tamper_detection_checksum(temp_storage: BiometricStorageManager):
    """Verify that tampering with container content triggers VectorTamperedError."""
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    vector = np.random.randn(192).astype(np.float32)

    path_str, sha256_hash = temp_storage.save_profile_vector(
        user_id=user_id,
        profile_id=profile_id,
        embedding=vector,
    )
    path = Path(path_str)

    # Tamper with file
    with open(path, "r+b") as f:
        f.seek(15)
        byte = f.read(1)
        f.seek(15)
        # Flip bits
        f.write(bytes([byte[0] ^ 0xFF]))

    # Must fail checksum verification
    with pytest.raises(VectorTamperedError, match="checksum mismatch"):
        temp_storage.load_profile_vector(
            user_id=user_id,
            profile_id=profile_id,
            expected_sha256=sha256_hash,
        )


def test_tamper_detection_gcm_auth_tag(temp_storage: BiometricStorageManager):
    """Verify that tampering with payload fails GCM authentication even if checksum is omitted."""
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    vector = np.random.randn(192).astype(np.float32)

    path_str, _ = temp_storage.save_profile_vector(
        user_id=user_id,
        profile_id=profile_id,
        embedding=vector,
    )
    path = Path(path_str)

    # Corrupt vector ciphertext
    with open(path, "r+b") as f:
        f.seek(-5, 2)
        f.write(b"\x00\x00")

    # Load without expected_sha256 - should fail at GCM decrypt step
    with pytest.raises(VectorTamperedError, match="Cryptographic tag authentication failed"):
        temp_storage.load_profile_vector(user_id=user_id, profile_id=profile_id)


def test_path_traversal_defenses(temp_storage: BiometricStorageManager):
    """Verify that directory traversal sequences are strictly trapped."""
    safe_profile = uuid.uuid4()

    with pytest.raises(DirectoryTraversalError):
        temp_storage.get_profile_path("../evil_user", safe_profile)

    with pytest.raises(DirectoryTraversalError):
        temp_storage.get_profile_path("..\\evil_user", safe_profile)

    with pytest.raises(DirectoryTraversalError):
        temp_storage.get_profile_path(uuid.uuid4(), "../escape_profile")

    with pytest.raises(DirectoryTraversalError):
        temp_storage.get_profile_path(uuid.uuid4(), "sub/path/file")


def test_cryptographic_shredding(temp_storage: BiometricStorageManager):
    """Verify that deleting a profile securely shreds and removes the container file."""
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    vector = np.random.randn(192).astype(np.float32)

    path_str, _ = temp_storage.save_profile_vector(user_id, profile_id, vector)
    path = Path(path_str)
    assert path.exists()

    result = temp_storage.delete_profile_vector(user_id, profile_id)
    assert result is True
    assert not path.exists()

    # Subsequent deletion returns False
    assert temp_storage.delete_profile_vector(user_id, profile_id) is False


def test_legacy_v1_backward_compatibility(temp_storage: BiometricStorageManager):
    """Verify that un-enveloped V1 containers can still be decrypted seamlessly."""
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    original_vector = np.random.randn(192).astype(np.float32)

    # Manually create V1 container directly encrypted with master key (no SNTV2 header)
    v1_bytes = encrypt_embedding_array(original_vector, key=temp_storage.master_key)
    path = temp_storage.get_profile_path(user_id, profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(v1_bytes)

    # Load via storage manager
    loaded_vector = temp_storage.load_profile_vector(user_id, profile_id)
    np.testing.assert_allclose(loaded_vector, original_vector, rtol=1e-5, atol=1e-6)


def test_load_nonexistent_vector_raises(temp_storage: BiometricStorageManager):
    """Verify that attempting to load a non-existent container raises BiometricStorageError."""
    with pytest.raises(BiometricStorageError, match="does not exist"):
        temp_storage.load_profile_vector(uuid.uuid4(), uuid.uuid4())

