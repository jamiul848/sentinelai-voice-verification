"""Speaker Embedding Cosine Similarity Engine.

Calculates directional similarity between two speaker embeddings with strict
dimensional, numerical, and zero-vector safety checks.
"""

from typing import Union
import numpy as np
import torch

from sentinelai.speaker.embedding import SpeakerEmbeddingResult
from sentinelai.speaker.exceptions import InvalidEmbeddingError


def _to_1d_numpy(embedding: Union[np.ndarray, torch.Tensor, SpeakerEmbeddingResult], param_name: str) -> np.ndarray:
    """Convert an embedding input into a clean 1D float64 NumPy array.

    Args:
        embedding: NumPy array, PyTorch Tensor, or SpeakerEmbeddingResult.
        param_name: Variable name for error reporting.

    Returns:
        1D float64 NumPy array.

    Raises:
        InvalidEmbeddingError: If input is empty, has invalid shape, or contains non-finite values.
    """
    arr: np.ndarray

    if isinstance(embedding, SpeakerEmbeddingResult):
        arr = embedding.embedding
    elif isinstance(embedding, torch.Tensor):
        arr = embedding.detach().cpu().numpy()
    elif isinstance(embedding, np.ndarray):
        arr = embedding
    else:
        raise InvalidEmbeddingError(
            f"Invalid type for {param_name}: expected np.ndarray, torch.Tensor, or "
            f"SpeakerEmbeddingResult, got {type(embedding).__name__}."
        )

    # Flatten if needed and cast to float64 for high numerical precision
    arr = arr.astype(np.float64, copy=False).ravel()

    if arr.size == 0:
        raise InvalidEmbeddingError(f"{param_name} is empty (0 elements).")

    if np.isnan(arr).any():
        raise InvalidEmbeddingError(f"{param_name} contains invalid numerical values: NaN detected.")

    if np.isinf(arr).any():
        raise InvalidEmbeddingError(f"{param_name} contains invalid numerical values: Infinity detected.")

    return arr


def compute_cosine_similarity(
    embedding_a: Union[np.ndarray, torch.Tensor, SpeakerEmbeddingResult],
    embedding_b: Union[np.ndarray, torch.Tensor, SpeakerEmbeddingResult],
    eps: float = 1e-12,
) -> float:
    """Calculate the cosine similarity between two speaker voiceprint embeddings.

    Mathematical definition:
        cos(theta) = (u . v) / (||u||_2 * ||v||_2)

    Score Interpretation:
        - +1.0 : Perfect directional alignment (identical embedding vectors).
        - ~0.0 : Orthogonal vectors (no directional acoustic correlation).
        - -1.0 : Diametrically opposite vectors.
        - Higher values indicate greater acoustic voiceprint similarity.

    IMPORTANT ARCHITECTURAL NOTE:
        Cosine similarity measures directional alignment in the embedding hyperspace.
        It does NOT independently prove identity or constitute a definitive biometric
        decision without calibrated decision thresholding, multi-utterance enrollment,
        and anti-spoofing verification.

    Args:
        embedding_a: First speaker embedding (array, tensor, or SpeakerEmbeddingResult).
        embedding_b: Second speaker embedding (array, tensor, or SpeakerEmbeddingResult).
        eps: Epsilon threshold to detect degenerate zero-norm vectors.

    Returns:
        Scalar float representing cosine similarity, clamped to [-1.0, 1.0].

    Raises:
        InvalidEmbeddingError: If vectors have mismatched dimensions, are zero vectors,
                               or contain non-finite numbers (NaN/Inf).
    """
    vec_a = _to_1d_numpy(embedding_a, param_name="embedding_a")
    vec_b = _to_1d_numpy(embedding_b, param_name="embedding_b")

    # Step 1: Validate dimensional congruence
    dim_a = vec_a.shape[0]
    dim_b = vec_b.shape[0]
    if dim_a != dim_b:
        raise InvalidEmbeddingError(
            f"Embedding dimension mismatch: embedding_a has {dim_a} dimensions, "
            f"but embedding_b has {dim_b} dimensions. Both embeddings must share "
            "the same dimensionality to compute similarity."
        )

    # Step 2: Compute norms and check for degenerate zero vectors
    norm_a = float(np.linalg.norm(vec_a))
    norm_b = float(np.linalg.norm(vec_b))

    if norm_a < eps:
        raise InvalidEmbeddingError(
            f"embedding_a is a zero vector or degenerate embedding (norm={norm_a:.2e}). "
            "Cannot calculate directional cosine similarity for zero vectors."
        )

    if norm_b < eps:
        raise InvalidEmbeddingError(
            f"embedding_b is a zero vector or degenerate embedding (norm={norm_b:.2e}). "
            "Cannot calculate directional cosine similarity for zero vectors."
        )

    # Step 3: Compute dot product and normalized cosine similarity
    dot_product = float(np.dot(vec_a, vec_b))
    raw_similarity = dot_product / (norm_a * norm_b)

    # Step 4: Clip minor floating-point deviations strictly to [-1.0, 1.0]
    clamped_similarity = float(np.clip(raw_similarity, -1.0, 1.0))

    return clamped_similarity

