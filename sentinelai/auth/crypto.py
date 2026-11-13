"""Sentinel Voice - Biometric Vector Encryption & Key Management.

Enforces zero-trust biometric storage:
1. Embeddings are encrypted at rest using AES-256-GCM (Galois/Counter Mode).
2. The master encryption key (SENTINEL_BIOMETRIC_ENCRYPTION_KEY) is strictly decoupled
   from the database.
3. Payloads include a 12-byte cryptographic nonce, ciphertext, and 16-byte authentication tag.
4. Tampering or key mismatch raises an exception.
5. Secure deletion utility overwrites vector files with random bytes and zeros before unlinking.
"""

import base64
import hashlib
import io
import os
from pathlib import Path
from typing import Union

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from sentinelai.config import get_settings

NONCE_SIZE_BYTES = 12
KEY_SIZE_BYTES = 32  # 256 bits


class BiometricDecryptionError(Exception):
    """Raised when biometric vector payload decryption or authentication fails."""


class BiometricKeyError(Exception):
    """Raised when the biometric encryption key is missing or invalid."""


def generate_biometric_key() -> str:
    """Generate a high-entropy 256-bit (32-byte) URL-safe Base64 encryption key.

    Returns:
        Base64-encoded 32-byte key string suitable for SENTINEL_BIOMETRIC_ENCRYPTION_KEY.
    """
    key_bytes = os.urandom(KEY_SIZE_BYTES)
    return base64.urlsafe_b64encode(key_bytes).decode("ascii")


def derive_key_bytes(key: Union[str, bytes, None] = None) -> bytes:
    """Resolve and validate the 32-byte symmetric key.

    Accepts:
    - 32 raw bytes
    - 44-character URL-safe or standard Base64 string (decodes to 32 bytes)
    - 64-character hexadecimal string (decodes to 32 bytes)
    - None (resolves from application settings)

    Args:
        key: Key string or raw bytes. If None, loaded from settings.

    Returns:
        32 raw bytes for AES-256-GCM.

    Raises:
        BiometricKeyError: If key is missing, empty, or cannot resolve to 32 bytes.
    """
    if key is None or (isinstance(key, str) and not key.strip()):
        settings = get_settings()
        key = settings.biometric_encryption_key

    if not key:
        raise BiometricKeyError(
            "Biometric encryption key is not configured. Set the "
            "SENTINEL_BIOMETRIC_ENCRYPTION_KEY environment variable."
        )

    if isinstance(key, bytes):
        if len(key) == KEY_SIZE_BYTES:
            return key
        raise BiometricKeyError(
            f"Biometric encryption key bytes must be exactly {KEY_SIZE_BYTES} bytes, got {len(key)}."
        )

    key_str = key.strip()

    # Try hex decoding (64 hex characters = 32 bytes)
    if len(key_str) == 64:
        try:
            return bytes.fromhex(key_str)
        except ValueError:
            pass

    # Try base64 decoding
    try:
        decoded = base64.urlsafe_b64decode(key_str)
        if len(decoded) == KEY_SIZE_BYTES:
            return decoded
    except Exception:
        pass

    try:
        decoded = base64.b64decode(key_str)
        if len(decoded) == KEY_SIZE_BYTES:
            return decoded
    except Exception:
        pass

    # If raw ASCII length is 32 bytes
    raw_bytes = key_str.encode("utf-8")
    if len(raw_bytes) == KEY_SIZE_BYTES:
        return raw_bytes

    # If key is provided as arbitrary string, hash with SHA-256 to derive deterministic 32 bytes
    return hashlib.sha256(raw_bytes).digest()


def compute_sha256(data: bytes) -> str:
    """Compute the SHA-256 hex digest for biometric payload integrity checking.

    Args:
        data: Arbitrary bytes.

    Returns:
        Hex-encoded SHA-256 string.
    """
    return hashlib.sha256(data).hexdigest()


def encrypt_vector_payload(
    data: bytes,
    key: Union[str, bytes, None] = None,
    associated_data: Union[bytes, None] = None,
) -> bytes:
    """Encrypt binary payload using AES-256-GCM.

    Output format:
    [12 bytes Nonce] + [Ciphertext + 16 bytes Tag]

    Args:
        data: Plaintext bytes to encrypt.
        key: Optional encryption key (resolved from settings if None).
        associated_data: Optional authenticated data.

    Returns:
        Encrypted payload bytes including prepended nonce and appended tag.
    """
    key_bytes = derive_key_bytes(key)
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(NONCE_SIZE_BYTES)
    ciphertext_and_tag = aesgcm.encrypt(nonce, data, associated_data)
    return nonce + ciphertext_and_tag


