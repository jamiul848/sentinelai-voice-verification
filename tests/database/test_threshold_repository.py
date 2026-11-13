"""Unit tests for ThresholdRepository."""

import pytest
from sentinelai.database.repositories.threshold_repository import ThresholdRepository


@pytest.mark.asyncio
async def test_threshold_repository_lifecycle(test_session):
    """Verify creating, listing, activating, and retrieving threshold configurations."""
    repo = ThresholdRepository(test_session)

    # 1. Create first threshold (inactive)
    t1 = await repo.create_threshold(
        version_tag="voxceleb-baseline-v1",
        model_identifier="speechbrain/spkrec-ecapa-voxceleb",
        threshold_value=0.3500,
        calibration_dataset="VoxCeleb1-test",
        calibration_criterion="EER",
        is_active=False,
    )
    assert t1.id is not None
    assert t1.is_active is False

    # 2. Create second threshold (active)
    t2 = await repo.create_threshold(
        version_tag="librispeech-calibrated-v1",
        model_identifier="speechbrain/spkrec-ecapa-voxceleb",
        threshold_value=0.405898,
        calibration_dataset="LibriSpeech dev-clean",
        calibration_criterion="EER",
        is_active=True,
    )
    assert t2.is_active is True

    # 3. Get active threshold
    active = await repo.get_active_threshold("speechbrain/spkrec-ecapa-voxceleb")
    assert active is not None
    assert active.id == t2.id
    assert float(active.threshold_value) == pytest.approx(0.405898, rel=1e-5)

    # 4. Get by version
    by_ver = await repo.get_by_version("voxceleb-baseline-v1")
    assert by_ver is not None
    assert by_ver.id == t1.id

    # 5. Switch active threshold
    activated_t1 = await repo.activate_threshold(t1.id)
    assert activated_t1.is_active is True

    active_now = await repo.get_active_threshold("speechbrain/spkrec-ecapa-voxceleb")
    assert active_now.id == t1.id

    # t2 should now be deactivated
    refreshed_t2 = await repo.get_by_id(t2.id)
    assert refreshed_t2.is_active is False

    # 6. List configurations
    configs = await repo.list_configurations("speechbrain/spkrec-ecapa-voxceleb")
    assert len(configs) == 2

