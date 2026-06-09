import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import pagination_dependency, require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.base import PaginationParams
from app.schemas.patient import (
    PatientCreate,
    PatientFilter,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_in: PatientCreate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    service = PatientService(db)
    patient = await service.create_patient(patient_in, actor_id=current_user.id)
    return PatientResponse.model_validate(patient)


@router.get("")
async def list_patients(
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    pagination: Annotated[PaginationParams, Depends(pagination_dependency)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = None,
    gender: str | None = None,
    date_of_birth_from: date | None = None,
    date_of_birth_to: date | None = None,
) -> PatientListResponse:
    service = PatientService(db)
    filter = PatientFilter(
        search=search,
        gender=gender,
        date_of_birth_from=date_of_birth_from,
        date_of_birth_to=date_of_birth_to,
    )
    skip = (pagination.page - 1) * pagination.page_size
    patients, total = await service.search_patients(
        filter, skip=skip, limit=pagination.page_size
    )
    return PatientListResponse(
        items=[PatientResponse.model_validate(p) for p in patients],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=max(1, -(-total // pagination.page_size)),
    )


@router.get("/{patient_id}")
async def get_patient(
    patient_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_roles("admin", "nurse", "patient"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    service = PatientService(db)
    patient = await service.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    if current_user.role == "patient" and current_user.id != patient.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return PatientResponse.model_validate(patient)


@router.patch("/{patient_id}")
async def update_patient(
    patient_id: uuid.UUID,
    patient_in: PatientUpdate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    service = PatientService(db)
    patient = await service.update_patient(patient_id, patient_in, actor_id=current_user.id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = PatientService(db)
    deleted = await service.delete_patient(patient_id, actor_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
