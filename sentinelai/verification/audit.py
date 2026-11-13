"""Privacy-Preserving Audit Logging for Speaker Verification Events.

Maintains an immutable, append-only log of verification transactions without
retaining raw audio, embedding vectors, or sensitive biometric representations.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from sentinelai.verification.exceptions import AuditLoggingError


@dataclass
class AuditRecord:
    """Structured representation of a verification audit event.

    CRITICAL PRIVACY INVARIANT:
        This record must NEVER contain raw audio waveforms, numpy arrays,
        speech tensors, biometric embedding vectors, or cryptographic secrets.
    """

    verification_id: str
    user_id: str
    profile_id: str
    status: str
    verified: bool
    threshold_version: str
    model_name: str
    timestamp: str
    processing_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to a JSON-serializable dictionary."""
        return asdict(self)


class AuditLoggerBackend(ABC):
    """Abstract interface defining operations for recording verification events."""

    @abstractmethod
    def log_verification(self, record: AuditRecord) -> None:
        """Persist a single verification audit record."""
        pass


class JsonLinesAuditLogger(AuditLoggerBackend):
    """Thread-safe append-only JSON lines logger for verification events."""

    def __init__(self, log_path: Path) -> None:
        """Initialize the audit logger.

        Args:
            log_path: Path to the target .jsonl audit file.
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log_verification(self, record: AuditRecord) -> None:
        """Write a single audit record as a JSON line to disk.

        Args:
            record: AuditRecord instance.

        Raises:
            AuditLoggingError: If write operation fails.
        """
        data = record.to_dict()

        # Enforce biometric sanitization checks
        for forbidden_key in ("embedding", "reference_embedding", "tensor", "audio", "bytes"):
            if forbidden_key in data or forbidden_key in data.get("metadata", {}):
                raise AuditLoggingError(
                    f"Biometric privacy violation: Audit payload contains forbidden key '{forbidden_key}'."
                )

        line = json.dumps(data, ensure_ascii=False) + "\n"
        with self._lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception as exc:
                raise AuditLoggingError(f"Failed to append audit record to '{self.log_path}': {exc}") from exc


class InMemoryAuditLogger(AuditLoggerBackend):
    """In-memory audit logger for testing and high-speed mock environments."""

    def __init__(self) -> None:
        self.records = []
        self._lock = Lock()

    def log_verification(self, record: AuditRecord) -> None:
        with self._lock:
            self.records.append(record)

