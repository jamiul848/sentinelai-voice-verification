"""Unit tests for the Verification Threshold Engine."""

import pytest

from sentinelai.verification.exceptions import ThresholdValidationError
from sentinelai.verification.threshold import VerificationThreshold


class TestVerificationThreshold:
    """Tests for threshold configuration, validation, and match logic."""

    def test_default_threshold_configuration(self) -> None:
        """Default threshold should initialize with 0.65 and development version string."""
        thresh = VerificationThreshold()
        assert thresh.threshold_value == 0.65
        assert thresh.version == "dev-uncalibrated-v1.0"
        assert not thresh.to_dict()["is_calibrated"]

    def test_custom_calibrated_threshold(self) -> None:
        """Custom threshold should store provided value, version, and calibrated status."""
        thresh = VerificationThreshold(
            threshold_value=0.72,
            version="eer-calibrated-voxceleb-v2.1",
            description="Empirical EER calibration on development cohort",
        )
        assert thresh.threshold_value == 0.72
        assert thresh.version == "eer-calibrated-voxceleb-v2.1"
        assert thresh.to_dict()["is_calibrated"]

    @pytest.mark.parametrize("valid_val", [-1.0, -0.5, 0.0, 0.5, 0.75, 1.0])
    def test_valid_threshold_values(self, valid_val: float) -> None:
        """Threshold values across [-1.0, 1.0] must be valid."""
        thresh = VerificationThreshold(threshold_value=valid_val)
        assert thresh.threshold_value == valid_val

    @pytest.mark.parametrize("invalid_val", [-1.01, 1.01, -10.0, 50.0])
    def test_out_of_bounds_threshold_raises_error(self, invalid_val: float) -> None:
        """Threshold values outside [-1.0, 1.0] must raise ThresholdValidationError."""
        with pytest.raises(ThresholdValidationError, match="out of valid bounds"):
            VerificationThreshold(threshold_value=invalid_val)

    def test_nan_and_inf_threshold_raises_error(self) -> None:
        """Non-finite threshold values must raise ThresholdValidationError."""
        with pytest.raises(ThresholdValidationError, match="finite numerical number"):
            VerificationThreshold(threshold_value=float("nan"))

        with pytest.raises(ThresholdValidationError, match="finite numerical number"):
            VerificationThreshold(threshold_value=float("inf"))

    def test_non_numeric_threshold_raises_error(self) -> None:
        """Non-numeric threshold values must raise ThresholdValidationError."""
        with pytest.raises(ThresholdValidationError, match="must be a numeric float"):
            VerificationThreshold(threshold_value="0.65")  # type: ignore

    def test_empty_version_raises_error(self) -> None:
        """Empty version strings must raise ThresholdValidationError."""
        with pytest.raises(ThresholdValidationError, match="version identifier cannot be empty"):
            VerificationThreshold(threshold_value=0.6, version="")

    def test_is_match_boundary_and_evaluation(self) -> None:
        """Scores above and on threshold should match; scores below should not."""
        thresh = VerificationThreshold(threshold_value=0.70)

        # Above threshold
        assert thresh.is_match(0.701) is True
        assert thresh.is_match(0.95) is True

        # Exactly on threshold
        assert thresh.is_match(0.700) is True

        # Below threshold
        assert thresh.is_match(0.699) is False
        assert thresh.is_match(0.0) is False
        assert thresh.is_match(-0.5) is False

    def test_threshold_to_dict_and_repr(self) -> None:
        """Threshold summary dict and repr should contain critical attributes."""
        thresh = VerificationThreshold(threshold_value=0.68, version="v1.0")
        info = thresh.to_dict()
        assert info["threshold_value"] == 0.68
        assert info["version"] == "v1.0"
        assert "VerificationThreshold" in repr(thresh)

