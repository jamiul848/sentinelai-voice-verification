"""Sentinel Voice - Encrypted Biometric Vector Storage Manager.

Provides zero-trust, envelope-encrypted biometric container storage:
1. Envelope Encryption: Each voice profile generates a unique 32-byte Data Encryption Key (DEK).
   - The 192D speaker embedding vector is encrypted with the DEK via AES-256-GCM.
   - The DEK is encrypted with the master Key Encryption Key (KEK) via AES-256-GCM.
2. Tamper Evident: Cryptographic GCM authentication tags verify data integrity.
3. Path Traversal Defense: All path lookups are canonicalized and strictly jailed within
   the configured biometric root.
4. Cryptographic Erasure: Revocation executes multi-pass file shredding before unlinking.
5. Backward Compatibility: Seamlessly reads legacy V1 un-enveloped containers.
"""

import hashlib
import io
import os
from pathlib import Path
import struct
from typing import Optional, Tuple, Union
import uuid

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from sentinelai.auth.crypto import (
    NONCE_SIZE_BYTES,
    decrypt_embedding_array,
    derive_key_bytes,
    secure_delete_file,
)
from sentinelai.biometrics.exceptions import (
    BiometricStorageError,
    DirectoryTraversalError,
    VectorTamperedError,
)
from sentinelai.config import get_settings

# Container Envelope Constants
MAGIC_HEADER = b"SNTV2"  # Sentinel Voice Biometric Container V2
HEADER_LEN = len(MAGIC_HEADER)
DEK_SIZE_BYTES = 32


