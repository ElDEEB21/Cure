import uuid
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import pagination_dependency, require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.base import PaginationParams
from app.schemas.user import UserListResponse, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(
    current_user: Annotated[
        User, Depends(require_roles("admin", "nurse", "patient"))
    ],
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me")
async def update_me(
    user_in: UserUpdate,
    current_user: Annotated[
        User, Depends(require_roles("admin", "nurse", "patient"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    service = UserService(db)
    user = await service.update_user(current_user.id, user_in, actor_id=current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


@router.get("")
async def list_users(
    current_user: Annotated[User, Depends(require_roles("admin"))],
    pagination: Annotated[PaginationParams, Depends(pagination_dependency)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserListResponse:
    service = UserService(db)
    skip = (pagination.page - 1) * pagination.page_size
    users, total = await service.get_users(skip=skip, limit=pagination.page_size)
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=max(1, -(-total // pagination.page_size)),
    )


@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[
        User, Depends(require_roles("admin", "nurse", "patient"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    if current_user.role == "patient" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    service = UserService(db)
    user = await service.update_user(user_id, user_in, actor_id=current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = UserService(db)
    deleted = await service.delete_user(user_id, actor_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
