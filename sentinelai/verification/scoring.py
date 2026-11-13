"""Speaker Similarity Scoring Component for Voice Verification.

Calculates directional cosine similarity between an enrolled reference embedding
and a newly extracted claimant embedding.
"""

from typing import Union
import numpy as np
import torch

from sentinelai.speaker.embedding import SpeakerEmbeddingResult
from sentinelai.speaker.exceptions import InvalidEmbeddingError
from sentinelai.speaker.similarity import compute_cosine_similarity
from sentinelai.verification.exceptions import VerificationScoringError


def compute_verification_score(
    reference_embedding: Union[np.ndarray, torch.Tensor, SpeakerEmbeddingResult],
    claimant_embedding: Union[np.ndarray, torch.Tensor, SpeakerEmbeddingResult],
) -> float:
    """Calculate the cosine similarity between an enrolled reference and a claimant embedding.

    Formula:
        Cosine Similarity = (u · v) / (||u||_2 * ||v||_2)

    CRITICAL SCIENTIFIC NOTE ON SCORE INTERPRETATION:
        The resulting similarity score is a directional geometric metric in [-1.0, 1.0].
        It is NOT a probability, likelihood ratio, or percentage confidence of identity.
        A score of 0.85 does NOT mean "85% confidence that the claimant is the speaker".
        It simply indicates the degree of directional alignment in the ECAPA-TDNN feature
        hyperspace and must be evaluated against a calibrated decision threshold.

    Args:
        reference_embedding: Stored reference voiceprint vector of the enrolled speaker.
        claimant_embedding: Newly extracted voiceprint vector from the claimant recording.

    Returns:
        Scalar float in range [-1.0, 1.0].

    Raises:
        VerificationScoringError: If vectors have mismatched dimensions, contain NaN/Inf,
                                  or are zero-magnitude vectors.
    """
    try:
        score = compute_cosine_similarity(reference_embedding, claimant_embedding)
        # Ensure floating-point clipping to [-1.0, 1.0]
        clipped_score = max(-1.0, min(1.0, float(score)))
        return clipped_score
    except InvalidEmbeddingError as exc:
        raise VerificationScoringError(f"Verification scoring failed: {exc}") from exc
    except Exception as exc:
        raise VerificationScoringError(f"Unexpected scoring failure: {exc}") from exc

