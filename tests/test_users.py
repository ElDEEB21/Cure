import pytest
from httpx import AsyncClient

REGISTER_PATIENT = {
    "email": "patient@example.com",
    "password": "password123",
    "full_name": "Patient User",
    "role": "patient",
}
REGISTER_ADMIN = {
    "email": "admin@example.com",
    "password": "password123",
    "full_name": "Admin User",
    "role": "admin",
}


@pytest.fixture
async def patient_tokens(client: AsyncClient) -> dict:
    await client.post("/api/v1/auth/register", json=REGISTER_PATIENT)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PATIENT["email"],
            "password": REGISTER_PATIENT["password"],
        },
    )
    return resp.json()


@pytest.fixture
async def admin_tokens(client: AsyncClient) -> dict:
    await client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_ADMIN["email"],
            "password": REGISTER_ADMIN["password"],
        },
    )
    return resp.json()


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, patient_tokens: dict) -> None:
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == REGISTER_PATIENT["email"]
    assert data["full_name"] == REGISTER_PATIENT["full_name"]


@pytest.mark.asyncio
async def test_get_me_without_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient, patient_tokens: dict) -> None:
    response = await client.patch(
        "/api/v1/users/me",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_admin_list_users(
    client: AsyncClient, admin_tokens: dict
) -> None:
    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_patient_cannot_list_users(
    client: AsyncClient, patient_tokens: dict
) -> None:
    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_get_user_by_id(
    client: AsyncClient, admin_tokens: dict, patient_tokens: dict
) -> None:
    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    patient_id = me_resp.json()["id"]
    response = await client.get(
        f"/api/v1/users/{patient_id}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == REGISTER_PATIENT["email"]


@pytest.mark.asyncio
async def test_patient_cannot_view_other_user(
    client: AsyncClient, patient_tokens: dict
) -> None:
    random_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/v1/users/{random_id}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_user(
    client: AsyncClient, admin_tokens: dict, patient_tokens: dict
) -> None:
    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    patient_id = me_resp.json()["id"]
    response = await client.patch(
        f"/api/v1/users/{patient_id}",
        json={"full_name": "Admin Updated"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Admin Updated"


@pytest.mark.asyncio
async def test_admin_delete_user(
    client: AsyncClient, admin_tokens: dict, patient_tokens: dict
) -> None:
    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    patient_id = me_resp.json()["id"]
    response = await client.delete(
        f"/api/v1/users/{patient_id}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 204
