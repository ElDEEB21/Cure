from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import pagination_dependency, require_roles
from app.models.user import User
from app.schemas.base import PaginationParams
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordFilter,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)
from app.services.medical_record_service import MedicalRecordService

router = APIRouter(prefix="/medical-records", tags=["medical-records"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_medical_record(
    record_in: MedicalRecordCreate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
) -> MedicalRecordResponse:
    service = MedicalRecordService()
    record = await service.create_record(record_in)
    return MedicalRecordResponse(**record)


@router.get("")
async def list_medical_records(
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    pagination: Annotated[PaginationParams, Depends(pagination_dependency)],
    patient_id: str | None = None,
    diagnosis: str | None = None,
) -> MedicalRecordListResponse:
    service = MedicalRecordService()
    filter = MedicalRecordFilter(patient_id=patient_id, diagnosis=diagnosis)
    skip = (pagination.page - 1) * pagination.page_size
    records, total = await service.list_records(
        filter, skip=skip, limit=pagination.page_size
    )
    return MedicalRecordListResponse(
        items=[MedicalRecordResponse(**r) for r in records],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=max(1, -(-total // pagination.page_size)),
    )


@router.get("/{record_id}")
async def get_medical_record(
    record_id: str,
    current_user: Annotated[
        User, Depends(require_roles("admin", "nurse", "patient"))
    ],
) -> MedicalRecordResponse:
    service = MedicalRecordService()
    record = await service.get_record(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    if current_user.role == "patient" and current_user.id.hex != record.get("patient_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return MedicalRecordResponse(**record)


@router.patch("/{record_id}")
async def update_medical_record(
    record_id: str,
    record_in: MedicalRecordUpdate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
) -> MedicalRecordResponse:
    service = MedicalRecordService()
    record = await service.update_record(record_id, record_in)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    return MedicalRecordResponse(**record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_record(
    record_id: str,
    current_user: Annotated[User, Depends(require_roles("admin"))],
) -> None:
    service = MedicalRecordService()
    deleted = await service.delete_record(record_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
