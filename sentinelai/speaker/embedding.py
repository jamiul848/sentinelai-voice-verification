"""Speaker Embedding Extraction using Pretrained ECAPA-TDNN.

Extracts fixed-dimensional speaker voiceprint embeddings from raw audio files,
streams, or preprocessed PyTorch FloatTensors.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
from pathlib import Path
from typing import Any, Dict, Optional, Union
import numpy as np
import torch

from sentinelai.audio.preprocessor import AudioPreprocessingResult, AudioPreprocessor
from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.exceptions import EmbeddingExtractionError, InvalidEmbeddingError
from sentinelai.speaker.model import ECAPAModelLoader, get_model_loader


@dataclass
class SpeakerEmbeddingResult:
    """Structured container returned by the SpeakerEmbeddingExtractor.

    Attributes:
        embedding: 1D NumPy float32 array representing the speaker embedding vector.
        embedding_tensor: 1D PyTorch float32 Tensor on CPU.
        dimension: Number of dimensions in the embedding vector (e.g. 192 for ECAPA-TDNN).
        model_id: Identifier of the pretrained SpeechBrain model used.
        device: Hardware device used for inference ("cpu" or "cuda").
        audio_duration_sec: Duration in seconds of the source audio used for extraction.
        extraction_timestamp: ISO 8601 UTC timestamp of extraction.
        normalized: Whether L2 unit normalization (||e||_2 = 1.0) was applied.
        metadata: Additional diagnostic metadata (sample rate, source info).
    """

    embedding: np.ndarray
    embedding_tensor: torch.Tensor
    dimension: int
    model_id: str
    device: str
    audio_duration_sec: float
    extraction_timestamp: str
    normalized: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result summary into a JSON-serializable dictionary."""
        return {
            "model_id": self.model_id,
            "dimension": self.dimension,
            "device": self.device,
            "audio_duration_sec": round(self.audio_duration_sec, 4),
            "extraction_timestamp": self.extraction_timestamp,
            "normalized": self.normalized,
            "embedding_l2_norm": float(np.linalg.norm(self.embedding)),
            "metadata": self.metadata,
        }


