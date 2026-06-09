import uuid
from typing import Any, Optional

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository
from app.schemas.audit_log import AuditLogCreate, AuditLogFilter, AuditLogUpdate


class AuditLogRepository(BaseRepository[AuditLog, AuditLogCreate, AuditLogUpdate]):
    async def search(
        self, filter: Optional[AuditLogFilter] = None, skip: int = 0, limit: int = 20
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        count_stmt = select(func.count()).select_from(AuditLog)

        conditions = []
        if filter:
            if filter.actor_id:
                conditions.append(AuditLog.actor_id == filter.actor_id)
            if filter.action:
                conditions.append(AuditLog.action == filter.action)
            if filter.resource_type:
                conditions.append(AuditLog.resource_type == filter.resource_type)
            if filter.date_from:
                conditions.append(AuditLog.created_at >= filter.date_from)
            if filter.date_to:
                conditions.append(AuditLog.created_at <= filter.date_to)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def update(self, db_obj: AuditLog, obj_in: AuditLogUpdate | dict[str, Any]) -> AuditLog:
        raise NotImplementedError("Audit logs are immutable and cannot be updated")

    async def delete(self, id: uuid.UUID) -> None:
        raise NotImplementedError("Audit logs are immutable and cannot be deleted")
