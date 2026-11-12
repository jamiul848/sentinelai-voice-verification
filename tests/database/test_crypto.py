"""Unit tests for Biometric Vector Encryption (AES-256-GCM) and Key Management."""

import os
from pathlib import Path
import tempfile

import numpy as np
import pytest

from sentinelai.auth.crypto import (
    BiometricDecryptionError,
    BiometricKeyError,
    compute_sha256,
    decrypt_embedding_array,
    decrypt_vector_payload,
    derive_key_bytes,
    encrypt_embedding_array,
    encrypt_vector_payload,
    generate_biometric_key,
    secure_delete_file,
)


class TestBiometricCrypto:
    """Test suite for AES-256-GCM biometric vector encryption and secure erasure."""

    def test_generate_and_derive_key(self):
        """Test key generation produces valid 32-byte key."""
        key_str = generate_biometric_key()
        assert isinstance(key_str, str)
        key_bytes = derive_key_bytes(key_str)
        assert len(key_bytes) == 32

    def test_derive_key_from_hex(self):
        """Test hex-encoded 64-character key."""
        hex_key = "a" * 64
        key_bytes = derive_key_bytes(hex_key)
        assert len(key_bytes) == 32
        assert key_bytes == bytes.fromhex(hex_key)

    def test_derive_key_missing_raises_error(self, monkeypatch):
        """Test missing key raises BiometricKeyError."""
        monkeypatch.setenv("SENTINEL_BIOMETRIC_ENCRYPTION_KEY", "")
        # Clear settings cache if any
        from sentinelai.config import get_settings
        get_settings.cache_clear()

        with pytest.raises(BiometricKeyError):
            derive_key_bytes("")

    def test_raw_payload_encryption_roundtrip(self):
        """Test encrypting and decrypting arbitrary bytes."""
        key = generate_biometric_key()
        raw_data = b"confidential_speaker_biometric_data_123456"
        encrypted = encrypt_vector_payload(raw_data, key=key)

        assert encrypted != raw_data
        assert len(encrypted) == 12 + len(raw_data) + 16

        decrypted = decrypt_vector_payload(encrypted, key=key)
        assert decrypted == raw_data

    def test_embedding_array_encryption_roundtrip(self):
        """Test encrypting and decrypting a 192D float32 numpy embedding."""
        key = generate_biometric_key()
        original_vector = np.random.randn(192).astype(np.float32)

        encrypted = encrypt_embedding_array(original_vector, key=key)
        assert len(encrypted) > 192 * 4

        decrypted_vector = decrypt_embedding_array(encrypted, key=key)
        assert decrypted_vector.shape == (192,)
        assert decrypted_vector.dtype == np.float32
        np.testing.assert_allclose(original_vector, decrypted_vector, atol=1e-6)

    def test_tampered_ciphertext_detection(self):
        """Test AES-256-GCM authentication tag rejects altered ciphertext."""
        key = generate_biometric_key()
        raw_data = b"sensitive_centroid_payload"
        encrypted = bytearray(encrypt_vector_payload(raw_data, key=key))

        # Tamper with a byte in ciphertext
        encrypted[15] ^= 0x55

        with pytest.raises(BiometricDecryptionError):
            decrypt_vector_payload(bytes(encrypted), key=key)

    def test_short_payload_detection(self):
        """Test payloads shorter than minimum nonce + tag are rejected."""
        key = generate_biometric_key()
        with pytest.raises(BiometricDecryptionError):
            decrypt_vector_payload(b"too_short", key=key)

    def test_wrong_key_fails_decryption(self):
        """Test decrypting with a mismatched key raises BiometricDecryptionError."""
        key1 = generate_biometric_key()
        key2 = generate_biometric_key()
        encrypted = encrypt_vector_payload(b"secret", key=key1)

        with pytest.raises(BiometricDecryptionError):
            decrypt_vector_payload(encrypted, key=key2)

    def test_compute_sha256(self):
        """Test SHA-256 calculation."""
        data = b"sentinel_voice_test"
        digest = compute_sha256(data)
        assert len(digest) == 64
        assert isinstance(digest, str)

    def test_secure_delete_file(self):
        """Test file overwriting and erasure."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"biometric_vector_bytes_to_delete" * 10)
            tmp_path = Path(tmp.name)

        assert tmp_path.exists()
        secure_delete_file(tmp_path)
        assert not tmp_path.exists()

