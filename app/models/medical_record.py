import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MedicalRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    patient_id: str
    diagnosis: str
    medications: list[str] = []
    allergies: list[str] = []
    blood_type: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
