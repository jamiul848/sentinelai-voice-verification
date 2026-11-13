"""Allow consent revocation by removing check constraint on consent_granted.

Revision ID: 0002_allow_consent_revocation
Revises: 0001_initial_schema
Create Date: 2026-11-13 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_allow_consent_revocation'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the check constraint requiring consent_granted to be TRUE.
    
    This allows immutable logging of consent revocation records (consent_granted=FALSE),
    preserving the full legal audit trail as mandated by GDPR Article 7(3).
    """
    # PostgreSQL supports drop_constraint on check constraints
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("check_consent_granted_true", "consent_records", type_="check")


def downgrade() -> None:
    """Restore the check constraint requiring consent_granted IS TRUE."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_check_constraint(
            "check_consent_granted_true",
            "consent_records",
            "consent_granted IS TRUE",
        )

