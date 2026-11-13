"""Add threshold_configurations table and link to verification_events.

Revision ID: 0003_add_threshold_configurations
Revises: 0002_allow_consent_revocation
Create Date: 2026-11-13 12:30:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_threshold_configs'
down_revision: Union[str, None] = '0002_allow_consent_revocation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create threshold_configurations table and add threshold_id to verification_events."""
    # 1. Create threshold_configurations table
    op.create_table(
        "threshold_configurations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version_tag", sa.String(50), nullable=False),
        sa.Column("model_identifier", sa.String(100), nullable=False),
        sa.Column("threshold_value", sa.Numeric(7, 6), nullable=False),
        sa.Column("calibration_dataset", sa.String(100), nullable=False),
        sa.Column(
            "calibration_criterion",
            sa.String(50),
            nullable=False,
            server_default="equal_error_rate_minimization",
        ),
        sa.Column("calibration_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_threshold_config_version",
        "threshold_configurations",
        ["version_tag"],
        unique=True,
    )
    op.create_index(
        "idx_threshold_config_active_model",
        "threshold_configurations",
        ["model_identifier", "is_active"],
    )

    # 2. Add threshold_id column to verification_events
    op.add_column(
        "verification_events",
        sa.Column(
            "threshold_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("threshold_configurations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_verification_events_threshold", "verification_events", ["threshold_id"])

    # 3. Seed the Phase 5E empirically calibrated threshold baseline
    initial_id = uuid.uuid4()
    meta = (
        '{"eer": 0.011227, "eer_percent": 1.1227, "calibration_split": "dev-clean", '
        '"test_split": "test-clean", "test_eer": 0.0056, "test_roc_auc": 0.9996}'
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO threshold_configurations (
                id, version_tag, model_identifier, threshold_value,
                calibration_dataset, calibration_criterion, calibration_metadata, is_active,
                created_at, updated_at
            ) VALUES (
                '{initial_id}',
                'librispeech-dev-clean-eer-v1.0',
                'speechbrain/spkrec-ecapa-voxceleb',
                0.405898,
                'LibriSpeech dev-clean',
                'equal_error_rate_minimization',
                '{meta}',
                TRUE,
                NOW(),
                NOW()
            );
            """
        )
    )


def downgrade() -> None:
    """Drop threshold_configurations and remove threshold_id column."""
    op.drop_index("idx_verification_events_threshold", table_name="verification_events")
    op.drop_column("verification_events", "threshold_id")
    op.drop_index("idx_threshold_config_active_model", table_name="threshold_configurations")
    op.drop_index("idx_threshold_config_version", table_name="threshold_configurations")
    op.drop_table("threshold_configurations")
