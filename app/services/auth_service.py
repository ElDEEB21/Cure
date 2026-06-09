import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token, get_password_hash, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate
from app.services.audit_service import AuditService


def _create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"exp": expire, "sub": user_id, "type": "access", "role": role}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def _create_refresh_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = {"exp": expire, "sub": user_id, "type": "refresh", "role": role}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


class AuthService:
    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.repo = UserRepository(User, db)
        self.redis = redis
        self.audit = AuditService(db)

    async def register(self, user_in: UserCreate) -> User:
        existing = await self.repo.get_by_email(user_in.email)
        if existing:
            raise ValueError("Email already registered")
        hashed = get_password_hash(user_in.password)
        user = User(
            email=user_in.email,
            hashed_password=hashed,
            full_name=user_in.full_name,
            role=user_in.role or "patient",
        )
        self.repo.session.add(user)
        await self.repo.session.flush()
        await self.repo.session.refresh(user)
        try:
            await self.audit.log_action(
                actor_id=user.id,
                action="auth.register",
                resource_type="user",
                resource_id=str(user.id),
            )
        except Exception:
            pass
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is inactive")
        access_token = _create_access_token(str(user.id), user.role)
        refresh_token = _create_refresh_token(str(user.id), user.role)
        try:
            await self.audit.log_action(
                actor_id=user.id,
                action="auth.login",
                resource_type="user",
                resource_id=str(user.id),
            )
        except Exception:
            pass
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise ValueError("Invalid refresh token")
            user_id = payload.get("sub")
            role = payload.get("role")
            if not user_id or not role:
                raise ValueError("Invalid refresh token")
            if self.redis:
                blacklisted = await self.redis.get(f"blacklist:{refresh_token_str}")
                if blacklisted:
                    raise ValueError("Refresh token has been revoked")
            user = await self.repo.get(uuid.UUID(user_id))
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")
            access_token = _create_access_token(user_id, user.role)
            new_refresh_token = _create_refresh_token(user_id, user.role)
            return TokenResponse(
                access_token=access_token, refresh_token=new_refresh_token
            )
        except JWTError:
            raise ValueError("Invalid refresh token")

    async def logout(self, refresh_token_str: str, actor_id: Optional[uuid.UUID] = None) -> None:
        if self.redis:
            await self.redis.set(
                f"blacklist:{refresh_token_str}",
                "1",
                ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            )
        if actor_id:
            try:
                await self.audit.log_action(
                    actor_id=actor_id,
                    action="auth.logout",
                    resource_type="user",
                    resource_id=str(actor_id),
                )
            except Exception:
                pass
