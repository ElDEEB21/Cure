from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import PaginationResponse


class PatientCreate(BaseModel):
    user_id: uuid.UUID
    date_of_birth: date
    gender: str
    phone: str
    address: str
    emergency_contact: str


class PatientUpdate(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None


class PatientResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date_of_birth: date
    gender: str
    phone: str
    address: str
    emergency_contact: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientFilter(BaseModel):
    search: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth_from: Optional[date] = None
    date_of_birth_to: Optional[date] = None


class PatientListResponse(PaginationResponse[PatientResponse]):
    pass
