import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import database as db_module
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)

TestSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _fake_redis_store.clear()
    db_module.mongo_client = FakeMongoDB()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


_fake_redis_store: dict[str, str] = {}


class FakeRedis:
    async def get(self, key: str) -> str | None:
        return _fake_redis_store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        _fake_redis_store[key] = value

    async def delete(self, key: str) -> None:
        _fake_redis_store.pop(key, None)

    async def close(self) -> None:
        _fake_redis_store.clear()


_fake_redis_instance = FakeRedis()


async def override_get_redis() -> AsyncGenerator[FakeRedis, None]:
    yield _fake_redis_instance


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis


class FakeMongoCollection:
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}

    def __getitem__(self, name: str) -> "FakeMongoCollection":
        return self

    async def insert_one(self, document: dict[str, Any]) -> Any:
        doc = dict(document)
        if "_id" not in doc or doc["_id"] is None:
            doc["_id"] = str(uuid.uuid4().hex[:24])
        oid = doc["_id"]
        self._docs[oid] = doc
        result = type("InsertOneResult", (), {"inserted_id": oid, "acknowledged": True})
        return result()

    async def find_one(self, filter: dict[str, Any] | None) -> dict[str, Any] | None:
        if not filter:
            docs = list(self._docs.values())
            return dict(docs[0]) if docs else None
        if "_id" in filter:
            oid_str = str(filter["_id"])
            doc = self._docs.get(oid_str)
            return dict(doc) if doc else None
        if "$regex" in filter.get("content", {}):
            import re
            pattern = filter["content"]["$regex"]
            flags = re.IGNORECASE if filter["content"].get("$options", "") == "i" else 0
            for doc in self._docs.values():
                if re.search(pattern, doc.get("content", ""), flags):
                    return dict(doc)
        return None

    async def count_documents(self, filter: dict[str, Any]) -> int:
        if not filter:
            return len(self._docs)
        return sum(
            1 for d in self._docs.values()
            if all(d.get(k) == v for k, v in filter.items())
        )

    def find(self, filter: dict[str, Any] | None = None) -> "FakeMongoCollection":
        docs = list(self._docs.values())
        if filter:
            docs = [d for d in docs if all(d.get(k) == v for k, v in filter.items())]
        self._cursor_docs = docs
        return self

    def skip(self, n: int) -> "FakeMongoCollection":
        if hasattr(self, "_cursor_docs"):
            self._cursor_docs = self._cursor_docs[n:]
        return self

    def limit(self, n: int) -> "FakeMongoCollection":
        if hasattr(self, "_cursor_docs"):
            self._cursor_docs = self._cursor_docs[:n]
        return self

    async def to_list(self, length: int) -> list[dict[str, Any]]:
        docs = getattr(self, "_cursor_docs", list(self._docs.values()))
        return [dict(d) for d in docs[:length]]

    async def find_one_and_update(
        self, filter: dict[str, Any], update: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any] | None:
        if "_id" in filter:
            oid_str = str(filter["_id"])
            if oid_str in self._docs:
                if "$set" in update:
                    self._docs[oid_str].update(update["$set"])
                return dict(self._docs[oid_str])
        return None

    async def delete_one(self, filter: dict[str, Any]) -> Any:
        if "_id" in filter:
            oid_str = str(filter["_id"])
            if oid_str in self._docs:
                del self._docs[oid_str]
                result = type("DeleteResult", (), {"deleted_count": 1, "acknowledged": True})
                return result()
        result = type("DeleteResult", (), {"deleted_count": 0, "acknowledged": True})
        return result()


class FakeMongoDB:
    def __init__(self) -> None:
        self._collections: dict[str, FakeMongoCollection] = {}

    async def list_collection_names(self) -> list[str]:
        return list(self._collections.keys())

    def __getitem__(self, name: str) -> FakeMongoCollection:
        if name not in self._collections:
            self._collections[name] = FakeMongoCollection()
        return self._collections[name]

    def __getattr__(self, name: str) -> Any:
        return self.__getitem__(name)

    async def __aenter__(self) -> "FakeMongoDB":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


db_module.mongo_client = FakeMongoDB()  # type: ignore[assignment]


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
