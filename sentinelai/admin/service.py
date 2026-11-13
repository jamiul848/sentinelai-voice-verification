"""Sentinel Voice - Administrator Operations Service Layer.

Orchestrates cross-entity aggregation, biometric lifecycle administration,
threshold governance, and audit logging.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinelai.admin.schemas import (
    AdminAnalyticsResponse,
    AdminAuditLogItem,
    AdminAuditLogListResponse,
    AdminOverviewResponse,
    AdminProfileListItem,
    AdminProfileListResponse,
    AdminSecurityEventsResponse,
    AdminTimelineItem,
    AuditEventBrief,
    ProfileOverviewStats,
    SystemHealthSummary,
    ThresholdConfigRequest,
    ThresholdConfigResponse,
    UserOverviewStats,
    VerificationOverviewStats,
)
from sentinelai.auth.exceptions import UserNotFoundError
from sentinelai.biometrics.storage import BiometricStorageManager
from sentinelai.config import Settings, get_settings
from sentinelai.database.base import utc_now
from sentinelai.database.models.audit_log import AuditLog
from sentinelai.database.models.threshold_configuration import ThresholdConfiguration
from sentinelai.database.models.user import User
from sentinelai.database.models.verification_event import VerificationEvent
from sentinelai.database.models.voice_profile import VoiceProfile
from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.threshold_repository import ThresholdRepository
from sentinelai.monitoring.health import HealthChecker


class AdminService:
    """Consolidated business logic for platform administration."""

    def __init__(self, session: AsyncSession, settings: Optional[Settings] = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.audit_repo = AuditRepository(session)
        self.threshold_repo = ThresholdRepository(session)
        self.health_checker = HealthChecker(self.settings)
        self.storage_manager = BiometricStorageManager(
            storage_root=self.settings.biometric_store_path,
            master_key=self.settings.biometric_encryption_key,
        )

    # --------------------------------------------------------------------------
    # 1. Platform Overview
    # --------------------------------------------------------------------------
    async def get_overview(self) -> AdminOverviewResponse:
        """Aggregate platform-wide telemetry, user states, biometric counts, and health."""
        # User counts
        user_total_stmt = select(func.count(User.id))
        user_active_stmt = select(func.count(User.id)).where(User.is_active.is_(True))
        user_total = (await self.session.execute(user_total_stmt)).scalar() or 0
        user_active = (await self.session.execute(user_active_stmt)).scalar() or 0
        user_inactive = user_total - user_active

        # Profile counts
        prof_total_stmt = select(func.count(VoiceProfile.id))
        prof_active_stmt = select(func.count(VoiceProfile.id)).where(VoiceProfile.status == "ACTIVE")
        prof_revoked_stmt = select(func.count(VoiceProfile.id)).where(VoiceProfile.status == "REVOKED")
        prof_total = (await self.session.execute(prof_total_stmt)).scalar() or 0
        prof_active = (await self.session.execute(prof_active_stmt)).scalar() or 0
        prof_revoked = (await self.session.execute(prof_revoked_stmt)).scalar() or 0

        # Verification event counts
        verif_total_stmt = select(func.count(VerificationEvent.id))
        verif_match_stmt = select(func.count(VerificationEvent.id)).where(VerificationEvent.decision == "MATCH")
        verif_nomatch_stmt = select(func.count(VerificationEvent.id)).where(VerificationEvent.decision == "NO_MATCH")
        verif_avg_lat_stmt = select(func.avg(VerificationEvent.processing_time_ms))

        verif_total = (await self.session.execute(verif_total_stmt)).scalar() or 0
        verif_match = (await self.session.execute(verif_match_stmt)).scalar() or 0
        verif_nomatch = (await self.session.execute(verif_nomatch_stmt)).scalar() or 0
        verif_avg_lat = float((await self.session.execute(verif_avg_lat_stmt)).scalar() or 0.0)

        match_rate = round((verif_match / verif_total * 100.0), 2) if verif_total > 0 else 0.0

        # System health probe
        is_ready, health_data = await self.health_checker.get_readiness(self.session)
        from sentinelai.monitoring.health import PROCESS_START_TIME
        import time

        uptime = round(time.time() - PROCESS_START_TIME, 1)

        from sentinelai.speaker.model import get_model_loader
        loader = get_model_loader()

        components = health_data.get("components", {})
        db_comp = components.get("database", {})
        redis_comp = components.get("redis", {})

        health_summary = SystemHealthSummary(
            status=health_data.get("status", "ready"),
            uptime_seconds=uptime,
            database_status=db_comp.get("status", "unknown"),
            redis_status=redis_comp.get("status", "unknown"),
            model_loaded=bool(loader.is_loaded),
            encryption_configured=bool(self.settings.biometric_encryption_key.strip()),
        )

        # Recent audit events (last 5)
        audit_stmt = (
            select(AuditLog)
            .order_by(desc(AuditLog.created_at))
            .limit(5)
        )
        recent_audit_rows = (await self.session.execute(audit_stmt)).scalars().all()
        recent_events = [
            AuditEventBrief(
                id=a.id,
                action=a.action,
                resource_type=a.resource_type,
                resource_id=a.resource_id,
                actor_user_id=a.actor_user_id,
                created_at=a.created_at,
            )
            for a in recent_audit_rows
        ]

        return AdminOverviewResponse(
            users=UserOverviewStats(total=user_total, active=user_active, inactive=user_inactive),
            voice_profiles=ProfileOverviewStats(total=prof_total, active=prof_active, revoked=prof_revoked),
            verifications=VerificationOverviewStats(
                total=verif_total,
                matches=verif_match,
                no_matches=verif_nomatch,
                match_rate=match_rate,
                avg_latency_ms=round(verif_avg_lat, 1),
            ),
            system_health=health_summary,
            recent_audit_events=recent_events,
        )

    # --------------------------------------------------------------------------
    # 2. Voice Profile Administration
    # --------------------------------------------------------------------------
    async def list_voice_profiles(
        self,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> AdminProfileListResponse:
        """List biometric profiles with associated user credentials (metadata only)."""
        count_stmt = select(func.count(VoiceProfile.id))
        stmt = (
            select(VoiceProfile)
            .options(selectinload(VoiceProfile.user))
            .order_by(desc(VoiceProfile.created_at))
        )

        if status_filter:
            count_stmt = count_stmt.where(VoiceProfile.status == status_filter.upper())
            stmt = stmt.where(VoiceProfile.status == status_filter.upper())
        if user_id:
            count_stmt = count_stmt.where(VoiceProfile.user_id == user_id)
            stmt = stmt.where(VoiceProfile.user_id == user_id)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        profiles = (await self.session.execute(stmt.offset(skip).limit(limit))).scalars().all()

        items = []
        for p in profiles:
            items.append(
                AdminProfileListItem(
                    id=p.id,
                    user_id=p.user_id,
                    user_email=p.user.email if p.user else None,
                    user_full_name=p.user.full_name if p.user else None,
                    status=p.status,
                    sample_count=p.sample_count,
                    mean_pairwise_similarity=float(p.mean_pairwise_similarity),
                    model_identifier=p.model_identifier,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    revoked_at=p.revoked_at,
                )
            )

        return AdminProfileListResponse(total=total, items=items)

    async def revoke_voice_profile(
        self,
        profile_id: uuid.UUID,
        admin_user: User,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Admin-authorized revocation with NIST SP 800-88 cryptographic shredding."""
        stmt = select(VoiceProfile).where(VoiceProfile.id == profile_id)
        profile = (await self.session.execute(stmt)).scalars().first()
        if not profile:
            raise UserNotFoundError(f"Voice profile {profile_id} not found.")

        # Cryptographically shred vector on disk if still present
        if profile.embedding_storage_path:
            try:
                self.storage_manager.shred_vector_file(profile.embedding_storage_path)
            except Exception:
                pass

        profile.status = "REVOKED"
        profile.revoked_at = utc_now()
        profile.updated_at = utc_now()

        # Append audit log
        await self.audit_repo.create_audit_event(
            action="PROFILE_REVOKED_BY_ADMIN",
            resource_type="voice_profile",
            resource_id=str(profile.id),
            actor_user_id=admin_user.id,
            changes={"prior_status": "ACTIVE", "new_status": "REVOKED", "admin_email": admin_user.email},
        )
        await self.session.commit()

        return {
            "profile_id": str(profile.id),
            "status": "REVOKED",
            "message": "Voice profile successfully revoked and shredded by administrator.",
        }

    # --------------------------------------------------------------------------
    # 3. Verification Analytics
    # --------------------------------------------------------------------------
    async def get_analytics(self, days: int = 7) -> AdminAnalyticsResponse:
        """Calculate historical verification decision volume, match rates, and latencies."""
        cutoff = utc_now() - timedelta(days=days)

        # Aggregate total, match, no_match
        total_stmt = select(func.count(VerificationEvent.id)).where(VerificationEvent.created_at >= cutoff)
        match_stmt = select(func.count(VerificationEvent.id)).where(
            VerificationEvent.created_at >= cutoff, VerificationEvent.decision == "MATCH"
        )
        nomatch_stmt = select(func.count(VerificationEvent.id)).where(
            VerificationEvent.created_at >= cutoff, VerificationEvent.decision == "NO_MATCH"
        )
        avg_lat_stmt = select(func.avg(VerificationEvent.processing_time_ms)).where(
            VerificationEvent.created_at >= cutoff
        )

        total = (await self.session.execute(total_stmt)).scalar() or 0
        matches = (await self.session.execute(match_stmt)).scalar() or 0
        no_matches = (await self.session.execute(nomatch_stmt)).scalar() or 0
        avg_lat = float((await self.session.execute(avg_lat_stmt)).scalar() or 0.0)

        match_rate = round((matches / total * 100.0), 2) if total > 0 else 0.0
        no_match_rate = round((no_matches / total * 100.0), 2) if total > 0 else 0.0

        # Query events for timeline construction
        events_stmt = (
            select(VerificationEvent)
            .where(VerificationEvent.created_at >= cutoff)
            .order_by(VerificationEvent.created_at)
        )
        events = (await self.session.execute(events_stmt)).scalars().all()

        timeline_map: Dict[str, Dict[str, Any]] = {}
        for ev in events:
            date_str = ev.created_at.strftime("%Y-%m-%d")
            if date_str not in timeline_map:
                timeline_map[date_str] = {"matches": 0, "no_matches": 0, "latencies": []}
            if ev.decision == "MATCH":
                timeline_map[date_str]["matches"] += 1
            else:
                timeline_map[date_str]["no_matches"] += 1
            timeline_map[date_str]["latencies"].append(float(ev.processing_time_ms))

        timeline = []
        for d, vals in sorted(timeline_map.items()):
            tot = vals["matches"] + vals["no_matches"]
            avg_l = sum(vals["latencies"]) / len(vals["latencies"]) if vals["latencies"] else 0.0
            timeline.append(
                AdminTimelineItem(
                    date=d,
                    matches=vals["matches"],
                    no_matches=vals["no_matches"],
                    total=tot,
                    avg_latency_ms=round(avg_l, 1),
                )
            )

        # Active threshold info
        active_thresh = await self.threshold_repo.get_active_threshold()
        thresh_info = None
        if active_thresh:
            thresh_info = {
                "version_tag": active_thresh.version_tag,
                "model_identifier": active_thresh.model_identifier,
                "threshold_value": float(active_thresh.threshold_value),
                "calibration_dataset": active_thresh.calibration_dataset,
                "calibration_criterion": active_thresh.calibration_criterion,
            }

        return AdminAnalyticsResponse(
            total_verifications=total,
            matches=matches,
            no_matches=no_matches,
            match_rate=match_rate,
            no_match_rate=no_match_rate,
            average_latency_ms=round(avg_lat, 1),
            timeline=timeline,
            active_threshold=thresh_info,
        )

    # --------------------------------------------------------------------------
    # 4. Threshold Governance
    # --------------------------------------------------------------------------
    async def list_thresholds(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ThresholdConfigResponse]:
        """Fetch all registered calibrated decision boundaries."""
        records = await self.threshold_repo.list_configurations(skip=skip, limit=limit)
        return [
            ThresholdConfigResponse(
                id=r.id,
                version_tag=r.version_tag,
                model_identifier=r.model_identifier,
                threshold_value=float(r.threshold_value),
                calibration_dataset=r.calibration_dataset,
                calibration_criterion=r.calibration_criterion,
                calibration_metadata=r.calibration_metadata or {},
                is_active=bool(r.is_active),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ]

    async def get_active_threshold(
        self,
        model_identifier: str = "speechbrain/spkrec-ecapa-voxceleb",
    ) -> Optional[ThresholdConfigResponse]:
        """Fetch active threshold for the specified neural backbone."""
        record = await self.threshold_repo.get_active_threshold(model_identifier)
        if not record:
            return None
        return ThresholdConfigResponse(
            id=record.id,
            version_tag=record.version_tag,
            model_identifier=record.model_identifier,
            threshold_value=float(record.threshold_value),
            calibration_dataset=record.calibration_dataset,
            calibration_criterion=record.calibration_criterion,
            calibration_metadata=record.calibration_metadata or {},
            is_active=bool(record.is_active),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create_threshold(
        self,
        req: ThresholdConfigRequest,
        admin_user: User,
        ip_address: Optional[str] = None,
    ) -> ThresholdConfigResponse:
        """Create and persist a new threshold configuration."""
        record = await self.threshold_repo.create_threshold(
            version_tag=req.version_tag,
            model_identifier=req.model_identifier,
            threshold_value=req.threshold_value,
            calibration_dataset=req.calibration_dataset,
            calibration_criterion=req.calibration_criterion,
            calibration_metadata=req.calibration_metadata,
            is_active=req.is_active,
        )

        await self.audit_repo.create_audit_event(
            action="THRESHOLD_CREATED",
            resource_type="threshold_configuration",
            resource_id=str(record.id),
            actor_user_id=admin_user.id,
            changes={"version_tag": req.version_tag, "threshold_value": req.threshold_value, "is_active": req.is_active},
        )
        await self.session.commit()

        return ThresholdConfigResponse(
            id=record.id,
            version_tag=record.version_tag,
            model_identifier=record.model_identifier,
            threshold_value=float(record.threshold_value),
            calibration_dataset=record.calibration_dataset,
            calibration_criterion=record.calibration_criterion,
            calibration_metadata=record.calibration_metadata or {},
            is_active=bool(record.is_active),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def activate_threshold(
        self,
        threshold_id: uuid.UUID,
        admin_user: User,
        ip_address: Optional[str] = None,
    ) -> ThresholdConfigResponse:
        """Activate a threshold configuration, deactivating prior configurations for that model."""
        target = await self.threshold_repo.activate_threshold(threshold_id)
        if not target:
            raise UserNotFoundError(f"Threshold configuration {threshold_id} not found.")

        await self.audit_repo.create_audit_event(
            action="THRESHOLD_ACTIVATED",
            resource_type="threshold_configuration",
            resource_id=str(target.id),
            actor_user_id=admin_user.id,
            changes={"version_tag": target.version_tag, "threshold_value": float(target.threshold_value)},
        )
        await self.session.commit()

        return ThresholdConfigResponse(
            id=target.id,
            version_tag=target.version_tag,
            model_identifier=target.model_identifier,
            threshold_value=float(target.threshold_value),
            calibration_dataset=target.calibration_dataset,
            calibration_criterion=target.calibration_criterion,
            calibration_metadata=target.calibration_metadata or {},
            is_active=bool(target.is_active),
            created_at=target.created_at,
            updated_at=target.updated_at,
        )

    # --------------------------------------------------------------------------
    # 5. Global Audit Logs
    # --------------------------------------------------------------------------
    async def list_audit_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> AdminAuditLogListResponse:
        """Query append-only audit trail with filtering and sanitized metadata."""
        count_stmt = select(func.count(AuditLog.id))
        stmt = (
            select(AuditLog)
            .options(selectinload(AuditLog.actor_user))
            .order_by(desc(AuditLog.created_at))
        )

        if action:
            count_stmt = count_stmt.where(AuditLog.action == action.upper())
            stmt = stmt.where(AuditLog.action == action.upper())
        if resource_type:
            count_stmt = count_stmt.where(AuditLog.resource_type == resource_type.lower())
            stmt = stmt.where(AuditLog.resource_type == resource_type.lower())
        if actor_user_id:
            count_stmt = count_stmt.where(AuditLog.actor_user_id == actor_user_id)
            stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        logs = (await self.session.execute(stmt.offset(skip).limit(limit))).scalars().all()

        items = [
            AdminAuditLogItem(
                id=l.id,
                actor_user_id=l.actor_user_id,
                actor_email=l.actor_user.email if l.actor_user else None,
                action=l.action,
                resource_type=l.resource_type,
                resource_id=l.resource_id,
                changes=l.changes,
                created_at=l.created_at,
            )
            for l in logs
        ]

        return AdminAuditLogListResponse(total=total, skip=skip, limit=limit, items=items)

    # --------------------------------------------------------------------------
    # 6. Security Events & Rate Limiter Telemetry
    # --------------------------------------------------------------------------
    async def get_security_events(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> AdminSecurityEventsResponse:
        """Fetch audit log items concerning security-sensitive actions and rate limiter status."""
        security_actions = [
            "USER_DEACTIVATED",
            "USER_ACTIVATED",
            "USER_ROLES_MODIFIED",
            "USER_DELETED",
            "PASSWORD_CHANGED",
            "CONSENT_REVOKED",
            "PROFILE_REVOKED",
            "PROFILE_REVOKED_BY_ADMIN",
            "THRESHOLD_ACTIVATED",
            "RATE_LIMIT_EXCEEDED",
            "ACCOUNT_THROTTLED",
            "IP_THROTTLED",
            "TOKEN_REUSE_DETECTED",
        ]

        count_stmt = select(func.count(AuditLog.id)).where(AuditLog.action.in_(security_actions))
        stmt = (
            select(AuditLog)
            .options(selectinload(AuditLog.actor_user))
            .where(AuditLog.action.in_(security_actions))
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )

        total = (await self.session.execute(count_stmt)).scalar() or 0
        logs = (await self.session.execute(stmt)).scalars().all()

        events = [
            AdminAuditLogItem(
                id=l.id,
                actor_user_id=l.actor_user_id,
                actor_email=l.actor_user.email if l.actor_user else None,
                action=l.action,
                resource_type=l.resource_type,
                resource_id=l.resource_id,
                changes=l.changes,
                created_at=l.created_at,
            )
            for l in logs
        ]

        rate_limiter_info = {
            "backend": self.settings.rate_limit_storage,
            "rules": {
                "auth_login": self.settings.rate_limit_login,
                "auth_register": self.settings.rate_limit_register,
                "biometrics_verify": self.settings.rate_limit_verification,
                "biometrics_enroll": self.settings.rate_limit_enrollment,
            },
            "redis_configured": bool(self.settings.redis_url),
        }

        return AdminSecurityEventsResponse(total=total, events=events, rate_limiter=rate_limiter_info)
