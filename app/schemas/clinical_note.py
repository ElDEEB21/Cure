from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.base import PaginationResponse


class ClinicalNoteCreate(BaseModel):
    patient_id: str
    author_id: str
    note_type: str
    content: str
    tags: list[str] = []


class ClinicalNoteUpdate(BaseModel):
    note_type: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class ClinicalNoteResponse(BaseModel):
    id: str
    patient_id: str
    author_id: str
    note_type: str
    content: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ClinicalNoteFilter(BaseModel):
    patient_id: Optional[str] = None
    note_type: Optional[str] = None
    tag: Optional[str] = None
    search: Optional[str] = None


class ClinicalNoteListResponse(PaginationResponse[ClinicalNoteResponse]):
    pass
