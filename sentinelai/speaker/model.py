"""Pretrained ECAPA-TDNN Model Loader for SentinelAI.

Manages downloading, local caching, device selection, and lifecycle management
for the SpeechBrain 'spkrec-ecapa-voxceleb' model.
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Optional
import torch

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.exceptions import ModelLoadError

logger = logging.getLogger(__name__)


class ECAPAModelLoader:
    """Singleton-friendly loader for the SpeechBrain ECAPA-TDNN speaker recognition model.

    Features:
    - Lazy loading and thread-safe in-memory caching to avoid repeated multi-second initialization.
    - Automatic hardware device selection (CPU on laptops, CUDA when a compatible GPU is available).
    - Clear exception handling with actionable error messages for network or caching failures.
    - Memory management utilities (is_loaded, unload) suitable for constrained memory environments.
    """

    def __init__(self, config: Optional[SpeakerConfig] = None) -> None:
        """Initialize the model loader with configuration.

        Args:
            config: Optional SpeakerConfig. If None, default settings are used.
        """
        self.config = config or SpeakerConfig()
        self._model: Optional[object] = None
        self._lock = Lock()

    @property
    def is_loaded(self) -> bool:
        """Return True if the model weights are currently loaded in memory."""
        return self._model is not None

    def get_device(self) -> torch.device:
        """Return the active PyTorch device configured for the model."""
        return self.config.torch_device

    def load(self, force_reload: bool = False) -> object:
        """Load and return the pretrained ECAPA-TDNN model instance.

        If the model is already loaded and force_reload is False, returns the cached instance.

        Args:
            force_reload: If True, forces re-initialization of the model.

        Returns:
            SpeechBrain EncoderClassifier model instance.

        Raises:
            ModelLoadError: If the model cannot be loaded, downloaded, or initialized.
        """
        with self._lock:
            if self._model is not None and not force_reload:
                return self._model

            device_str = self.config.resolved_device
            savedir = Path(self.config.savedir)

            logger.info(
                f"Loading ECAPA-TDNN model from '{self.config.model_source}' "
                f"(cache dir: {savedir}, device: {device_str})..."
            )

            try:
                import warnings
                # Suppress Windows symlink UserWarning from SpeechBrain fetching on Windows
                warnings.filterwarnings("ignore", message=".*symlink.*", category=UserWarning)

                # Import SpeechBrain inference module lazily
                from speechbrain.inference.speaker import EncoderClassifier

                savedir.mkdir(parents=True, exist_ok=True)

                model = EncoderClassifier.from_hparams(
                    source=self.config.model_source,
                    savedir=str(savedir),
                    run_opts={"device": device_str},
                )
                if hasattr(model, "eval"):
                    model.eval()
                self._model = model
                logger.info("ECAPA-TDNN model successfully loaded and ready for inference.")
                return self._model
            except Exception as exc:
                self._model = None
                error_msg = (
                    f"Failed to load pretrained ECAPA-TDNN model '{self.config.model_source}' "
                    f"to device '{device_str}': {exc}. "
                    "Ensure an active internet connection is available for initial download, "
                    "or verify that the cache directory is writable."
                )
                logger.error(error_msg, exc_info=True)
                raise ModelLoadError(error_msg, details={"source": self.config.model_source, "device": device_str}) from exc

    def unload(self) -> None:
        """Unload model from memory and trigger garbage collection.

        Useful on memory-constrained systems (e.g. 8 GB RAM) when speaker verification
        is not actively running.
        """
        with self._lock:
            if self._model is not None:
                del self._model
                self._model = None
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logger.info("ECAPA-TDNN model unloaded from memory.")


# Module-level default singleton loader instance
_default_loader: Optional[ECAPAModelLoader] = None
_singleton_lock = Lock()


def get_model_loader(config: Optional[SpeakerConfig] = None) -> ECAPAModelLoader:
    """Retrieve or create the shared default ECAPAModelLoader singleton."""
    global _default_loader
    with _singleton_lock:
        if _default_loader is None or config is not None:
            _default_loader = ECAPAModelLoader(config=config)
        return _default_loader
