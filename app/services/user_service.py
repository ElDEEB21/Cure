import uuid
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserUpdate
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(User, db)
        self.audit = AuditService(db)

    async def get_user(self, user_id: uuid.UUID) -> Optional[User]:
        return await self.repo.get(user_id)

    async def get_users(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[Sequence[User], int]:
        users = await self.repo.get_multi(skip=skip, limit=limit)
        total = await self.repo.count()
        return users, total

    async def update_user(
        self, user_id: uuid.UUID, user_in: UserUpdate, actor_id: Optional[uuid.UUID] = None
    ) -> Optional[User]:
        user = await self.repo.get(user_id)
        if not user:
            return None
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"] is not None:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )
        updated = await self.repo.update(user, update_data)
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="user.update",
                    resource_type="user",
                    resource_id=str(user_id),
                )
            except Exception:
                pass
        return updated

    async def delete_user(self, user_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None) -> bool:
        user = await self.repo.get(user_id)
        if not user:
            return False
        await self.repo.delete(user_id)
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="user.delete",
                    resource_type="user",
                    resource_id=str(user_id),
                )
            except Exception:
                pass
        return True
