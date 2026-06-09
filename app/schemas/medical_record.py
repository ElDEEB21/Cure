from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import PaginationResponse


class MedicalRecordCreate(BaseModel):
    patient_id: str
    diagnosis: str
    medications: list[str] = []
    allergies: list[str] = []
    blood_type: str = ""
    notes: str = ""


class MedicalRecordUpdate(BaseModel):
    diagnosis: Optional[str] = None
    medications: Optional[list[str]] = None
    allergies: Optional[list[str]] = None
    blood_type: Optional[str] = None
    notes: Optional[str] = None


class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    diagnosis: str
    medications: list[str]
    allergies: list[str]
    blood_type: str
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class MedicalRecordFilter(BaseModel):
    patient_id: Optional[str] = None
    diagnosis: Optional[str] = None


class MedicalRecordListResponse(PaginationResponse[MedicalRecordResponse]):
    pass
