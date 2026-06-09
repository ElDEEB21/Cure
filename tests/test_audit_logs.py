import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.audit_service import AuditService
from tests.conftest import TestSessionLocal


@pytest.mark.asyncio
async def test_audit_log_created_on_register(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "audit-test@example.com",
            "password": "password123",
            "full_name": "Audit Test",
            "role": "admin",
        },
    )
    assert response.status_code == 201

    from app.models.audit_log import AuditLog

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "auth.register")
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.action == "auth.register"
        assert log.resource_type == "user"


@pytest.mark.asyncio
async def test_audit_log_list_admin_only(client: AsyncClient) -> None:
    admin_user_id = await _create_admin_user()
    admin_token = _create_admin_token(admin_user_id)

    response = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_audit_log_list_non_admin_forbidden(client: AsyncClient) -> None:
    patient_token = await _create_patient_token()

    response = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_get_specific(client: AsyncClient) -> None:
    admin_user_id = await _create_admin_user()
    admin_token = _create_admin_token(admin_user_id)

    async with TestSessionLocal() as session:
        service = AuditService(session)
        log = await service.log_action(
            actor_id=admin_user_id,
            action="test.action",
            resource_type="test",
            resource_id="123",
        )
        log_id = log.id
        await session.commit()

    response = await client.get(
        f"/api/v1/audit-logs/{log_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "test.action"
    assert data["resource_type"] == "test"
    assert data["resource_id"] == "123"


@pytest.mark.asyncio
async def test_audit_log_get_not_found(client: AsyncClient) -> None:
    admin_user_id = await _create_admin_user()
    admin_token = _create_admin_token(admin_user_id)

    response = await client.get(
        f"/api/v1/audit-logs/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def _create_admin_user() -> uuid.UUID:
    async with TestSessionLocal() as session:
        repo = UserRepository(User, session)
        existing = await repo.get_by_email("admin-audit@example.com")
        if existing:
            return existing.id
        user = User(
            email="admin-audit@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Admin Audit",
            role="admin",
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        await session.commit()
        return user.id


def _create_admin_token(user_id: uuid.UUID) -> str:
    return create_access_token(str(user_id))


async def _create_patient_token() -> str:
    async with TestSessionLocal() as session:
        repo = UserRepository(User, session)
        existing = await repo.get_by_email("patient-audit@example.com")
        if existing:
            user_id = existing.id
        else:
            user = User(
                email="patient-audit@example.com",
                hashed_password=get_password_hash("password123"),
                full_name="Patient Audit",
                role="patient",
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            await session.commit()
            user_id = user.id
    return create_access_token(str(user_id))
