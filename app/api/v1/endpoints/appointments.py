import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import pagination_dependency, require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentFilter,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    AvailabilityRequest,
    AvailabilityResponse,
)
from app.schemas.base import PaginationParams
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_in: AppointmentCreate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    service = AppointmentService(db)
    try:
        appointment = await service.schedule_appointment(appointment_in, actor_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AppointmentResponse.model_validate(appointment)


@router.get("")
async def list_appointments(
    current_user: Annotated[User, Depends(require_roles("admin", "nurse", "patient"))],
    pagination: Annotated[PaginationParams, Depends(pagination_dependency)],
    db: Annotated[AsyncSession, Depends(get_db)],
    patient_id: uuid.UUID | None = None,
    nurse_id: uuid.UUID | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> AppointmentListResponse:
    service = AppointmentService(db)
    appt_filter = AppointmentFilter(
        patient_id=patient_id,
        nurse_id=nurse_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    if current_user.role == "patient":
        appt_filter.patient_id = current_user.id
    if current_user.role == "nurse":
        appt_filter.nurse_id = current_user.id

    skip = (pagination.page - 1) * pagination.page_size
    appointments, total = await service.list_appointments(
        appt_filter, skip=skip, limit=pagination.page_size
    )
    return AppointmentListResponse(
        items=[AppointmentResponse.model_validate(a) for a in appointments],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=max(1, -(-total // pagination.page_size)),
    )


@router.get("/availability")
async def check_availability(
    current_user: Annotated[User, Depends(require_roles("admin", "nurse", "patient"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    nurse_id: uuid.UUID = Query(...),
    date: date = Query(...),
    service_type: str | None = None,
) -> AvailabilityResponse:
    service = AppointmentService(db)
    slots = await service.check_availability(nurse_id, date, service_type)
    return AvailabilityResponse(available_slots=slots)


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_roles("admin", "nurse", "patient"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    service = AppointmentService(db)
    appointment = await service.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    if current_user.role == "patient" and current_user.id != appointment.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    if current_user.role == "nurse" and current_user.id != appointment.nurse_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return AppointmentResponse.model_validate(appointment)


@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: uuid.UUID,
    appointment_in: AppointmentUpdate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    service = AppointmentService(db)
    try:
        updated = await service.update_appointment(appointment_id, appointment_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return AppointmentResponse.model_validate(updated)


@router.patch("/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: uuid.UUID,
    status_update: AppointmentStatusUpdate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    service = AppointmentService(db)
    new_status = status_update.status.value
    try:
        if new_status == "confirmed":
            appointment = await service.confirm_appointment(appointment_id, actor_id=current_user.id)
        elif new_status == "in_progress":
            appointment = await service.start_appointment(appointment_id, actor_id=current_user.id)
        elif new_status == "completed":
            appointment = await service.complete_appointment(appointment_id, actor_id=current_user.id)
        elif new_status == "cancelled":
            appointment = await service.cancel_appointment(
                appointment_id, status_update.cancellation_reason, actor_id=current_user.id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}",
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AppointmentResponse.model_validate(appointment)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = AppointmentService(db)
    try:
        await service.delete_appointment(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
