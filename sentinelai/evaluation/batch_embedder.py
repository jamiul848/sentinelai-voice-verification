"""Batch Embedding Extraction for Large-Scale Speaker Evaluation.

Extracts ECAPA-TDNN speaker embeddings for all recordings in an evaluation split,
with progress reporting, disk caching for resumability, and memory-efficient
serial processing suitable for CPU-only systems.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor, SpeakerEmbeddingResult
from sentinelai.speaker.model import ECAPAModelLoader

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingCacheEntry:
    """Single cached embedding with metadata.

    Attributes:
        speaker_id: Speaker identity.
        recording_path: Original audio file path.
        embedding: 1D float32 NumPy array.
        dimension: Embedding dimensionality.
        model_id: Model identifier used for extraction.
        audio_duration_sec: Duration of the source audio.
        extraction_time_sec: Wall-clock time for this extraction.
    """

    speaker_id: str
    recording_path: str
    embedding: np.ndarray
    dimension: int
    model_id: str
    audio_duration_sec: float
    extraction_time_sec: float


@dataclass
class BatchExtractionResult:
    """Result of batch embedding extraction for an evaluation split.

    Attributes:
        split_name: Name of the split (e.g. 'dev-clean').
        embeddings: Mapping from recording filename stem to EmbeddingCacheEntry.
        total_extracted: Number of embeddings successfully extracted.
        total_skipped: Number of embeddings loaded from cache.
        total_failed: Number of recordings that failed extraction.
        failed_recordings: List of (path, error_message) tuples for failed files.
        total_extraction_time_sec: Total wall-clock time for all extractions.
        embedding_dimension: Detected embedding dimensionality.
        model_id: Model identifier used.
        device: Inference device used.
    """

    split_name: str
    embeddings: Dict[str, EmbeddingCacheEntry] = field(default_factory=dict)
    total_extracted: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    failed_recordings: List[Dict[str, str]] = field(default_factory=list)
    total_extraction_time_sec: float = 0.0
    embedding_dimension: int = 0
    model_id: str = ""
    device: str = ""


class BatchEmbedder:
    """Extracts speaker embeddings for all recordings in an evaluation split.

    Features:
        - Single model load: reuses the same ECAPAModelLoader instance across all extractions.
        - Disk caching: saves embeddings to .npz files for resumability.
        - Progress reporting: logs extraction progress at configurable intervals.
        - Memory-efficient serial processing suitable for CPU-only 8GB RAM systems.
        - Graceful failure handling: logs errors per recording without aborting the batch.
    """

    def __init__(
        self,
        output_dir: Path,
        config: Optional[SpeakerConfig] = None,
        loader: Optional[ECAPAModelLoader] = None,
        progress_interval: int = 50,
    ) -> None:
        """Initialize the batch embedder.

        Args:
            output_dir: Directory to cache extracted embeddings (.npz files).
            config: Optional SpeakerConfig for the extractor.
            loader: Optional shared ECAPAModelLoader instance.
            progress_interval: Log progress every N recordings.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or SpeakerConfig()
        self.loader = loader or ECAPAModelLoader(config=self.config)
        self.progress_interval = max(1, progress_interval)
        self._extractor: Optional[SpeakerEmbeddingExtractor] = None

    def _get_extractor(self) -> SpeakerEmbeddingExtractor:
        """Lazily create the embedding extractor, reusing the shared model loader."""
        if self._extractor is None:
            self._extractor = SpeakerEmbeddingExtractor(
                config=self.config, loader=self.loader
            )
        return self._extractor

    def _cache_path(self, recording_path: Path) -> Path:
        """Generate the .npz cache path for a recording."""
        return self.output_dir / f"{recording_path.stem}.npz"

    def _load_cached(self, cache_file: Path) -> Optional[np.ndarray]:
        """Load a cached embedding from disk if it exists and is valid."""
        if not cache_file.exists():
            return None
        try:
            data = np.load(str(cache_file))
            emb = data["embedding"]
            if emb.ndim == 1 and emb.size > 0 and np.isfinite(emb).all():
                return emb.astype(np.float32)
        except Exception as exc:
            logger.warning(f"Cache file {cache_file} corrupted, re-extracting: {exc}")
        return None

    def _save_cached(self, cache_file: Path, embedding: np.ndarray, metadata: Dict[str, Any]) -> None:
        """Save an embedding and metadata to disk as .npz."""
        np.savez(
            str(cache_file),
            embedding=embedding,
            **{k: np.array(v) if isinstance(v, (int, float)) else np.array(str(v))
               for k, v in metadata.items()},
        )

    def extract_batch(
        self,
        recordings: List[Path],
        speaker_ids: Dict[str, str],
        split_name: str,
        skip_cached: bool = True,
    ) -> BatchExtractionResult:
        """Extract embeddings for a batch of recordings.

        Args:
            recordings: List of audio file paths to process.
            speaker_ids: Mapping from recording filename stem to speaker_id.
            split_name: Name of the split for logging.
            skip_cached: If True, skip recordings with valid cached embeddings.

        Returns:
            BatchExtractionResult with all extracted embeddings and statistics.
        """
        result = BatchExtractionResult(
            split_name=split_name,
            model_id=self.config.model_source,
            device=self.config.resolved_device,
        )

        total = len(recordings)
        logger.info(
            f"[{split_name}] Starting batch embedding extraction: "
            f"{total} recordings, device={self.config.resolved_device}"
        )

        extractor = self._get_extractor()
        batch_start = time.time()

        for idx, rec_path in enumerate(recordings, 1):
            stem = rec_path.stem
            spk_id = speaker_ids.get(stem, "unknown")
            cache_file = self._cache_path(rec_path)

            # Try loading from cache
            if skip_cached:
                cached_emb = self._load_cached(cache_file)
                if cached_emb is not None:
                    result.embeddings[stem] = EmbeddingCacheEntry(
                        speaker_id=spk_id,
                        recording_path=str(rec_path),
                        embedding=cached_emb,
                        dimension=int(cached_emb.shape[0]),
                        model_id=self.config.model_source,
                        audio_duration_sec=0.0,  # Not stored in cache
                        extraction_time_sec=0.0,
                    )
                    result.total_skipped += 1

                    if result.embedding_dimension == 0:
                        result.embedding_dimension = int(cached_emb.shape[0])

                    continue

            # Extract embedding
            t0 = time.time()
            try:
                emb_result: SpeakerEmbeddingResult = extractor.extract(
                    source=rec_path, source_id=stem
                )
                elapsed = time.time() - t0

                result.embeddings[stem] = EmbeddingCacheEntry(
                    speaker_id=spk_id,
                    recording_path=str(rec_path),
                    embedding=emb_result.embedding,
                    dimension=emb_result.dimension,
                    model_id=emb_result.model_id,
                    audio_duration_sec=emb_result.audio_duration_sec,
                    extraction_time_sec=elapsed,
                )
                result.total_extracted += 1

                if result.embedding_dimension == 0:
                    result.embedding_dimension = emb_result.dimension

                # Cache to disk
                self._save_cached(
                    cache_file,
                    emb_result.embedding,
                    {"speaker_id": spk_id, "dimension": emb_result.dimension},
                )

            except Exception as exc:
                elapsed = time.time() - t0
                result.total_failed += 1
                result.failed_recordings.append({
                    "path": str(rec_path),
                    "speaker_id": spk_id,
                    "error": str(exc),
                })
                logger.error(
                    f"[{split_name}] Failed to extract embedding for {rec_path.name}: {exc}"
                )

            # Progress reporting
            if idx % self.progress_interval == 0 or idx == total:
                elapsed_total = time.time() - batch_start
                rate = idx / elapsed_total if elapsed_total > 0 else 0
                eta_sec = (total - idx) / rate if rate > 0 else 0
                logger.info(
                    f"[{split_name}] Progress: {idx}/{total} "
                    f"({100 * idx / total:.1f}%) | "
                    f"Rate: {rate:.1f} rec/s | "
                    f"ETA: {eta_sec / 60:.1f} min"
                )

        result.total_extraction_time_sec = time.time() - batch_start
        logger.info(
            f"[{split_name}] Batch extraction complete: "
            f"{result.total_extracted} extracted, "
            f"{result.total_skipped} cached, "
            f"{result.total_failed} failed, "
            f"dimension={result.embedding_dimension}, "
            f"time={result.total_extraction_time_sec:.1f}s"
        )

        return result

