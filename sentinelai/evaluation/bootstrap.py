"""Speaker-Level Cluster and Multiway Dyadic Bootstrap Engine.

Implements cluster-based non-parametric bootstrap resampling for speaker verification:
- Resamples speaker identities (clusters) with replacement to account for intra-speaker acoustic correlation.
- Preserves the dyadic pair structure (claimed speaker vs. actual speaker) without artificial cross-replica impostor collisions.
- Recalculates full error curves, continuous Equal Error Rate (EER), ROC-AUC, and operational classification metrics per replicate.
- Quantifies empirical 95% confidence intervals and standard errors.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from sentinelai.evaluation.confidence_intervals import (
    EvaluationConfidenceIntervals,
    MetricConfidenceInterval,
    compute_metric_confidence_interval,
)
from sentinelai.evaluation.metrics import (
    ClassificationMetrics,
    EERResult,
    compute_classification_metrics,
    compute_eer,
    compute_roc_auc,
)
from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial

logger = logging.getLogger(__name__)


@dataclass
class BootstrapResult:
    """Complete summary of the speaker-cluster bootstrap analysis.

    Attributes:
        dataset_name: Evaluated dataset partition.
        iterations_requested: Total bootstrap iterations attempted.
        iterations_valid: Number of successful non-degenerate replicates.
        iterations_skipped: Number of discarded degenerate replicates.
        skip_reasons: Detailed breakdown of skip reasons if any.
        frozen_threshold: Decision threshold held constant during evaluation.
        point_estimates: Original observed point estimates from Phase 5C.
        confidence_intervals: EvaluationConfidenceIntervals instance.
        distributions: Empirical arrays of replicate values for plotting.
        seed: Deterministic random seed used.
    """

    dataset_name: str
    iterations_requested: int
    iterations_valid: int
    iterations_skipped: int
    skip_reasons: List[str]
    frozen_threshold: float
    point_estimates: Dict[str, float]
    confidence_intervals: EvaluationConfidenceIntervals
    distributions: Dict[str, List[float]] = field(default_factory=dict)
    seed: int = 42

    def to_dict(self, include_distributions: bool = False) -> Dict[str, Any]:
        """Convert bootstrap result to JSON-serializable dictionary."""
        data: Dict[str, Any] = {
            "dataset_name": self.dataset_name,
            "resampling_strategy": "speaker_cluster_dyadic_bootstrap",
            "iterations_requested": self.iterations_requested,
            "iterations_valid": self.iterations_valid,
            "iterations_skipped": self.iterations_skipped,
            "skip_reasons": self.skip_reasons,
            "frozen_threshold": round(self.frozen_threshold, 6),
            "point_estimates": {k: round(v, 6) for k, v in self.point_estimates.items()},
            "confidence_intervals": self.confidence_intervals.to_dict(),
            "seed": self.seed,
        }
        if include_distributions:
            data["distributions"] = self.distributions
        return data

    def save_json(self, output_path: Path, include_distributions: bool = False) -> Path:
        """Save bootstrap results to a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(include_distributions=include_distributions), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved bootstrap results to {output_path}")
        return output_path


