"""Reference Embedding Aggregation for Voice Enrollment.

Combines multiple utterance embedding vectors into a single L2-normalized reference
voiceprint centroid vector.
"""

from dataclasses import dataclass
from typing import Any, Dict, List
import numpy as np

from sentinelai.enrollment.exceptions import AggregationError


@dataclass
class AggregationResult:
    """Container holding the aggregated reference embedding and consistency diagnostics.

    Attributes:
        reference_embedding: 1D float32 NumPy array representing the L2-normalized centroid.
        individual_embeddings: List of the original valid 1D float32 embedding arrays.
        dimension: Dimensionality of the vectors.
        sample_count: Number of embeddings combined.
        mean_pairwise_similarity: Average cosine similarity among the enrollment samples.
        min_pairwise_similarity: Minimum pairwise similarity (detects outlier recordings).
        metrics: Diagnostic metrics (dispersion, intra-session consistency).
    """

    reference_embedding: np.ndarray
    individual_embeddings: List[np.ndarray]
    dimension: int
    sample_count: int
    mean_pairwise_similarity: float
    min_pairwise_similarity: float
    metrics: Dict[str, Any]


def aggregate_embeddings(embeddings: List[np.ndarray], eps: float = 1e-12) -> AggregationResult:
    """Aggregate multiple speaker embeddings into a single L2-normalized reference centroid.

    Methodology:
        1. Compute the arithmetic mean vector:
           m = (1 / K) * sum_{i=1}^K e_i
        2. Apply L2 unit length normalization:
           e_ref = m / ||m||_2
        3. Evaluate intra-utterance consistency by computing pairwise cosine similarities.

    Limitations of Mean-Based Aggregation:
        - Assumes a unimodal, symmetric acoustic distribution on the hypersphere.
        - Susceptible to outliers: an utterance contaminated with acoustic noise or
          unusual vocal strain will skew the mean away from the genuine speaker center.
        - Does not model multimodal speaker variance (e.g. whispered vs. shouted speech,
          emotional state, or diurnal vocal register drift).
        - Aggregation produces a representative central estimate, but does not automatically
          guarantee superior verification accuracy across non-stationary acoustic domains.

    Args:
        embeddings: List of 1D NumPy float32 arrays, all sharing identical dimensionality.
        eps: Epsilon threshold for numerical stability.

    Returns:
        AggregationResult containing the normalized reference embedding and metrics.

    Raises:
        AggregationError: If list is empty, dimensions mismatch, or vectors contain non-finite numbers.
    """
    if not embeddings:
        raise AggregationError("Cannot aggregate an empty list of embeddings.")

    sample_count = len(embeddings)
    clean_embeddings: List[np.ndarray] = []

    # Step 1: Validate input vector shapes, dimensions, and finite values
    expected_dim = embeddings[0].shape[0] if embeddings[0].ndim == 1 else None
    if expected_dim is None or expected_dim == 0:
        raise AggregationError(f"First embedding has invalid shape {embeddings[0].shape}.")

    for idx, emb in enumerate(embeddings):
        if not isinstance(emb, np.ndarray):
            raise AggregationError(f"Embedding at index {idx} is not a NumPy array (got {type(emb).__name__}).")

        arr = emb.astype(np.float64, copy=False).ravel()

        if arr.shape[0] != expected_dim:
            raise AggregationError(
                f"Embedding dimension mismatch at index {idx}: expected {expected_dim} dimensions, "
                f"got {arr.shape[0]} dimensions."
            )

        if np.isnan(arr).any():
            raise AggregationError(f"Embedding at index {idx} contains NaN values.")

        if np.isinf(arr).any():
            raise AggregationError(f"Embedding at index {idx} contains Infinite values.")

        norm = float(np.linalg.norm(arr))
        if norm < eps:
            raise AggregationError(f"Embedding at index {idx} is a zero-vector or degenerate.")

        clean_embeddings.append(arr)

    # Step 2: Calculate arithmetic mean vector across all enrollment utterances
    stacked = np.vstack(clean_embeddings)  # Shape: (K, D)
    mean_vector = np.mean(stacked, axis=0)  # Shape: (D,)

    # Step 3: Apply L2 normalization to project mean onto unit hypersphere
    mean_norm = float(np.linalg.norm(mean_vector))
    if mean_norm < eps:
        raise AggregationError(
            f"Mean embedding vector has zero norm ({mean_norm:.2e}). "
            "Vectors may be mutually canceling or degenerate."
        )

    ref_embedding = (mean_vector / mean_norm).astype(np.float32)

    # Step 4: Calculate intra-enrollment pairwise cosine similarities and dispersion
    pairwise_similarities: List[float] = []
    if sample_count > 1:
        # Normalize rows to ensure exact cosine product
        norms = np.linalg.norm(stacked, axis=1, keepdims=True)
        normalized_stacked = stacked / np.maximum(norms, eps)
        similarity_matrix = np.dot(normalized_stacked, normalized_stacked.T)

        # Extract upper triangle without diagonal
        for i in range(sample_count):
            for j in range(i + 1, sample_count):
                sim = float(np.clip(similarity_matrix[i, j], -1.0, 1.0))
                pairwise_similarities.append(sim)

        mean_sim = float(np.mean(pairwise_similarities))
        min_sim = float(np.min(pairwise_similarities))
    else:
        mean_sim = 1.0
        min_sim = 1.0

    # Calculate standard deviation across samples (measure of intra-session acoustic spread)
    std_spread = float(np.mean(np.std(stacked, axis=0)))

    metrics = {
        "sample_count": sample_count,
        "mean_norm_before_l2": mean_norm,
        "intra_session_std_spread": round(std_spread, 6),
        "mean_pairwise_similarity": round(mean_sim, 4),
        "min_pairwise_similarity": round(min_sim, 4),
    }

    # Store individual embeddings as float32
    float32_individual = [e.astype(np.float32) for e in clean_embeddings]

    return AggregationResult(
        reference_embedding=ref_embedding,
        individual_embeddings=float32_individual,
        dimension=expected_dim,
        sample_count=sample_count,
        mean_pairwise_similarity=round(mean_sim, 4),
        min_pairwise_similarity=round(min_sim, 4),
        metrics=metrics,
    )