class SpeakerEmbeddingExtractor:
    """Extracts speaker embeddings using the pretrained ECAPA-TDNN model.

    Pipeline:
    1. Preprocesses input audio (or accepts preprocessed tensor) to enforce 16 kHz mono.
    2. Sends audio tensor of shape [1, N] to SpeechBrain ECAPA-TDNN model.
    3. Extracts speaker embedding vector using model.encode_batch().
    4. Validates shape, finiteness (no NaN/Inf), and dimension count.
    5. Applies optional L2 unit length normalization (||e||_2 = 1.0).
    6. Constructs structured SpeakerEmbeddingResult.
    """

    def __init__(
        self,
        config: Optional[SpeakerConfig] = None,
        loader: Optional[ECAPAModelLoader] = None,
        preprocessor: Optional[AudioPreprocessor] = None,
    ) -> None:
        """Initialize the SpeakerEmbeddingExtractor.

        Args:
            config: Optional SpeakerConfig.
            loader: Optional ECAPAModelLoader instance.
            preprocessor: Optional AudioPreprocessor instance.
        """
        self.config = config or SpeakerConfig()
        self.loader = loader or get_model_loader(config=self.config)
        self.preprocessor = preprocessor or AudioPreprocessor()

    def _validate_embedding_array(self, emb: np.ndarray) -> None:
        """Verify numerical integrity and finiteness of the extracted embedding.

        Args:
            emb: Extracted embedding array.

        Raises:
            InvalidEmbeddingError: If embedding contains NaNs, Infs, or has zero length.
        """
        if emb.size == 0:
            raise InvalidEmbeddingError("Extracted embedding is empty (0 dimensions).")

        if np.isnan(emb).any():
            raise InvalidEmbeddingError("Extracted embedding contains invalid numerical values: NaN detected.")

        if np.isinf(emb).any():
            raise InvalidEmbeddingError("Extracted embedding contains invalid numerical values: Infinity detected.")

    @staticmethod
    def normalize_l2(embedding: np.ndarray, eps: float = 1e-12) -> np.ndarray:
        """Apply L2 unit length normalization to an embedding vector.

        Projects the vector onto the unit hypersphere: e_norm = e / ||e||_2.
        In this space, cosine similarity simplifies to the Euclidean dot product.

        Args:
            embedding: 1D NumPy array representing the speaker embedding.
            eps: Epsilon floor to prevent division by zero.

        Returns:
            1D NumPy array with Euclidean norm equal to 1.0.

        Raises:
            InvalidEmbeddingError: If the embedding is a zero vector.
        """
        norm = float(np.linalg.norm(embedding))
        if norm < eps:
            raise InvalidEmbeddingError(
                f"Cannot L2-normalize zero vector or degenerate embedding (norm={norm:.2e})."
            )
        normalized = embedding / norm
        return normalized.astype(np.float32)

    def extract(
        self,
        source: Union[str, Path, bytes, io.BytesIO, AudioPreprocessingResult, torch.Tensor],
        source_id: Optional[str] = None,
    ) -> SpeakerEmbeddingResult:
        """Extract a fixed-dimensional speaker embedding from an audio input.

        Args:
            source: Audio file path, raw WAV bytes, stream, AudioPreprocessingResult,
                    or a 1D/2D PyTorch FloatTensor sampled at 16000 Hz.
            source_id: Optional identifier for logging and traceability.

        Returns:
            SpeakerEmbeddingResult containing the embedding and diagnostic metadata.

        Raises:
            EmbeddingExtractionError: If inference fails on the model.
            InvalidEmbeddingError: If output embedding is degenerate or non-finite.
            SentinelAudioError: If input audio fails preprocessing validation.
        """
        audio_tensor: torch.Tensor
        duration_sec: float

        # Step 1: Preprocess or prepare audio tensor
        if isinstance(source, AudioPreprocessingResult):
            audio_tensor = source.audio_tensor
            duration_sec = source.duration_sec
        elif isinstance(source, torch.Tensor):
            # Tensor input: assert dimensions
            if source.ndim == 1:
                audio_tensor = source.unsqueeze(0).float()
            elif source.ndim == 2:
                audio_tensor = source.float()
            else:
                raise EmbeddingExtractionError(
                    f"Expected 1D or 2D audio tensor, got shape {source.shape} (ndim={source.ndim})."
                )
            duration_sec = float(audio_tensor.shape[1] / self.config.expected_sample_rate)
        else:
            # File path, bytes, or BytesIO stream -> route through AudioPreprocessor
            prep_result = self.preprocessor.process(source, source_id=source_id)
            audio_tensor = prep_result.audio_tensor
            duration_sec = prep_result.duration_sec

        # Ensure audio tensor is on the active model device
        device = self.loader.get_device()
        audio_tensor = audio_tensor.to(device)

        # Step 2: Load model (cached)
        model = self.loader.load()

        # Step 3: Extract embedding via ECAPA-TDNN forward pass
        try:
            with torch.no_grad():
                # SpeechBrain EncoderClassifier.encode_batch expects shape [batch, time_steps]
                # Output shape is typically [batch, 1, emb_dim] or [batch, emb_dim]
                raw_out = model.encode_batch(audio_tensor)
        except Exception as exc:
            raise EmbeddingExtractionError(
                f"ECAPA-TDNN embedding inference failed on device '{device}': {exc}"
            ) from exc

        # Step 4: Convert to clean 1D CPU tensor and NumPy array
        # Squeeze batch and channel singleton dimensions
        emb_tensor_cpu = raw_out.squeeze().detach().cpu().float()
        if emb_tensor_cpu.ndim != 1:
            # In case shape had extra dimensions, flatten to 1D
            emb_tensor_cpu = emb_tensor_cpu.flatten()

        emb_numpy = emb_tensor_cpu.numpy().astype(np.float32)

        # Step 5: Validate numerical integrity
        self._validate_embedding_array(emb_numpy)

        # Dynamically record embedding dimension from actual model output
        actual_dimension = int(emb_numpy.shape[0])

        # Step 6: Apply L2 normalization if enabled
        is_normalized = False
        if self.config.normalize_embeddings:
            emb_numpy = self.normalize_l2(emb_numpy)
            emb_tensor_cpu = torch.from_numpy(emb_numpy).float()
            is_normalized = True

        timestamp_utc = datetime.now(timezone.utc).isoformat()

        metadata: Dict[str, Any] = {
            "source_id": source_id,
            "source_type": type(source).__name__,
            "model_source": self.config.model_source,
            "sample_rate_hz": self.config.expected_sample_rate,
        }

        return SpeakerEmbeddingResult(
            embedding=emb_numpy,
            embedding_tensor=emb_tensor_cpu,
            dimension=actual_dimension,
            model_id=self.config.model_source,
            device=str(device),
            audio_duration_sec=duration_sec,
            extraction_timestamp=timestamp_utc,
            normalized=is_normalized,
            metadata=metadata,
        )

