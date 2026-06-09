from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import pagination_dependency, require_roles
from app.models.user import User
from app.schemas.base import PaginationParams
from app.schemas.clinical_note import (
    ClinicalNoteCreate,
    ClinicalNoteFilter,
    ClinicalNoteListResponse,
    ClinicalNoteResponse,
    ClinicalNoteUpdate,
)
from app.services.clinical_note_service import ClinicalNoteService

router = APIRouter(prefix="/clinical-notes", tags=["clinical-notes"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_clinical_note(
    note_in: ClinicalNoteCreate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
) -> ClinicalNoteResponse:
    service = ClinicalNoteService()
    note = await service.create_note(note_in)
    return ClinicalNoteResponse(**note)


@router.get("")
async def list_clinical_notes(
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
    pagination: Annotated[PaginationParams, Depends(pagination_dependency)],
    patient_id: str | None = None,
    note_type: str | None = None,
    tag: str | None = None,
    search: str | None = None,
) -> ClinicalNoteListResponse:
    service = ClinicalNoteService()
    filter = ClinicalNoteFilter(
        patient_id=patient_id, note_type=note_type, tag=tag, search=search
    )
    skip = (pagination.page - 1) * pagination.page_size
    notes, total = await service.list_notes(
        filter, skip=skip, limit=pagination.page_size
    )
    return ClinicalNoteListResponse(
        items=[ClinicalNoteResponse(**n) for n in notes],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=max(1, -(-total // pagination.page_size)),
    )


@router.get("/{note_id}")
async def get_clinical_note(
    note_id: str,
    current_user: Annotated[
        User, Depends(require_roles("admin", "nurse", "patient"))
    ],
) -> ClinicalNoteResponse:
    service = ClinicalNoteService()
    note = await service.get_note(note_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical note not found",
        )
    if current_user.role == "patient" and current_user.id.hex != note.get("patient_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return ClinicalNoteResponse(**note)


@router.patch("/{note_id}")
async def update_clinical_note(
    note_id: str,
    note_in: ClinicalNoteUpdate,
    current_user: Annotated[User, Depends(require_roles("admin", "nurse"))],
) -> ClinicalNoteResponse:
    service = ClinicalNoteService()
    note = await service.update_note(note_id, note_in)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical note not found",
        )
    return ClinicalNoteResponse(**note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinical_note(
    note_id: str,
    current_user: Annotated[User, Depends(require_roles("admin"))],
) -> None:
    service = ClinicalNoteService()
    deleted = await service.delete_note(note_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical note not found",
        )
