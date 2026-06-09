import pytest
from httpx import AsyncClient

REGISTER_PATIENT = {
    "email": "patient@example.com",
    "password": "password123",
    "full_name": "Patient User",
    "role": "patient",
}
REGISTER_NURSE = {
    "email": "nurse@example.com",
    "password": "password123",
    "full_name": "Nurse User",
    "role": "nurse",
}
REGISTER_ADMIN = {
    "email": "admin@example.com",
    "password": "password123",
    "full_name": "Admin User",
    "role": "admin",
}
PATIENT_DATA = {
    "date_of_birth": "1990-01-15",
    "gender": "male",
    "phone": "+1234567890",
    "address": "123 Main St",
    "emergency_contact": "Jane Doe",
}


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


@pytest.fixture
async def nurse_tokens(client: AsyncClient) -> dict:
    await client.post("/api/v1/auth/register", json=REGISTER_NURSE)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_NURSE["email"],
            "password": REGISTER_NURSE["password"],
        },
    )
    return resp.json()


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
async def patient_id(client: AsyncClient, admin_tokens: dict) -> str:
    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    return me_resp.json()["id"]


@pytest.mark.asyncio
async def test_create_patient(
    client: AsyncClient, admin_tokens: dict, patient_id: str
) -> None:
    response = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["gender"] == "male"
    assert data["phone"] == "+1234567890"
    assert "id" in data


@pytest.mark.asyncio
async def test_nurse_can_create_patient(
    client: AsyncClient, nurse_tokens: dict, patient_id: str
) -> None:
    response = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {nurse_tokens['access_token']}"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_patient_cannot_create_patient(
    client: AsyncClient, patient_tokens: dict, patient_id: str
) -> None:
    response = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_patients(
    client: AsyncClient, admin_tokens: dict, patient_id: str
) -> None:
    await client.post(
        "/api/v1/patients",
        json={"user_id": patient_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    response = await client.get(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_patient(
    client: AsyncClient, admin_tokens: dict, patient_id: str
) -> None:
    create_resp = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    pid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/patients/{pid}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == pid


@pytest.mark.asyncio
async def test_patient_can_view_own(
    client: AsyncClient, admin_tokens: dict, patient_tokens: dict
) -> None:
    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    patient_user_id = me_resp.json()["id"]
    create_resp = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_user_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    pid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/patients/{pid}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_patient(
    client: AsyncClient, admin_tokens: dict, patient_id: str
) -> None:
    create_resp = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    pid = create_resp.json()["id"]
    response = await client.patch(
        f"/api/v1/patients/{pid}",
        json={"phone": "+9876543210"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "+9876543210"


@pytest.mark.asyncio
async def test_delete_patient(
    client: AsyncClient, admin_tokens: dict, patient_id: str
) -> None:
    create_resp = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    pid = create_resp.json()["id"]
    response = await client.delete(
        f"/api/v1/patients/{pid}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_patient_not_found(
    client: AsyncClient, admin_tokens: dict
) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/v1/patients/{fake_id}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 404
