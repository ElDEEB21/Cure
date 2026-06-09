from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

mongo_client: AsyncIOMotorClient | None = None


def get_mongo_db() -> AsyncIOMotorDatabase:
    if mongo_client is None:
        raise RuntimeError("MongoDB client not initialized. Call init_db() first.")
    return mongo_client[settings.MONGO_DB_NAME]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    global mongo_client
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    mongo_client = AsyncIOMotorClient(settings.MONGO_URL)


async def close_db() -> None:
    global mongo_client
    await engine.dispose()
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
