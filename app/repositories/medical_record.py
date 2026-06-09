from datetime import datetime, timezone

from app.core.database import get_mongo_db

COLLECTION = "medical_records"


class MedicalRecordRepository:
    async def create(self, record_in: dict) -> dict:
        db = get_mongo_db()
        doc_id = record_in.get("id")
        record_in["_id"] = doc_id
        await db[COLLECTION].insert_one(record_in)
        return record_in

    async def get(self, record_id: str) -> dict | None:
        db = get_mongo_db()
        result = await db[COLLECTION].find_one({"_id": record_id})
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

    async def list_all(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[dict], int]:
        db = get_mongo_db()
        total = await db[COLLECTION].count_documents({})
        cursor = db[COLLECTION].find({}).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        for item in items:
            item["id"] = item.pop("_id")
        return items, total

    async def update(self, record_id: str, data: dict) -> dict | None:
        db = get_mongo_db()
        data["updated_at"] = datetime.now(timezone.utc)
        result = await db[COLLECTION].find_one_and_update(
            {"_id": record_id},
            {"$set": data},
            return_document=True,
        )
        if result:
            result["id"] = result.pop("_id")
        return result

    async def delete(self, record_id: str) -> bool:
        db = get_mongo_db()
        result = await db[COLLECTION].delete_one({"_id": record_id})
        return result.deleted_count > 0