def decrypt_vector_payload(
    encrypted_data: bytes,
    key: Union[str, bytes, None] = None,
    associated_data: Union[bytes, None] = None,
) -> bytes:
    """Decrypt binary payload using AES-256-GCM and verify integrity.

    Args:
        encrypted_data: Bytes produced by encrypt_vector_payload (nonce + ciphertext + tag).
        key: Optional encryption key (resolved from settings if None).
        associated_data: Optional authenticated data.

    Returns:
        Decrypted plaintext bytes.

    Raises:
        BiometricDecryptionError: If the payload is too short, key is invalid,
            or ciphertext/tag was tampered with.
    """
    if len(encrypted_data) < NONCE_SIZE_BYTES + 16:
        raise BiometricDecryptionError(
            f"Invalid ciphertext: payload length ({len(encrypted_data)} bytes) is shorter "
            f"than minimum header ({NONCE_SIZE_BYTES + 16} bytes)."
        )

    key_bytes = derive_key_bytes(key)
    nonce = encrypted_data[:NONCE_SIZE_BYTES]
    ciphertext_and_tag = encrypted_data[NONCE_SIZE_BYTES:]

    aesgcm = AESGCM(key_bytes)
    try:
        return aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data)
    except InvalidTag as err:
        raise BiometricDecryptionError(
            "Biometric payload authentication failed: invalid tag or ciphertext tampered."
        ) from err
    except Exception as err:
        raise BiometricDecryptionError(f"Biometric decryption failed: {err}") from err


def encrypt_embedding_array(
    embedding: np.ndarray,
    key: Union[str, bytes, None] = None,
    associated_data: Union[bytes, None] = None,
) -> bytes:
    """Serialize a numpy float32 embedding vector and encrypt it with AES-256-GCM.

    Args:
        embedding: Numpy float32 vector (e.g. 192D ECAPA-TDNN embedding).
        key: Optional encryption key.
        associated_data: Optional authenticated data.

    Returns:
        Encrypted payload bytes.
    """
    if not isinstance(embedding, np.ndarray):
        raise TypeError(f"Expected np.ndarray, got {type(embedding).__name__}")

    # Ensure float32 contiguous array
    array = np.ascontiguousarray(embedding, dtype=np.float32)

    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    serialized_bytes = buffer.getvalue()

    return encrypt_vector_payload(serialized_bytes, key=key, associated_data=associated_data)


def decrypt_embedding_array(
    encrypted_bytes: bytes,
    key: Union[str, bytes, None] = None,
    associated_data: Union[bytes, None] = None,
) -> np.ndarray:
    """Decrypt and deserialize an AES-256-GCM encrypted embedding array.

    Args:
        encrypted_bytes: Encrypted payload bytes.
        key: Optional encryption key.
        associated_data: Optional authenticated data.

    Returns:
        Numpy float32 array.

    Raises:
        BiometricDecryptionError: If decryption or deserialization fails.
    """
    decrypted_bytes = decrypt_vector_payload(
        encrypted_bytes,
        key=key,
        associated_data=associated_data,
    )
    buffer = io.BytesIO(decrypted_bytes)
    try:
        array = np.load(buffer, allow_pickle=False)
        return array.astype(np.float32)
    except Exception as err:
        raise BiometricDecryptionError(
            f"Failed to deserialize decrypted vector into numpy array: {err}"
        ) from err


def secure_delete_file(file_path: Union[str, Path]) -> None:
    """Securely overwrite and erase a vector file from disk before unlinking.

    Pass 1: Overwrite with random bytes.
    Pass 2: Overwrite with zeros.
    Pass 3: Unlink file from filesystem.

    Args:
        file_path: Absolute or relative path to the file.
    """
    path = Path(file_path)
    if not path.exists():
        return

    try:
        file_size = path.stat().st_size
        if file_size > 0:
            with open(path, "r+b") as f:
                # Pass 1: Random bytes
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())

                # Pass 2: Zeroes
                f.seek(0)
                f.write(b"\x00" * file_size)
                f.flush()
                os.fsync(f.fileno())
    except Exception:
        # Best effort overwrite; proceed to unlink
        pass
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass

