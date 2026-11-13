"""Integration test with the real pretrained SpeechBrain ECAPA-TDNN model.

SCIENTIFIC AND ETHICAL GUARDRAIL:
The audio inputs used in this test are purely synthetic mathematical signals (sine tones)
generated dynamically to verify that the live neural network weights, PyTorch graph,
and feature extraction pipeline execute cleanly on the target CPU environment.
Synthetic tones are NEVER treated as real human speaker recordings, nor used to assert
or fabricate speaker recognition accuracy or Equal Error Rate (EER) benchmarks.
"""

from pathlib import Path
import pytest
import soundfile as sf
import torch

from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.exceptions import ModelLoadError
from sentinelai.speaker.model import ECAPAModelLoader
from sentinelai.speaker.similarity import compute_cosine_similarity


@pytest.mark.integration
class TestECAPAPretrainedIntegration:
    """Integration test suite executing real pretrained ECAPA-TDNN inference on CPU."""

    def test_live_pretrained_ecapa_pipeline_with_synthetic_audio(
        self, synthetic_mono_wav_16k: Path, tmp_path: Path
    ) -> None:
        """Verify real ECAPA-TDNN model loading, embedding extraction, and similarity computation."""
        # Use a localized cache dir inside tmp_path or standard cache
        cache_dir = tmp_path / "ecapa_cache"
        config = SpeakerConfig(
            model_source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=cache_dir,
            device="cpu",
        )
        loader = ECAPAModelLoader(config=config)

        try:
            extractor = SpeakerEmbeddingExtractor(config=config, loader=loader)
            # Extract embedding from synthetic test tone (2.0s sine wave at 16kHz)
            result = extractor.extract(synthetic_mono_wav_16k, source_id="synthetic-tone-1")
        except ModelLoadError as err:
            pytest.skip(
                f"[SentinelAI Integration Notice] Pretrained model download failed "
                f"(network offline or HuggingFace unreachable): {err}. "
                "Skipping live integration test."
            )

        # 1. Verify model loader state
        assert loader.is_loaded is True

        # 2. Verify actual extracted embedding properties
        assert result.embedding.ndim == 1
        assert result.dimension > 0
        # SpeechBrain spkrec-ecapa-voxceleb produces 192-dimensional embeddings
        assert result.dimension == 192
        assert result.device == "cpu"
        assert result.normalized is True
        assert pytest.approx(float(torch.norm(result.embedding_tensor)), abs=1e-4) == 1.0

        # 3. Create a second synthetic audio file (higher frequency tone)
        second_audio_path = tmp_path / "synthetic_second_tone.wav"
        sr = 16000
        import numpy as np
        t = np.linspace(0.0, 2.0, sr * 2, endpoint=False)
        second_signal = (0.5 * np.sin(2.0 * np.pi * 880.0 * t)).astype(np.float32)
        sf.write(str(second_audio_path), second_signal, sr, subtype="PCM_16")

        result2 = extractor.extract(second_audio_path, source_id="synthetic-tone-2")

        # 4. Compute cosine similarity between the two synthetic signals
        similarity = compute_cosine_similarity(result, result2)
        assert isinstance(similarity, float)
        assert -1.0 <= similarity <= 1.0

        # Self-similarity must be exactly 1.0
        self_similarity = compute_cosine_similarity(result, result)
        assert pytest.approx(self_similarity, abs=1e-5) == 1.0

        # Unload model to verify clean memory release on 8GB RAM system
        loader.unload()
        assert loader.is_loaded is False

