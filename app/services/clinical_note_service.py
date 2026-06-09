from typing import Optional

from app.models.clinical_note import ClinicalNote
from app.repositories.clinical_note import ClinicalNoteRepository
from app.schemas.clinical_note import ClinicalNoteCreate, ClinicalNoteFilter, ClinicalNoteUpdate


class ClinicalNoteService:
    def __init__(self):
        self.repo = ClinicalNoteRepository()

    async def create_note(self, note_in: ClinicalNoteCreate) -> dict:
        note = ClinicalNote(**note_in.model_dump())
        return await self.repo.create(note.model_dump())

    async def get_note(self, note_id: str) -> Optional[dict]:
        return await self.repo.get(note_id)

    async def update_note(
        self, note_id: str, note_in: ClinicalNoteUpdate
    ) -> Optional[dict]:
        data = note_in.model_dump(exclude_unset=True)
        if not data:
            return await self.repo.get(note_id)
        return await self.repo.update(note_id, data)

    async def delete_note(self, note_id: str) -> bool:
        return await self.repo.delete(note_id)

    async def list_notes(
        self, filter: ClinicalNoteFilter, skip: int = 0, limit: int = 20
    ) -> tuple[list[dict], int]:
        if filter.patient_id:
            return await self.repo.get_by_patient(filter.patient_id, skip=skip, limit=limit)
        return await self.repo.list_all(
            skip=skip,
            limit=limit,
            note_type=filter.note_type,
            tag=filter.tag,
            search=filter.search,
        )
