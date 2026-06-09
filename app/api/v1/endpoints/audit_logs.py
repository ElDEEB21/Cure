import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import pagination_dependency, require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogFilter, AuditLogListResponse, AuditLogResponse
from app.schemas.base import PaginationParams
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    pagination: Annotated[PaginationParams, Depends(pagination_dependency)],
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> AuditLogListResponse:
    service = AuditService(db)
    audit_filter = AuditLogFilter(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    )
    skip = (pagination.page - 1) * pagination.page_size
    logs, total = await service.repo.search(
        audit_filter, skip=skip, limit=pagination.page_size
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=max(1, -(-total // pagination.page_size)),
    )


@router.get("/{log_id}")
async def get_audit_log(
    log_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogResponse:
    service = AuditService(db)
    log = await service.repo.get(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    return AuditLogResponse.model_validate(log)
