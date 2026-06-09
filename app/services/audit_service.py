import json
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogCreate


class AuditService:
    def __init__(self, db: AsyncSession):
        self.repo = AuditLogRepository(AuditLog, db)

    async def log_action(
        self,
        actor_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        obj_in = AuditLogCreate(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return await self.repo.create(obj_in)
