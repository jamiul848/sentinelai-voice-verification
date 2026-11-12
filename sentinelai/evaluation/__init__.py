"""SentinelAI Evaluation and Benchmark Module.

Provides:
- Phase 5A: Dataset inspection, audio acoustic validation, demographic annotation, overlap detection.
- Phase 5B: Speaker discovery, deterministic enrollment partitioning, trial generation, leakage validation.
- Phase 5C: Trial scoring, threshold calibration, EER/FAR/FRR/ROC-AUC computation, frozen test evaluation,
            visualization rendering, and formal research reporting.
"""

from sentinelai.evaluation.batch_embedder import (
    BatchEmbedder,
    BatchExtractionResult,
    EmbeddingCacheEntry,
)
from sentinelai.evaluation.dataset_inspector import DatasetInspector
from sentinelai.evaluation.dataset_report import (
    AudioFileInfo,
    DatasetInspectionReport,
    SpeakerSummary,
    SplitInspectionReport,
    format_duration,
)
from sentinelai.evaluation.evaluation_report import (
    EvaluationReportGenerator,
    SplitEvaluationSummary,
)
from sentinelai.evaluation.evaluator import (
    EvaluationPipelineResult,
    SpeakerVerificationEvaluator,
)
from sentinelai.evaluation.leakage_validator import LeakageValidator, ValidationResult
from sentinelai.evaluation.metrics import (
    ClassificationMetrics,
    EERResult,
    FarFrrCurve,
    compute_classification_metrics,
    compute_det_coordinates,
    compute_eer,
    compute_far_frr_curve,
    compute_roc_auc,
)
from sentinelai.evaluation.speaker_discovery import (
    EnrollmentSelector,
    EnrollmentSplit,
    SpeakerRecordingDiscovery,
    SpeakerRecordings,
    SplitDiscoveryResult,
)
from sentinelai.evaluation.threshold_calibrator import (
    CalibratedThresholdMetadata,
    ThresholdCalibrator,
)
from sentinelai.evaluation.trial_generator import (
    TrialGenerationResult,
    TrialGenerator,
    VerificationTrial,
)
from sentinelai.evaluation.trial_manifest import TrialManifestWriter
from sentinelai.evaluation.trial_scorer import ScoredDataset, ScoredTrial, TrialScorer
from sentinelai.evaluation.visualizer import EvaluationVisualizer

__all__ = [
    # Phase 5A
    "DatasetInspector",
    "DatasetInspectionReport",
    "SplitInspectionReport",
    "AudioFileInfo",
    "SpeakerSummary",
    "format_duration",
    # Phase 5B
    "SpeakerRecordingDiscovery",
    "SpeakerRecordings",
    "EnrollmentSelector",
    "EnrollmentSplit",
    "SplitDiscoveryResult",
    "TrialGenerator",
    "TrialGenerationResult",
    "VerificationTrial",
    "TrialManifestWriter",
    "LeakageValidator",
    "ValidationResult",
    "BatchEmbedder",
    "BatchExtractionResult",
    "EmbeddingCacheEntry",
    # Phase 5C
    "FarFrrCurve",
    "EERResult",
    "ClassificationMetrics",
    "compute_far_frr_curve",
    "compute_eer",
    "compute_roc_auc",
    "compute_classification_metrics",
    "compute_det_coordinates",
    "CalibratedThresholdMetadata",
    "ThresholdCalibrator",
    "ScoredTrial",
    "ScoredDataset",
    "TrialScorer",
    "EvaluationVisualizer",
    "SplitEvaluationSummary",
    "EvaluationReportGenerator",
    "EvaluationPipelineResult",
    "SpeakerVerificationEvaluator",
]
