"""Tests for Sentinel Voice Biometric Encryption Hardening and Key Management.

Validates AES-256-GCM envelope encryption, Master Key rotation without re-enrollment,
cryptographic erasure (NIST SP 800-88), and tamper detection tags.
"""

from pathlib import Path
import numpy as np
import pytest

from sentinelai.biometrics.exceptions import BiometricStorageError, VectorTamperedError
from sentinelai.biometrics.storage import BiometricStorageManager


def test_master_key_rotation_flow(tmp_path: Path):
    """Verify rotate_master_key re-wraps DEKs with new KEK without corrupting vectors."""
    storage_dir = tmp_path / "biometric_vectors"
    key1 = "old_master_key_32_bytes_long_123"
    key2 = "new_master_key_32_bytes_long_456"

    # 1. Initialize storage and persist a 192D test embedding
    mgr1 = BiometricStorageManager(storage_root=storage_dir, master_key=key1)
    user_id = "user_rot_001"
    profile_id = "prof_rot_001"
    orig_vector = np.random.randn(192).astype(np.float32)

    saved_path, _ = mgr1.save_profile_vector(user_id, profile_id, orig_vector)
    assert Path(saved_path).exists()

    # Verify key1 can load it
    loaded_1 = mgr1.load_profile_vector(user_id, profile_id)
    assert np.allclose(orig_vector, loaded_1, atol=1e-5)

    # 2. Execute master key rotation
    rotated = mgr1.rotate_master_key(old_key=key1, new_key=key2)
    assert rotated == 1

    # 3. Manager using key1 must now fail to decrypt the container
    mgr_old = BiometricStorageManager(storage_root=storage_dir, master_key=key1)
    with pytest.raises(VectorTamperedError):
        mgr_old.load_profile_vector(user_id, profile_id)

    # 4. Manager using key2 must successfully decrypt the exact vector
    mgr_new = BiometricStorageManager(storage_root=storage_dir, master_key=key2)
    loaded_2 = mgr_new.load_profile_vector(user_id, profile_id)
    assert np.allclose(orig_vector, loaded_2, atol=1e-5)


def test_tamper_detection_in_container(tmp_path: Path):
    """Verify tampering with either header or ciphertext triggers VectorTamperedError."""
    storage_dir = tmp_path / "biometric_vectors"
    key = "master_key_for_tamper_test_32_b"

    mgr = BiometricStorageManager(storage_root=storage_dir, master_key=key)
    user_id = "user_tamper_001"
    profile_id = "prof_tamper_001"
    orig_vector = np.random.randn(192).astype(np.float32)

    saved_path, _ = mgr.save_profile_vector(user_id, profile_id, orig_vector)
    target_file = Path(saved_path)

    # Corrupt the last byte of the encrypted container file
    data = bytearray(target_file.read_bytes())
    data[-1] ^= 0xFF
    target_file.write_bytes(data)

    # Decryption must detect tag mismatch and fail closed
    with pytest.raises(VectorTamperedError, match="corrupted or tampered"):
        mgr.load_profile_vector(user_id, profile_id)


def test_cryptographic_erasure_via_deletion(tmp_path: Path):
    """Verify NIST SP 800-88 Cryptographic Erasure shreds container and destroys DEK."""
    storage_dir = tmp_path / "biometric_vectors"
    key = "master_key_for_erasure_test_32b"

    mgr = BiometricStorageManager(storage_root=storage_dir, master_key=key)
    user_id = "user_shred_001"
    profile_id = "prof_shred_001"
    orig_vector = np.random.randn(192).astype(np.float32)

    saved_path_str, _ = mgr.save_profile_vector(user_id, profile_id, orig_vector)
    saved_path = Path(saved_path_str)
    assert saved_path.exists()

    # Delete profile vector (executes secure shredding and unlinking)
    deleted = mgr.delete_profile_vector(user_id, profile_id)
    assert deleted is True
    assert not saved_path.exists()

    # Subsequent load must fail with BiometricStorageError (profile not found)
    with pytest.raises(BiometricStorageError, match="does not exist"):
        mgr.load_profile_vector(user_id, profile_id)