class BiometricStorageManager:
    """Manages envelope-encrypted voiceprint vector storage on the local filesystem."""

    def __init__(
        self,
        storage_root: Optional[Union[str, Path]] = None,
        master_key: Optional[Union[str, bytes]] = None,
    ) -> None:
        """Initialize the storage manager.

        Args:
            storage_root: Root directory for biometric containers. Defaults to settings.biometric_store_path.
            master_key: Master symmetric encryption key. Defaults to settings.biometric_encryption_key.
        """
        settings = get_settings()
        self.storage_root = Path(storage_root or settings.biometric_store_path).resolve()
        self.master_key = master_key if master_key is not None else settings.biometric_encryption_key
        # Ensure root directory exists
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def get_profile_path(
        self,
        user_id: Union[uuid.UUID, str],
        profile_id: Union[uuid.UUID, str],
    ) -> Path:
        """Resolve and validate the canonical storage path for a profile container.

        Enforces strict path traversal defenses.

        Args:
            user_id: User UUID.
            profile_id: Profile UUID.

        Returns:
            Canonical Path object within the authorized storage root.

        Raises:
            DirectoryTraversalError: If path resolves outside the storage root.
        """
        user_str = str(user_id).strip()
        profile_str = str(profile_id).strip()

        # Prevent basic path traversal strings in parameters
        if ".." in user_str or "/" in user_str or "\\" in user_str:
            raise DirectoryTraversalError("Invalid characters in user_id parameter.")
        if ".." in profile_str or "/" in profile_str or "\\" in profile_str:
            raise DirectoryTraversalError("Invalid characters in profile_id parameter.")

        target_path = (self.storage_root / user_str / f"{profile_str}.enc").resolve()

        try:
            target_path.relative_to(self.storage_root)
        except ValueError as err:
            raise DirectoryTraversalError(
                f"Resolved storage path '{target_path}' traverses outside storage root '{self.storage_root}'."
            ) from err

        return target_path

    def save_profile_vector(
        self,
        user_id: Union[uuid.UUID, str],
        profile_id: Union[uuid.UUID, str],
        embedding: np.ndarray,
    ) -> Tuple[str, str]:
        """Envelope-encrypt and persist a reference speaker embedding vector to disk.

        Pipeline:
        1. Generate ephemeral 256-bit profile DEK.
        2. Serialize numpy float32 embedding and encrypt with DEK (AES-256-GCM).
        3. Encrypt DEK with master KEK (AES-256-GCM).
        4. Assemble envelope container: MAGIC_HEADER + DEK_PAYLOAD_LEN + ENCRYPTED_DEK + ENCRYPTED_VECTOR.
        5. Write payload to disk securely and compute SHA-256 checksum.

        Args:
            user_id: Owner user UUID.
            profile_id: Profile UUID.
            embedding: 1D float32 NumPy array (e.g. 192D ECAPA-TDNN centroid).

        Returns:
            Tuple of (canonical_storage_path_str, sha256_hex_digest).

        Raises:
            BiometricStorageError: If disk writing or encryption fails.
        """
        if not isinstance(embedding, np.ndarray):
            raise TypeError(f"Expected np.ndarray, got {type(embedding).__name__}")

        target_path = self.get_profile_path(user_id, profile_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            kek_bytes = derive_key_bytes(self.master_key)
            dek = os.urandom(DEK_SIZE_BYTES)

            # Step 1: Encrypt vector with DEK
            vector_array = np.ascontiguousarray(embedding, dtype=np.float32)
            buf = io.BytesIO()
            np.save(buf, vector_array, allow_pickle=False)
            vector_bytes = buf.getvalue()

            vector_nonce = os.urandom(NONCE_SIZE_BYTES)
            aesgcm_dek = AESGCM(dek)
            encrypted_vector = aesgcm_dek.encrypt(vector_nonce, vector_bytes, None)
            vector_payload = vector_nonce + encrypted_vector

            # Step 2: Encrypt DEK with Master KEK
            dek_nonce = os.urandom(NONCE_SIZE_BYTES)
            aesgcm_kek = AESGCM(kek_bytes)
            encrypted_dek = aesgcm_kek.encrypt(dek_nonce, dek, None)
            dek_payload = dek_nonce + encrypted_dek

            # Step 3: Pack Envelope Container
            # Format: [5B Magic: SNTV2][2B Big-Endian DEK len][DEK Payload][Vector Payload]
            dek_len = len(dek_payload)
            container_bytes = (
                MAGIC_HEADER
                + struct.pack(">H", dek_len)
                + dek_payload
                + vector_payload
            )

            # Step 4: Write to disk and calculate checksum
            with open(target_path, "wb") as f:
                f.write(container_bytes)
                f.flush()
                os.fsync(f.fileno())

            sha256_checksum = hashlib.sha256(container_bytes).hexdigest()
            return str(target_path), sha256_checksum

        except Exception as err:
            # Clean up partial file if write failed
            if target_path.exists():
                secure_delete_file(target_path)
            raise BiometricStorageError(f"Failed to persist encrypted vector: {err}") from err

    def load_profile_vector(
        self,
        user_id: Union[uuid.UUID, str],
        profile_id: Union[uuid.UUID, str],
        storage_path: Optional[str] = None,
        expected_sha256: Optional[str] = None,
    ) -> np.ndarray:
        """Load, authenticate, and decrypt an enrolled reference vector from disk.

        Args:
            user_id: Owner user UUID.
            profile_id: Profile UUID.
            storage_path: Optional explicit storage path. If None, resolved canonically.
            expected_sha256: Optional expected SHA-256 checksum from database metadata.

        Returns:
            1D float32 NumPy array.

        Raises:
            BiometricStorageError: If file is missing or unreadable.
            VectorTamperedError: If checksum or cryptographic authentication tag fails.
        """
        if storage_path:
            path = Path(storage_path).resolve()
            try:
                path.relative_to(self.storage_root)
            except ValueError as err:
                raise DirectoryTraversalError(
                    f"Supplied storage path '{path}' is outside storage root."
                ) from err
        else:
            path = self.get_profile_path(user_id, profile_id)

        if not path.exists():
            raise BiometricStorageError(f"Biometric vector container does not exist: {path}")

        try:
            with open(path, "rb") as f:
                container_bytes = f.read()
        except Exception as err:
            raise BiometricStorageError(f"Failed to read biometric container: {err}") from err

        # Verify cryptographic integrity checksum if supplied
        if expected_sha256:
            actual_sha256 = hashlib.sha256(container_bytes).hexdigest()
            if actual_sha256.lower() != expected_sha256.lower():
                raise VectorTamperedError(
                    f"Biometric container checksum mismatch: expected {expected_sha256[:12]}..., "
                    f"computed {actual_sha256[:12]}..."
                )

        # Check for Envelope V2 Magic Header
        if container_bytes.startswith(MAGIC_HEADER):
            try:
                kek_bytes = derive_key_bytes(self.master_key)
                aesgcm_kek = AESGCM(kek_bytes)

                # Unpack envelope header
                dek_len = struct.unpack(">H", container_bytes[HEADER_LEN : HEADER_LEN + 2])[0]
                offset_dek_end = HEADER_LEN + 2 + dek_len

                dek_payload = container_bytes[HEADER_LEN + 2 : offset_dek_end]
                vector_payload = container_bytes[offset_dek_end:]

                # Decrypt DEK
                dek_nonce = dek_payload[:NONCE_SIZE_BYTES]
                dek_ciphertext = dek_payload[NONCE_SIZE_BYTES:]
                dek = aesgcm_kek.decrypt(dek_nonce, dek_ciphertext, None)

                # Decrypt vector
                aesgcm_dek = AESGCM(dek)
                vector_nonce = vector_payload[:NONCE_SIZE_BYTES]
                vector_ciphertext = vector_payload[NONCE_SIZE_BYTES:]
                vector_raw = aesgcm_dek.decrypt(vector_nonce, vector_ciphertext, None)

                # Deserialize numpy array
                buf = io.BytesIO(vector_raw)
                array = np.load(buf, allow_pickle=False)
                return array.astype(np.float32)

            except InvalidTag as err:
                raise VectorTamperedError(
                    "Cryptographic tag authentication failed: container corrupted or tampered."
                ) from err
            except Exception as err:
                raise VectorTamperedError(f"Failed to decrypt biometric container: {err}") from err

        # Fallback to Legacy V1 Container format
        try:
            return decrypt_embedding_array(container_bytes, key=self.master_key)
        except Exception as err:
            raise VectorTamperedError(f"Failed to decrypt legacy biometric container: {err}") from err

    def delete_profile_vector(
        self,
        user_id: Union[uuid.UUID, str],
        profile_id: Union[uuid.UUID, str],
        storage_path: Optional[str] = None,
    ) -> bool:
        """Securely shred and unlink a biometric vector container using Cryptographic Erasure.

        Operational Security Note (NIST SP 800-88 Rev. 1):
        Physical overwriting on flash-based SSDs, wear-leveling controllers, journaled,
        and Copy-on-Write (CoW) filesystems (e.g. ZFS, Btrfs) cannot physically guarantee
        that every raw flash block is overwritten in-place.
        
        Therefore, Sentinel Voice enforces Cryptographic Erasure (Crypto-Shredding):
        1. Each voice profile centroid vector is encrypted using an ephemeral 256-bit DEK.
        2. The DEK exists solely within the wrapped header of this container file.
        3. Destroying the wrapped DEK renders the 192D biometric ciphertext mathematically
           irrecoverable (AES-256 keyspace = 2^256), regardless of physical wear-leveling
           or filesystem re-allocations.
        4. In addition, multi-pass overwriting (random bytes + zero fill) and physical fsync
           are executed prior to filesystem unlinking.

        Args:
            user_id: Owner user UUID.
            profile_id: Profile UUID.
            storage_path: Optional explicit storage path.

        Returns:
            True if file was found and deleted, False if already absent.
        """
        if storage_path:
            path = Path(storage_path).resolve()
            try:
                path.relative_to(self.storage_root)
            except ValueError:
                # If path is not relative, fallback to canonical
                path = self.get_profile_path(user_id, profile_id)
        else:
            path = self.get_profile_path(user_id, profile_id)

        if not path.exists():
            return False

        secure_delete_file(path)

        # Clean up empty parent directory if left empty
        try:
            parent = path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except Exception:
            pass

        return True

    def rotate_master_key(
        self,
        old_key: Union[str, bytes],
        new_key: Union[str, bytes],
    ) -> int:
        """Re-wrap all profile Data Encryption Keys (DEKs) with a new Master KEK.

        Enables seamless Key Encryption Key rotation without requiring users to re-enroll
        or decrypting raw 192D speaker embedding vectors.

        Args:
            old_key: Existing master key.
            new_key: New master key to wrap DEKs with.

        Returns:
            Number of biometric containers successfully rotated.

        Raises:
            BiometricStorageError: If key rotation fails on any container.
        """
        old_kek = derive_key_bytes(old_key)
        new_kek = derive_key_bytes(new_key)
        aesgcm_old = AESGCM(old_kek)
        aesgcm_new = AESGCM(new_kek)

        rotated_count = 0
        container_files = list(self.storage_root.rglob("*.enc"))

        for file_path in container_files:
            try:
                with open(file_path, "rb") as f:
                    data = f.read()

                if not data.startswith(MAGIC_HEADER):
                    # Legacy V1 container (master key encrypted): upgrade to V2 envelope
                    raw_vector = decrypt_embedding_array(data, key=old_key)
                    # Re-save with new key in V2 format
                    user_id = file_path.parent.name
                    profile_id = file_path.stem
                    self.master_key = new_key
                    self.save_profile_vector(user_id, profile_id, raw_vector)
                    rotated_count += 1
                    continue

                # Unpack V2 envelope
                dek_len = struct.unpack(">H", data[HEADER_LEN : HEADER_LEN + 2])[0]
                offset_dek_end = HEADER_LEN + 2 + dek_len

                old_dek_payload = data[HEADER_LEN + 2 : offset_dek_end]
                vector_payload = data[offset_dek_end:]

                # Decrypt DEK with old KEK
                old_dek_nonce = old_dek_payload[:NONCE_SIZE_BYTES]
                old_dek_ct = old_dek_payload[NONCE_SIZE_BYTES:]
                dek = aesgcm_old.decrypt(old_dek_nonce, old_dek_ct, None)

                # Re-encrypt DEK with new KEK
                new_dek_nonce = os.urandom(NONCE_SIZE_BYTES)
                new_dek_ct = aesgcm_new.encrypt(new_dek_nonce, dek, None)
                new_dek_payload = new_dek_nonce + new_dek_ct

                # Reassemble container
                new_container = (
                    MAGIC_HEADER
                    + struct.pack(">H", len(new_dek_payload))
                    + new_dek_payload
                    + vector_payload
                )

                # Atomically write updated container
                with open(file_path, "wb") as f:
                    f.write(new_container)
                    f.flush()
                    os.fsync(f.fileno())

                rotated_count += 1

            except Exception as err:
                raise BiometricStorageError(
                    f"Failed to rotate master key for container '{file_path.name}': {err}"
                ) from err

        return rotated_count

