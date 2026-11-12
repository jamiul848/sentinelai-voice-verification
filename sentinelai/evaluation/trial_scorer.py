"""Trial Scorer for Speaker Verification Evaluation.

Pairs enrolled reference speaker embeddings with verification probe embeddings,
computes directional cosine similarity, validates scores, and writes score manifests
without exposing sensitive biometric embedding vectors.
"""

import csv
from dataclasses import asdict, dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from sentinelai.evaluation.trial_manifest import TrialManifestWriter
from sentinelai.verification.scoring import compute_verification_score

logger = logging.getLogger(__name__)


@dataclass
class ScoredTrial:
    """A scored verification trial containing metadata, ground truth, and cosine score.

    Attributes:
        trial_id: Unique identifier for the trial.
        claimed_speaker_id: Claimed enrolled speaker identity.
        actual_speaker_id: True speaker identity of the probe recording.
        trial_type: 'genuine' (same speaker) or 'impostor' (different speaker).
        ground_truth_label: 1 for genuine, 0 for impostor.
        similarity_score: Cosine similarity in [-1.0, 1.0].
        split: Dataset split name (e.g. 'dev-clean').
        model_identifier: Model used for feature extraction.
        score_source: Provenance metadata ('real_ecapa_inference' vs 'synthetic_demonstration').
    """

    trial_id: str
    claimed_speaker_id: str
    actual_speaker_id: str
    trial_type: str
    ground_truth_label: int
    similarity_score: float
    split: str
    model_identifier: str
    score_source: str = "real_ecapa_inference"


@dataclass
class ScoredDataset:
    """Aggregated container of scored trials with extracted NumPy arrays for metric evaluation.

    Attributes:
        split_name: Name of the dataset split (e.g. 'dev-clean').
        trials: List of all ScoredTrial instances.
        scores: 1D NumPy array of all similarity scores.
        labels: 1D NumPy array of all ground-truth binary labels.
        model_identifier: Model identifier.
    """

    split_name: str
    trials: List[ScoredTrial] = field(default_factory=list)
    scores: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float64))
    labels: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))
    model_identifier: str = ""

    @property
    def genuine_scores(self) -> np.ndarray:
        """Return 1D array of similarity scores for genuine trials."""
        return self.scores[self.labels == 1]

    @property
    def impostor_scores(self) -> np.ndarray:
        """Return 1D array of similarity scores for impostor trials."""
        return self.scores[self.labels == 0]

    @property
    def genuine_count(self) -> int:
        """Count of genuine trials."""
        return int(np.sum(self.labels == 1))

    @property
    def impostor_count(self) -> int:
        """Count of impostor trials."""
        return int(np.sum(self.labels == 0))

    @property
    def total_count(self) -> int:
        """Total trial count."""
        return len(self.trials)


