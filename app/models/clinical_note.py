import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ClinicalNote(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    patient_id: str
    author_id: str
    note_type: str
    content: str
    tags: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
