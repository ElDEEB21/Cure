from datetime import datetime, timezone
from typing import Optional

from app.models.medical_record import MedicalRecord
from app.repositories.medical_record import MedicalRecordRepository
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordFilter, MedicalRecordUpdate


class MedicalRecordService:
    def __init__(self):
        self.repo = MedicalRecordRepository()

    async def create_record(self, record_in: MedicalRecordCreate) -> dict:
        record = MedicalRecord(**record_in.model_dump())
        return await self.repo.create(record.model_dump())

    async def get_record(self, record_id: str) -> Optional[dict]:
        return await self.repo.get(record_id)

    async def update_record(
        self, record_id: str, record_in: MedicalRecordUpdate
    ) -> Optional[dict]:
        data = record_in.model_dump(exclude_unset=True)
        if not data:
            return await self.repo.get(record_id)
        return await self.repo.update(record_id, data)

    async def delete_record(self, record_id: str) -> bool:
        return await self.repo.delete(record_id)

    async def list_records(
        self, filter: MedicalRecordFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[dict], int]:
        if filter.patient_id:
            return await self.repo.get_by_patient(filter.patient_id, skip=skip, limit=limit)
        return await self.repo.list_all(skip=skip, limit=limit)
