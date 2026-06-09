import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.repositories.appointment import AppointmentRepository
from app.schemas.appointment import AppointmentCreate, AppointmentFilter, AppointmentUpdate
from app.services.audit_service import AuditService

VALID_TRANSITIONS: dict[str, set[str]] = {
    "scheduled": {"confirmed", "cancelled"},
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

SAUDI_BBOX = {"lat_min": 24.0, "lat_max": 27.0, "lng_min": 46.0, "lng_max": 56.0}

WORK_START_HOUR = 8
WORK_END_HOUR = 18
SLOT_INTERVAL_MINUTES = 30


class AppointmentService:
    def __init__(self, db: AsyncSession):
        self.repo = AppointmentRepository(Appointment, db)
        self.audit = AuditService(db)

    def _validate_location(self, lat: float | None, lng: float | None) -> None:
        if lat is None and lng is None:
            return
        if lat is None or lng is None:
            raise ValueError("Both location_lat and location_lng must be provided together")
        if not (SAUDI_BBOX["lat_min"] <= lat <= SAUDI_BBOX["lat_max"]):
            raise ValueError(
                f"Location latitude must be between {SAUDI_BBOX['lat_min']} and {SAUDI_BBOX['lat_max']}"
            )
        if not (SAUDI_BBOX["lng_min"] <= lng <= SAUDI_BBOX["lng_max"]):
            raise ValueError(
                f"Location longitude must be between {SAUDI_BBOX['lng_min']} and {SAUDI_BBOX['lng_max']}"
            )

    def _validate_transition(self, current_status: str, new_status: str) -> None:
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{current_status}' to '{new_status}'. "
                f"Allowed transitions: {allowed}"
            )

    async def schedule_appointment(self, appointment_in: AppointmentCreate, actor_id: Optional[uuid.UUID] = None) -> Appointment:
        self._validate_location(appointment_in.location_lat, appointment_in.location_lng)

        if appointment_in.scheduled_at.tzinfo is None:
            scheduled_at = appointment_in.scheduled_at.replace(tzinfo=timezone.utc)
        else:
            scheduled_at = appointment_in.scheduled_at

        conflicts = await self.repo.get_conflicting(
            appointment_in.nurse_id, scheduled_at, appointment_in.duration_minutes
        )
        if conflicts:
            raise ValueError(
                f"Nurse {appointment_in.nurse_id} has a conflicting appointment "
                f"at the requested time"
            )

        create_data = appointment_in.model_copy(
            update={"scheduled_at": scheduled_at, "notes": appointment_in.notes or ""}
        )
        appointment = await self.repo.create(create_data)
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="appointment.schedule",
                    resource_type="appointment",
                    resource_id=str(appointment.id),
                )
            except Exception:
                pass
        return appointment

    async def confirm_appointment(self, appointment_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None) -> Appointment:
        appointment = await self.repo.get(appointment_id)
        if not appointment:
            raise ValueError("Appointment not found")
        self._validate_transition(appointment.status, "confirmed")
        updated = await self.repo.update(appointment, {"status": "confirmed"})
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="appointment.confirm",
                    resource_type="appointment",
                    resource_id=str(appointment_id),
                )
            except Exception:
                pass
        return updated

    async def start_appointment(self, appointment_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None) -> Appointment:
        appointment = await self.repo.get(appointment_id)
        if not appointment:
            raise ValueError("Appointment not found")
        self._validate_transition(appointment.status, "in_progress")
        updated = await self.repo.update(appointment, {"status": "in_progress"})
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="appointment.start",
                    resource_type="appointment",
                    resource_id=str(appointment_id),
                )
            except Exception:
                pass
        return updated

    async def complete_appointment(self, appointment_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None) -> Appointment:
        appointment = await self.repo.get(appointment_id)
        if not appointment:
            raise ValueError("Appointment not found")
        self._validate_transition(appointment.status, "completed")
        updated = await self.repo.update(appointment, {"status": "completed"})
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="appointment.complete",
                    resource_type="appointment",
                    resource_id=str(appointment_id),
                )
            except Exception:
                pass
        return updated

    async def cancel_appointment(
        self, appointment_id: uuid.UUID, reason: str | None = None, actor_id: Optional[uuid.UUID] = None
    ) -> Appointment:
        appointment = await self.repo.get(appointment_id)
        if not appointment:
            raise ValueError("Appointment not found")
        self._validate_transition(appointment.status, "cancelled")
        updated = await self.repo.update(
            appointment, {"status": "cancelled", "cancellation_reason": reason}
        )
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="appointment.cancel",
                    resource_type="appointment",
                    resource_id=str(appointment_id),
                )
            except Exception:
                pass
        return updated

    async def update_appointment(
        self, appointment_id: uuid.UUID, appointment_in: AppointmentUpdate
    ) -> Appointment:
        appointment = await self.repo.get(appointment_id)
        if not appointment:
            raise ValueError("Appointment not found")
        return await self.repo.update(appointment, appointment_in)

    async def delete_appointment(self, appointment_id: uuid.UUID) -> None:
        appointment = await self.repo.get(appointment_id)
        if not appointment:
            raise ValueError("Appointment not found")
        await self.repo.delete(appointment_id)

    async def get_appointment(self, appointment_id: uuid.UUID) -> Optional[Appointment]:
        return await self.repo.get(appointment_id)

    async def list_appointments(
        self, appt_filter: AppointmentFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[Appointment], int]:
        return await self.repo.search(appt_filter, skip=skip, limit=limit)

    async def check_availability(
        self,
        nurse_id: uuid.UUID,
        date: date,
        service_type: str | None = None,
    ) -> list[datetime]:
        day_start = datetime.combine(date, datetime.min.time().replace(hour=WORK_START_HOUR), tzinfo=timezone.utc)
        day_end = datetime.combine(date, datetime.min.time().replace(hour=WORK_END_HOUR), tzinfo=timezone.utc)
        all_slots: list[datetime] = []
        current = day_start
        while current < day_end:
            all_slots.append(current)
            current += timedelta(minutes=SLOT_INTERVAL_MINUTES)

        available: list[datetime] = []
        for slot in all_slots:
            conflicts = await self.repo.get_conflicting(nurse_id, slot, SLOT_INTERVAL_MINUTES)
            if not conflicts:
                available.append(slot)

        return available