class TrialScorer:
    """Evaluates trial manifests against enrolled reference embeddings and probe embeddings.

    Produces sanitized score manifests suitable for performance analysis.
    """

    SCORE_CSV_COLUMNS = [
        "trial_id",
        "claimed_speaker_id",
        "actual_speaker_id",
        "trial_type",
        "ground_truth_label",
        "similarity_score",
        "split",
        "model_identifier",
        "score_source",
    ]

    def __init__(self, model_identifier: str = "speechbrain/spkrec-ecapa-voxceleb") -> None:
        """Initialize the TrialScorer.

        Args:
            model_identifier: Pretrained model identifier string.
        """
        self.model_identifier = model_identifier

    def score_trials(
        self,
        trial_rows: List[Dict[str, Any]],
        reference_embeddings: Dict[str, np.ndarray],
        probe_embeddings: Dict[str, np.ndarray],
        split_name: str,
    ) -> ScoredDataset:
        """Score a list of trial rows using loaded embeddings.

        Args:
            trial_rows: List of trial dictionaries (from trials.csv).
            reference_embeddings: Mapping from speaker_id -> 1D reference embedding.
            probe_embeddings: Mapping from recording stem -> 1D probe embedding.
            split_name: Dataset split name.

        Returns:
            ScoredDataset containing all scored trials and score/label arrays.

        Raises:
            KeyError: If a claimed speaker or probe recording is missing from embeddings.
            ValueError: If a trial score is non-finite or empty.
        """
        scored_trials: List[ScoredTrial] = []
        score_list: List[float] = []
        label_list: List[int] = []

        total_trials = len(trial_rows)
        logger.info(f"[{split_name}] Scoring {total_trials} verification trials...")

        for idx, row in enumerate(trial_rows):
            trial_id = str(row["trial_id"])
            claimed_id = str(row["claimed_speaker_id"])
            actual_id = str(row["actual_speaker_id"])
            trial_type = str(row["trial_type"])
            label = int(row["ground_truth_label"])
            probe_id = str(row["verification_recording_id"])

            # 1. Retrieve reference embedding
            if claimed_id not in reference_embeddings:
                raise KeyError(
                    f"Claimed speaker '{claimed_id}' not found in reference embeddings "
                    f"for trial {trial_id}."
                )
            ref_emb = reference_embeddings[claimed_id]

            # 2. Retrieve probe recording embedding
            if probe_id not in probe_embeddings:
                raise KeyError(
                    f"Verification recording '{probe_id}' not found in probe embeddings "
                    f"for trial {trial_id}."
                )
            probe_emb = probe_embeddings[probe_id]

            # 3. Calculate cosine similarity
            score = compute_verification_score(ref_emb, probe_emb)

            if not np.isfinite(score):
                raise ValueError(
                    f"Trial {trial_id} produced non-finite score {score}."
                )

            # 4. Construct ScoredTrial
            scored = ScoredTrial(
                trial_id=trial_id,
                claimed_speaker_id=claimed_id,
                actual_speaker_id=actual_id,
                trial_type=trial_type,
                ground_truth_label=label,
                similarity_score=round(score, 6),
                split=split_name,
                model_identifier=self.model_identifier,
                score_source="real_ecapa_inference",
            )

            scored_trials.append(scored)
            score_list.append(score)
            label_list.append(label)

        scores_arr = np.asarray(score_list, dtype=np.float64)
        labels_arr = np.asarray(label_list, dtype=np.int64)

        logger.info(
            f"[{split_name}] Completed scoring: {len(scored_trials)} trials "
            f"(genuine={np.sum(labels_arr == 1)}, impostor={np.sum(labels_arr == 0)}), "
            f"score range: [{np.min(scores_arr):.4f}, {np.max(scores_arr):.4f}]"
        )

        return ScoredDataset(
            split_name=split_name,
            trials=scored_trials,
            scores=scores_arr,
            labels=labels_arr,
            model_identifier=self.model_identifier,
        )

    def write_scores_csv(
        self,
        scored_dataset: ScoredDataset,
        output_path: Path,
    ) -> Path:
        """Write scored trials to a CSV manifest without raw embedding vectors.

        Args:
            scored_dataset: ScoredDataset instance.
            output_path: Target CSV file path.

        Returns:
            Path to the written CSV file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.SCORE_CSV_COLUMNS)
            writer.writeheader()

            for t in scored_dataset.trials:
                row = {
                    "trial_id": t.trial_id,
                    "claimed_speaker_id": t.claimed_speaker_id,
                    "actual_speaker_id": t.actual_speaker_id,
                    "trial_type": t.trial_type,
                    "ground_truth_label": t.ground_truth_label,
                    "similarity_score": t.similarity_score,
                    "split": t.split,
                    "model_identifier": t.model_identifier,
                    "score_source": getattr(t, "score_source", "real_ecapa_inference"),
                }
                writer.writerow(row)

        logger.info(f"Wrote {len(scored_dataset.trials)} scores to {output_path}")
        return output_path

    def load_scores_csv(
        self,
        csv_path: Path,
        split_name: Optional[str] = None,
        allow_synthetic: bool = False,
    ) -> ScoredDataset:
        """Load previously scored trials from a CSV manifest into a ScoredDataset.

        Args:
            csv_path: Path to scores.csv.
            split_name: Optional split name override.
            allow_synthetic: Whether to accept synthetic demonstration scores. Defaults to False.

        Returns:
            ScoredDataset instance.

        Raises:
            FileNotFoundError: If csv_path does not exist.
            ValueError: If synthetic demonstration scores are detected when allow_synthetic is False.
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Score manifest not found at {csv_path}")

        scored_trials: List[ScoredTrial] = []
        score_list: List[float] = []
        label_list: List[int] = []
        detected_split = split_name or "unknown"
        detected_model = self.model_identifier

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trial_id = str(row["trial_id"])
                score_source = row.get("score_source", "unknown")

                # Stale synthetic score detection
                if not allow_synthetic:
                    if trial_id.startswith("synth-") or score_source == "synthetic_demonstration":
                        raise ValueError(
                            f"Stale synthetic score manifest detected at {csv_path} (trial_id={trial_id!r}, "
                            f"score_source={score_source!r}). Real benchmark execution requires genuine "
                            f"ECAPA-TDNN inference. Set allow_synthetic=True or --demo-mode if demonstration scores "
                            f"are explicitly intended."
                        )

                score = float(row["similarity_score"])
                label = int(row["ground_truth_label"])
                trial = ScoredTrial(
                    trial_id=trial_id,
                    claimed_speaker_id=row["claimed_speaker_id"],
                    actual_speaker_id=row["actual_speaker_id"],
                    trial_type=row["trial_type"],
                    ground_truth_label=label,
                    similarity_score=score,
                    split=row.get("split", detected_split),
                    model_identifier=row.get("model_identifier", detected_model),
                    score_source=score_source,
                )
                scored_trials.append(trial)
                score_list.append(score)
                label_list.append(label)
                detected_split = trial.split
                detected_model = trial.model_identifier

        return ScoredDataset(
            split_name=split_name or detected_split,
            trials=scored_trials,
            scores=np.asarray(score_list, dtype=np.float64),
            labels=np.asarray(label_list, dtype=np.int64),
            model_identifier=detected_model,
        )

