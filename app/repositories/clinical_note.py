from datetime import datetime, timezone
from typing import Any

from app.core.database import get_mongo_db

COLLECTION = "clinical_notes"


class ClinicalNoteRepository:
    async def create(self, note_in: dict) -> dict:
        db = get_mongo_db()
        doc_id = note_in.get("id")
        note_in["_id"] = doc_id
        await db[COLLECTION].insert_one(note_in)
        return note_in

    async def get(self, note_id: str) -> dict | None:
        db = get_mongo_db()
        result = await db[COLLECTION].find_one({"_id": note_id})
        if result:
            result["id"] = result.pop("_id")
        return result

    async def get_by_patient(
        self, patient_id: str, skip: int = 0, limit: int = 20
    ) -> tuple[list[dict], int]:
        db = get_mongo_db()
        query = {"patient_id": patient_id}
        total = await db[COLLECTION].count_documents(query)
        cursor = db[COLLECTION].find(query).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        for item in items:
            item["id"] = item.pop("_id")
        return items, total

    async def get_by_author(
        self, author_id: str, skip: int = 0, limit: int = 20
    ) -> tuple[list[dict], int]:
        db = get_mongo_db()
        query = {"author_id": author_id}
        total = await db[COLLECTION].count_documents(query)
        cursor = db[COLLECTION].find(query).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        for item in items:
            item["id"] = item.pop("_id")
        return items, total

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 20,
        note_type: str | None = None,
        tag: str | None = None,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        db = get_mongo_db()
        query: dict[str, Any] = {}
        if note_type:
            query["note_type"] = note_type
        if tag:
            query["tags"] = tag
        if search:
            query["content"] = {"$regex": search, "$options": "i"}
        total = await db[COLLECTION].count_documents(query)
        cursor = db[COLLECTION].find(query).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        for item in items:
            item["id"] = item.pop("_id")
        return items, total

    async def update(self, note_id: str, data: dict) -> dict | None:
        db = get_mongo_db()
        data["updated_at"] = datetime.now(timezone.utc)
        result = await db[COLLECTION].find_one_and_update(
            {"_id": note_id},
            {"$set": data},
            return_document=True,
        )
        if result:
            result["id"] = result.pop("_id")
        return result

    async def delete(self, note_id: str) -> bool:
        db = get_mongo_db()
        result = await db[COLLECTION].delete_one({"_id": note_id})
        return result.deleted_count > 0
