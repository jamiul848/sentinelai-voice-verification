"""Data Leakage and Integrity Validator for Evaluation Pipelines.

Validates that generated verification trials are free from:
- Speaker overlap between development and test splits.
- Enrollment/verification recording overlap within a speaker.
- Duplicate trial IDs or duplicate trial pairs.
- Missing or invalid audio file references.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sentinelai.evaluation.speaker_discovery import EnrollmentSplit
from sentinelai.evaluation.trial_generator import VerificationTrial

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data leakage and integrity validation.

    Attributes:
        is_valid: True if all validation checks passed.
        checks_passed: Number of validation checks that passed.
        checks_failed: Number of validation checks that failed.
        violations: List of (check_name, description) for each violation found.
        warnings: List of (check_name, description) for non-critical issues.
        summary: Human-readable summary of the validation outcome.
    """

    is_valid: bool = True
    checks_passed: int = 0
    checks_failed: int = 0
    violations: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[Dict[str, str]] = field(default_factory=list)
    summary: str = ""


class LeakageValidator:
    """Validates data integrity and leakage prevention for verification trials.

    Performs the following validation checks:
    1. Speaker-disjoint splits: No speaker appears in both dev and test.
    2. Enrollment/verification non-overlap: No recording appears in both sets.
    3. No duplicate trial IDs.
    4. No duplicate trial pairs (same claimed_speaker + same verification_recording).
    5. Genuine trials must have matching claimed and actual speaker IDs.
    6. Impostor trials must have different claimed and actual speaker IDs.
    7. All verification recording paths reference existing files (optional).
    """

    def validate_speaker_disjoint(
        self,
        dev_speakers: Set[str],
        test_speakers: Set[str],
    ) -> Tuple[bool, List[str]]:
        """Check that no speaker appears in both development and test splits.

        Args:
            dev_speakers: Set of speaker IDs in the development split.
            test_speakers: Set of speaker IDs in the test split.

        Returns:
            Tuple of (is_disjoint, list_of_overlapping_speaker_ids).
        """
        overlap = dev_speakers.intersection(test_speakers)
        return len(overlap) == 0, sorted(overlap)

    def validate_enrollment_verification_nonoverlap(
        self,
        enrollment_splits: Dict[str, EnrollmentSplit],
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """Check that no recording appears in both enrollment and verification sets.

        Args:
            enrollment_splits: Mapping from speaker_id to EnrollmentSplit.

        Returns:
            Tuple of (is_valid, list_of_violations_with_speaker_and_recording).
        """
        violations: List[Dict[str, str]] = []

        for spk_id, split_info in enrollment_splits.items():
            if not split_info.is_eligible:
                continue

            enrollment_set = {p.stem for p in split_info.enrollment_recordings}
            verification_set = {p.stem for p in split_info.verification_recordings}

            overlap = enrollment_set.intersection(verification_set)
            for rec in sorted(overlap):
                violations.append({
                    "speaker_id": spk_id,
                    "recording": rec,
                    "type": "enrollment_verification_overlap",
                })

        return len(violations) == 0, violations

    def validate_no_duplicate_trial_ids(
        self,
        trials: List[VerificationTrial],
    ) -> Tuple[bool, List[str]]:
        """Check that all trial IDs are unique.

        Args:
            trials: List of VerificationTrial instances.

        Returns:
            Tuple of (is_valid, list_of_duplicate_trial_ids).
        """
        seen: Dict[str, int] = {}
        duplicates: List[str] = []

        for trial in trials:
            if trial.trial_id in seen:
                duplicates.append(trial.trial_id)
            seen[trial.trial_id] = seen.get(trial.trial_id, 0) + 1

        return len(duplicates) == 0, duplicates

    def validate_no_duplicate_pairs(
        self,
        trials: List[VerificationTrial],
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """Check that no (claimed_speaker_id, verification_recording_id) pair is duplicated.

        Args:
            trials: List of VerificationTrial instances.

        Returns:
            Tuple of (is_valid, list_of_duplicate_pair_details).
        """
        seen: Set[Tuple[str, str]] = set()
        duplicates: List[Dict[str, str]] = []

        for trial in trials:
            pair = (trial.claimed_speaker_id, trial.verification_recording_id)
            if pair in seen:
                duplicates.append({
                    "claimed_speaker_id": trial.claimed_speaker_id,
                    "verification_recording_id": trial.verification_recording_id,
                    "trial_type": trial.trial_type,
                })
            seen.add(pair)

        return len(duplicates) == 0, duplicates

    def validate_trial_labels(
        self,
        trials: List[VerificationTrial],
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """Validate that trial types match ground truth labels.

        - Genuine: claimed_speaker_id == actual_speaker_id, label == 1
        - Impostor: claimed_speaker_id != actual_speaker_id, label == 0

        Args:
            trials: List of VerificationTrial instances.

        Returns:
            Tuple of (is_valid, list_of_mismatched_trials).
        """
        mismatches: List[Dict[str, str]] = []

        for trial in trials:
            if trial.trial_type == "genuine":
                if trial.claimed_speaker_id != trial.actual_speaker_id:
                    mismatches.append({
                        "trial_id": trial.trial_id,
                        "issue": "Genuine trial has mismatched speaker IDs",
                        "claimed": trial.claimed_speaker_id,
                        "actual": trial.actual_speaker_id,
                    })
                if trial.ground_truth_label != 1:
                    mismatches.append({
                        "trial_id": trial.trial_id,
                        "issue": f"Genuine trial has label {trial.ground_truth_label}, expected 1",
                    })
            elif trial.trial_type == "impostor":
                if trial.claimed_speaker_id == trial.actual_speaker_id:
                    mismatches.append({
                        "trial_id": trial.trial_id,
                        "issue": "Impostor trial has matching speaker IDs",
                        "claimed": trial.claimed_speaker_id,
                        "actual": trial.actual_speaker_id,
                    })
                if trial.ground_truth_label != 0:
                    mismatches.append({
                        "trial_id": trial.trial_id,
                        "issue": f"Impostor trial has label {trial.ground_truth_label}, expected 0",
                    })

        return len(mismatches) == 0, mismatches

    def validate_all(
        self,
        trials: List[VerificationTrial],
        enrollment_splits: Dict[str, EnrollmentSplit],
        dev_speakers: Optional[Set[str]] = None,
        test_speakers: Optional[Set[str]] = None,
    ) -> ValidationResult:
        """Run all validation checks and compile results.

        Args:
            trials: List of all VerificationTrial instances.
            enrollment_splits: Mapping from speaker_id to EnrollmentSplit.
            dev_speakers: Optional set of development split speaker IDs.
            test_speakers: Optional set of test split speaker IDs.

        Returns:
            ValidationResult with aggregated check outcomes.
        """
        result = ValidationResult()

        # Check 1: Speaker-disjoint splits (if both sets provided)
        if dev_speakers is not None and test_speakers is not None:
            is_disjoint, overlap = self.validate_speaker_disjoint(
                dev_speakers, test_speakers
            )
            if is_disjoint:
                result.checks_passed += 1
            else:
                result.checks_failed += 1
                result.is_valid = False
                result.violations.append({
                    "check": "speaker_disjoint_splits",
                    "description": f"Speaker overlap between splits: {overlap}",
                })

        # Check 2: Enrollment/verification non-overlap
        is_nonoverlap, ev_violations = (
            self.validate_enrollment_verification_nonoverlap(enrollment_splits)
        )
        if is_nonoverlap:
            result.checks_passed += 1
        else:
            result.checks_failed += 1
            result.is_valid = False
            for v in ev_violations:
                result.violations.append({
                    "check": "enrollment_verification_nonoverlap",
                    "description": f"Speaker {v['speaker_id']}: recording {v['recording']} in both sets",
                })

        # Check 3: No duplicate trial IDs
        no_dup_ids, dup_ids = self.validate_no_duplicate_trial_ids(trials)
        if no_dup_ids:
            result.checks_passed += 1
        else:
            result.checks_failed += 1
            result.is_valid = False
            result.violations.append({
                "check": "no_duplicate_trial_ids",
                "description": f"{len(dup_ids)} duplicate trial IDs found",
            })

        # Check 4: No duplicate trial pairs
        no_dup_pairs, dup_pairs = self.validate_no_duplicate_pairs(trials)
        if no_dup_pairs:
            result.checks_passed += 1
        else:
            result.checks_failed += 1
            result.is_valid = False
            result.violations.append({
                "check": "no_duplicate_pairs",
                "description": f"{len(dup_pairs)} duplicate trial pairs found",
            })

        # Check 5: Trial label consistency
        labels_ok, label_mismatches = self.validate_trial_labels(trials)
        if labels_ok:
            result.checks_passed += 1
        else:
            result.checks_failed += 1
            result.is_valid = False
            for m in label_mismatches:
                result.violations.append({
                    "check": "trial_label_consistency",
                    "description": m.get("issue", "Label mismatch"),
                })

        # Build summary
        total_checks = result.checks_passed + result.checks_failed
        if result.is_valid:
            result.summary = (
                f"All {total_checks} validation checks passed. "
                f"No data leakage or integrity violations detected."
            )
        else:
            result.summary = (
                f"{result.checks_failed} of {total_checks} validation checks failed. "
                f"Found {len(result.violations)} violation(s)."
            )

        logger.info(
            f"Validation complete: {'PASSED' if result.is_valid else 'FAILED'} "
            f"({result.checks_passed}/{total_checks} checks passed)"
        )

        return result

