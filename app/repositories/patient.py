import uuid
from typing import Optional

from sqlalchemy import func, or_, select

from app.models.patient import Patient
from app.repositories.base import BaseRepository
from app.schemas.patient import PatientCreate, PatientFilter, PatientUpdate


class PatientRepository(BaseRepository[Patient, PatientCreate, PatientUpdate]):
    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Patient]:
        stmt = select(Patient).where(Patient.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self, filter: PatientFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[Patient], int]:
        stmt = select(Patient)
        count_stmt = select(func.count()).select_from(Patient)

        conditions = []
        if filter.search:
            search_term = f"%{filter.search}%"
            conditions.append(
                or_(
                    Patient.phone.ilike(search_term),
                    Patient.address.ilike(search_term),
                    Patient.emergency_contact.ilike(search_term),
                )
            )
        if filter.gender:
            conditions.append(Patient.gender == filter.gender)
        if filter.date_of_birth_from:
            conditions.append(Patient.date_of_birth >= filter.date_of_birth_from)
        if filter.date_of_birth_to:
            conditions.append(Patient.date_of_birth <= filter.date_of_birth_to)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        patients = result.scalars().all()

        return list(patients), total
