"""Configuration settings for the SentinelAI Speaker Recognition and ECAPA-TDNN module."""

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import torch


class SpeakerConfig(BaseModel):
    """Configuration model for ECAPA-TDNN model loading and speaker embedding extraction.

    Attributes:
        model_source: Pretrained Hugging Face repository or local path for ECAPA-TDNN.
            Default: "speechbrain/spkrec-ecapa-voxceleb" (ECAPA-TDNN trained on VoxCeleb 1 & 2).
        savedir: Local directory for downloading and caching model weights.
        device: Device selection ("auto", "cpu", or "cuda"). "auto" selects CUDA if available, else CPU.
        expected_sample_rate: Required acoustic sample rate in Hz (16000 for ECAPA-TDNN).
        normalize_embeddings: Whether to apply L2 unit length normalization to extracted embeddings.
    """

    model_source: str = Field(
        default="speechbrain/spkrec-ecapa-voxceleb",
        description="SpeechBrain pretrained model identifier or local checkpoint path.",
    )
    savedir: Path = Field(
        default=Path(".cache/sentinelai/ecapa_tdnn"),
        description="Local directory for downloading and caching model weights.",
    )
    device: Literal["auto", "cpu", "cuda"] = Field(
        default="auto",
        description="Compute device: 'auto' uses GPU if available, else CPU.",
    )
    expected_sample_rate: int = Field(
        default=16000,
        gt=0,
        description="Sample rate in Hz required by the pretrained ECAPA-TDNN model.",
    )
    normalize_embeddings: bool = Field(
        default=True,
        description="If True, scales embedding vectors to unit L2 norm (||e||_2 = 1.0).",
    )

    @field_validator("savedir", mode="before")
    @classmethod
    def convert_savedir_to_path(cls, v: object) -> Path:
        """Convert string paths to Path instances."""
        if isinstance(v, str):
            return Path(v)
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_device_availability(self) -> "SpeakerConfig":
        """Explicitly validate CUDA availability if CUDA was specifically requested."""
        if self.device == "cuda" and not torch.cuda.is_available():
            raise ValueError(
                "CUDA device was explicitly requested in SpeakerConfig, but CUDA is not available "
                "on this system. Configure device='cpu' or device='auto' instead."
            )
        return self

    @property
    def resolved_device(self) -> str:
        """Resolve 'auto' device to 'cuda' (if torch.cuda.is_available()) or 'cpu'."""
        if self.device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return self.device

    @property
    def torch_device(self) -> torch.device:
        """Return resolved torch.device instance."""
        return torch.device(self.resolved_device)
