import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select

from app.models.appointment import Appointment
from app.repositories.base import BaseRepository
from app.schemas.appointment import AppointmentCreate, AppointmentFilter, AppointmentUpdate


class AppointmentRepository(
    BaseRepository[Appointment, AppointmentCreate, AppointmentUpdate]
):
    async def get_by_patient(
        self, patient_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment).where(Appointment.patient_id == patient_id)
        count_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.patient_id == patient_id)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(Appointment.scheduled_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_nurse(
        self, nurse_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment).where(Appointment.nurse_id == nurse_id)
        count_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.nurse_id == nurse_id)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(Appointment.scheduled_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 20
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment).where(Appointment.status == status)
        count_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.status == status)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(Appointment.scheduled_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_date_range(
        self,
        date_from: datetime,
        date_to: datetime,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment).where(
            and_(Appointment.scheduled_at >= date_from, Appointment.scheduled_at <= date_to)
        )
        count_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(
                and_(
                    Appointment.scheduled_at >= date_from,
                    Appointment.scheduled_at <= date_to,
                )
            )
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(Appointment.scheduled_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_conflicting(
        self, nurse_id: uuid.UUID, scheduled_at: datetime, duration_minutes: int
    ) -> list[Appointment]:
        slot_start_utc = scheduled_at.replace(tzinfo=None)
        slot_end_utc = scheduled_at.replace(tzinfo=None) + timedelta(minutes=duration_minutes)
        stmt = select(Appointment).where(
            and_(
                Appointment.nurse_id == nurse_id,
                Appointment.status.in_(["scheduled", "confirmed", "in_progress"]),
                Appointment.scheduled_at < slot_end_utc,
            )
        )
        result = await self.session.execute(stmt)
        appointments = result.scalars().all()
        return [
            a
            for a in appointments
            if (a.scheduled_at.replace(tzinfo=None) + timedelta(minutes=a.duration_minutes)) > slot_start_utc
        ]

    async def search(
        self, filter: AppointmentFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment)
        count_stmt = select(func.count()).select_from(Appointment)

        conditions = []
        if filter.patient_id:
            conditions.append(Appointment.patient_id == filter.patient_id)
        if filter.nurse_id:
            conditions.append(Appointment.nurse_id == filter.nurse_id)
        if filter.status:
            conditions.append(Appointment.status == filter.status)
        if filter.date_from:
            conditions.append(Appointment.scheduled_at >= filter.date_from)
        if filter.date_to:
            conditions.append(Appointment.scheduled_at <= filter.date_to)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit).order_by(Appointment.scheduled_at.desc())
        result = await self.session.execute(stmt)
        appointments = result.scalars().all()

        return list(appointments), total