class SpeakerClusterBootstrap:
    r"""Performs cluster-based non-parametric bootstrap resampling on speaker verification trials.

    Theoretical Foundation:
        Speaker recognition trials violate the standard independent and identically distributed (i.i.d.)
        assumption because individual speakers contribute multiple genuine utterances and participate in
        multiple impostor comparisons. An i.i.d. trial-level bootstrap dramatically underestimates sampling
        variance, generating overconfident confidence intervals.

    Resampling Strategy (Dyadic Speaker Cluster Resampling):
        1. Identify the $K$ unique speakers participating in the trial corpus.
        2. In each iteration $b \in \{1, \dots, B\}$, draw $K$ speaker identities with replacement:
           $S^{*(b)} = \{s_1^*, s_2^*, \dots, s_K^*\}$.
        3. Assign an instance index $m \in \{1, \dots, c(s)\}$ to differentiate duplicate draws of the same speaker,
           preserving the distinct identity of each draw.
        4. Populate Genuine Trials:
           For each sampled instance $(s_i^*, m)$, include all genuine trials where $s_i^*$ was the claimant.
        5. Populate Impostor Trials:
           For each pair of distinct sampled instances $((s_i^*, m), (s_j^*, n))$ where $s_i^* \ne s_j^*$,
           include the cross-speaker impostor trials between claimant $s_i^*$ and probe speaker $s_j^*$.
        6. Within each replicate $b$, recompute:
           - Operational metrics at frozen threshold $\theta^*$: FAR, FRR, Accuracy, Precision, Recall, F1.
           - Continuous linear interpolated EER.
           - ROC-AUC.
    """

    METRIC_NAMES = [
        "far",
        "frr",
        "eer",
        "accuracy",
        "precision",
        "recall",
        "f1_score",
        "roc_auc",
    ]

    def __init__(
        self,
        iterations: int = 1000,
        seed: int = 42,
        confidence_level: float = 0.95,
    ) -> None:
        """Initialize the speaker-cluster bootstrap engine.

        Args:
            iterations: Number of bootstrap iterations (default: 1000).
            seed: Deterministic random seed for reproducibility.
            confidence_level: Nominal confidence level (default: 0.95 for 95% CI).
        """
        self.iterations = max(1, iterations)
        self.seed = seed
        self.confidence_level = confidence_level

    def _index_trials_by_speaker(
        self, trials: List[ScoredTrial]
    ) -> Tuple[List[str], Dict[str, List[ScoredTrial]], Dict[Tuple[str, str], List[ScoredTrial]]]:
        """Index trials into genuine clusters and pairwise impostor dyad clusters.

        Returns:
            Tuple of:
            - Sorted list of unique speaker IDs.
            - Mapping: speaker_id -> list of genuine ScoredTrials.
            - Mapping: (claimed_id, actual_id) -> list of impostor ScoredTrials.
        """
        genuine_by_spk: Dict[str, List[ScoredTrial]] = defaultdict(list)
        impostor_by_dyad: Dict[Tuple[str, str], List[ScoredTrial]] = defaultdict(list)
        all_speakers: Set[str] = set()

        for t in trials:
            all_speakers.add(t.claimed_speaker_id)
            all_speakers.add(t.actual_speaker_id)

            if t.ground_truth_label == 1:
                genuine_by_spk[t.claimed_speaker_id].append(t)
            else:
                impostor_by_dyad[(t.claimed_speaker_id, t.actual_speaker_id)].append(t)

        return sorted(list(all_speakers)), genuine_by_spk, impostor_by_dyad

    def run(
        self,
        dataset: ScoredDataset,
        frozen_threshold: float,
        point_estimates: Optional[Dict[str, float]] = None,
    ) -> BootstrapResult:
        """Execute speaker-cluster bootstrap analysis on the provided scored dataset.

        Args:
            dataset: ScoredDataset containing trials from the evaluation partition.
            frozen_threshold: Calibrated operating threshold held constant.
            point_estimates: Optional pre-calculated point estimates (from Phase 5C).

        Returns:
            BootstrapResult containing empirical metric distributions and 95% confidence intervals.
        """
        rng = np.random.default_rng(self.seed)
        unique_speakers, gen_by_spk, imp_by_dyad = self._index_trials_by_speaker(dataset.trials)
        n_speakers = len(unique_speakers)

        if n_speakers < 2:
            raise ValueError(f"Bootstrap requires at least 2 unique speakers, found {n_speakers}.")

        # Baseline point estimates
        if point_estimates is None:
            base_metrics = compute_classification_metrics(dataset.scores, dataset.labels, threshold=frozen_threshold)
            base_eer = compute_eer(dataset.scores, dataset.labels)
            base_auc = compute_roc_auc(dataset.scores, dataset.labels)
            point_estimates = {
                "far": base_metrics.far,
                "frr": base_metrics.frr,
                "eer": base_eer.eer,
                "accuracy": base_metrics.accuracy,
                "precision": base_metrics.precision,
                "recall": base_metrics.recall,
                "f1_score": base_metrics.f1_score,
                "roc_auc": base_auc,
            }

        logger.info(
            f"Starting speaker-cluster bootstrap: {self.iterations} iterations on {dataset.split_name} "
            f"({n_speakers} speaker clusters, {dataset.total_count} trials, seed={self.seed})..."
        )

        distributions: Dict[str, List[float]] = {k: [] for k in self.METRIC_NAMES}
        skip_reasons: List[str] = []
        valid_replicates = 0

        for b in range(self.iterations):
            # Step 1: Draw n_speakers speaker identities with replacement
            sampled_indices = rng.integers(0, n_speakers, size=n_speakers)
            sampled_speakers = [unique_speakers[idx] for idx in sampled_indices]

            # Step 2: Track instances of duplicate draws
            speaker_instances: List[Tuple[str, int]] = []
            instance_counts: Dict[str, int] = defaultdict(int)
            for spk in sampled_speakers:
                instance_counts[spk] += 1
                speaker_instances.append((spk, instance_counts[spk]))

            # Step 3: Collect genuine trials for all sampled instances
            rep_scores: List[float] = []
            rep_labels: List[int] = []

            for spk, _ in speaker_instances:
                for t in gen_by_spk.get(spk, []):
                    rep_scores.append(t.similarity_score)
                    rep_labels.append(1)

            # Step 4: Collect impostor trials between distinct speaker pairs
            # For each distinct pair of drawn instances where spk_i != spk_j
            n_inst = len(speaker_instances)
            for i in range(n_inst):
                spk_i, _ = speaker_instances[i]
                for j in range(n_inst):
                    if i == j:
                        continue
                    spk_j, _ = speaker_instances[j]
                    if spk_i == spk_j:
                        continue  # Two draws of the same speaker do not form impostor comparisons
                    dyad_trials = imp_by_dyad.get((spk_i, spk_j), [])
                    for t in dyad_trials:
                        rep_scores.append(t.similarity_score)
                        rep_labels.append(0)

            # Check for degenerate sample
            arr_scores = np.asarray(rep_scores, dtype=np.float64)
            arr_labels = np.asarray(rep_labels, dtype=np.int64)

            n_gen = int(np.sum(arr_labels == 1))
            n_imp = int(np.sum(arr_labels == 0))

            if n_gen == 0 or n_imp == 0:
                skip_reasons.append(f"Replicate {b}: Degenerate sample with n_gen={n_gen}, n_imp={n_imp}")
                continue

            # Step 5: Evaluate metrics for valid replicate
            try:
                op_metrics = compute_classification_metrics(arr_scores, arr_labels, threshold=frozen_threshold)
                eer_res = compute_eer(arr_scores, arr_labels)
                auc_val = compute_roc_auc(arr_scores, arr_labels)

                distributions["far"].append(op_metrics.far)
                distributions["frr"].append(op_metrics.frr)
                distributions["eer"].append(eer_res.eer)
                distributions["accuracy"].append(op_metrics.accuracy)
                distributions["precision"].append(op_metrics.precision)
                distributions["recall"].append(op_metrics.recall)
                distributions["f1_score"].append(op_metrics.f1_score)
                distributions["roc_auc"].append(auc_val)

                valid_replicates += 1
            except Exception as exc:
                skip_reasons.append(f"Replicate {b}: Evaluation failed: {exc}")

        skipped_replicates = len(skip_reasons)
        logger.info(
            f"Speaker-cluster bootstrap complete: {valid_replicates}/{self.iterations} valid replicates "
            f"({skipped_replicates} skipped)"
        )

        # Step 6: Compute empirical 95% confidence intervals
        ci_dict: Dict[str, MetricConfidenceInterval] = {}
        for m_name in self.METRIC_NAMES:
            vals = distributions[m_name]
            pt = point_estimates.get(m_name, float(np.mean(vals)) if vals else 0.0)
            ci_dict[m_name] = compute_metric_confidence_interval(
                metric_name=m_name,
                point_estimate=pt,
                replicates=vals,
                confidence_level=self.confidence_level,
            )

        ci_container = EvaluationConfidenceIntervals(
            dataset_name=dataset.split_name,
            resampling_unit="speaker_cluster",
            iterations=self.iterations,
            valid_replicates=valid_replicates,
            metrics=ci_dict,
            metadata={
                "strategy": "dyadic_multiway_speaker_cluster_bootstrap",
                "frozen_threshold": frozen_threshold,
                "confidence_level": self.confidence_level,
                "seed": self.seed,
            },
        )

        return BootstrapResult(
            dataset_name=dataset.split_name,
            iterations_requested=self.iterations,
            iterations_valid=valid_replicates,
            iterations_skipped=skipped_replicates,
            skip_reasons=skip_reasons[:20],  # Keep top 20
            frozen_threshold=frozen_threshold,
            point_estimates=point_estimates,
            confidence_intervals=ci_container,
            distributions=distributions,
            seed=self.seed,
        )
