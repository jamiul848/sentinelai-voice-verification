"""Initial relational database schema for Sentinel Voice.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-11-13 00:00:00.000000

Establishes the ten core application and security entities:
1. users
2. roles
3. user_roles
4. refresh_tokens
5. api_credentials
6. consent_records
7. voice_profiles
8. enrollment_records
9. verification_events
10. audit_logs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_is_active", "users", ["is_active"])

    # 2. roles
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_roles_name", "roles", ["name"], unique=True)

    # 3. user_roles
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_id_role_id"),
    )
    op.create_index("idx_user_roles_user", "user_roles", ["user_id"])
    op.create_index("idx_user_roles_role", "user_roles", ["role_id"])

    # 4. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_refresh_tokens_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id", "is_revoked"])

    # 5. api_credentials
    op.create_table(
        "api_credentials",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[\"verify\"]'")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_api_credentials_hash", "api_credentials", ["key_hash"], unique=True)
    op.create_index("idx_api_credentials_user", "api_credentials", ["user_id"])

    # 6. consent_records
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.String(50), nullable=False, server_default="VOICE_BIOMETRIC_ENROLLMENT"),
        sa.Column("consent_granted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("consent_version", sa.String(20), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("consent_granted IS TRUE", name="check_consent_granted_true"),
    )
    op.create_index("idx_consent_records_user", "consent_records", ["user_id"])
    op.create_index("idx_consent_records_user_created", "consent_records", ["user_id", "created_at"])

    # 7. voice_profiles
    op.create_table(
        "voice_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("mean_pairwise_similarity", sa.Numeric(6, 4), nullable=False),
        sa.Column("model_identifier", sa.String(100), nullable=False, server_default="speechbrain/spkrec-ecapa-voxceleb"),
        sa.Column("embedding_storage_path", sa.String(512), nullable=False),
        sa.Column("embedding_sha256", sa.String(64), nullable=False),
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
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sample_count >= 3", name="check_min_enrollment_samples"),
    )
    op.create_index("idx_voice_profiles_user_status", "voice_profiles", ["user_id", "status"])
    op.create_index("idx_voice_profiles_status", "voice_profiles", ["status"])

    # 8. enrollment_records
    op.create_table(
        "enrollment_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.Uuid(as_uuid=True), sa.ForeignKey("voice_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("duration_sec", sa.Numeric(6, 3), nullable=False),
        sa.Column("rms_energy", sa.Numeric(8, 6), nullable=False),
        sa.Column("peak_amplitude", sa.Numeric(8, 6), nullable=False),
        sa.Column("snr_db", sa.Numeric(6, 2), nullable=True),
        sa.Column("audio_format", sa.String(10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("duration_sec >= 1.0 AND duration_sec <= 60.0", name="check_enrollment_duration_range"),
    )
    op.create_index("idx_enrollment_records_profile", "enrollment_records", ["profile_id"])
    op.create_index("idx_enrollment_records_profile_created", "enrollment_records", ["profile_id", "created_at"])

    # 9. verification_events
    op.create_table(
        "verification_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", sa.Uuid(as_uuid=True), sa.ForeignKey("voice_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("similarity_score", sa.Numeric(7, 6), nullable=False),
        sa.Column("applied_threshold", sa.Numeric(7, 6), nullable=False),
        sa.Column("is_match", sa.Boolean(), nullable=False),
        sa.Column("processing_time_ms", sa.Numeric(8, 2), nullable=False),
        sa.Column("client_ip", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_verif_events_user_time", "verification_events", ["user_id", "created_at"])
    op.create_index("idx_verif_events_decision_time", "verification_events", ["decision", "created_at"])

    # 10. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_audit_logs_actor_time", "audit_logs", ["actor_user_id", "created_at"])
    op.create_index("idx_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("verification_events")
    op.drop_table("enrollment_records")
    op.drop_table("voice_profiles")
    op.drop_table("consent_records")
    op.drop_table("api_credentials")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
