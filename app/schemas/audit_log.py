from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import PaginationResponse


class AuditLogCreate(BaseModel):
    actor_id: uuid.UUID
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogUpdate(BaseModel):
    pass


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    actor_id: Optional[uuid.UUID] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class AuditLogListResponse(PaginationResponse[AuditLogResponse]):
    pass
