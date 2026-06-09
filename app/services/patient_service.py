import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.repositories.patient import PatientRepository
from app.schemas.patient import PatientCreate, PatientFilter, PatientUpdate
from app.services.audit_service import AuditService


class PatientService:
    def __init__(self, db: AsyncSession):
        self.repo = PatientRepository(Patient, db)
        self.audit = AuditService(db)

    async def create_patient(self, patient_in: PatientCreate, actor_id: Optional[uuid.UUID] = None) -> Patient:
        patient = await self.repo.create(patient_in)
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="patient.create",
                    resource_type="patient",
                    resource_id=str(patient.id),
                )
            except Exception:
                pass
        return patient

    async def get_patient(self, patient_id: uuid.UUID) -> Optional[Patient]:
        return await self.repo.get(patient_id)

    async def get_patient_by_user(self, user_id: uuid.UUID) -> Optional[Patient]:
        return await self.repo.get_by_user_id(user_id)

    async def update_patient(
        self, patient_id: uuid.UUID, patient_in: PatientUpdate, actor_id: Optional[uuid.UUID] = None
    ) -> Optional[Patient]:
        patient = await self.repo.get(patient_id)
        if not patient:
            return None
        updated = await self.repo.update(patient, patient_in)
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="patient.update",
                    resource_type="patient",
                    resource_id=str(patient_id),
                )
            except Exception:
                pass
        return updated

    async def delete_patient(self, patient_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None) -> bool:
        patient = await self.repo.get(patient_id)
        if not patient:
            return False
        await self.repo.delete(patient_id)
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="patient.delete",
                    resource_type="patient",
                    resource_id=str(patient_id),
                )
            except Exception:
                pass
        return True

    async def search_patients(
        self, filter: PatientFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[Patient], int]:
        return await self.repo.search(filter, skip=skip, limit=limit)
