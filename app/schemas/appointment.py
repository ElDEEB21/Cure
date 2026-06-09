from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import PaginationResponse


class AppointmentStatusEnum(str, Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    nurse_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=480)
    service_type: str
    notes: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

    @field_validator("scheduled_at")
    @classmethod
    def validate_future(cls, v: datetime) -> datetime:
        from datetime import datetime as dt_mod, timezone as tz_mod
        if v.tzinfo is not None and v < dt_mod.now(tz_mod.utc):
            raise ValueError("scheduled_at must be in the future")
        return v


class AppointmentUpdate(BaseModel):
    patient_id: Optional[uuid.UUID] = None
    nurse_id: Optional[uuid.UUID] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=480)
    service_type: Optional[str] = None
    notes: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    cancellation_reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    nurse_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    status: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    service_type: str
    notes: str
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppointmentFilter(BaseModel):
    patient_id: Optional[uuid.UUID] = None
    nurse_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatusEnum
    cancellation_reason: Optional[str] = None


class AppointmentListResponse(PaginationResponse[AppointmentResponse]):
    pass


class AvailabilityRequest(BaseModel):
    nurse_id: uuid.UUID
    date: date
    service_type: Optional[str] = None


class AvailabilityResponse(BaseModel):
    available_slots: list[datetime]
