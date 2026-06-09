import pytest
from httpx import AsyncClient

REGISTER_ADMIN = {
    "email": "admin@example.com",
    "password": "password123",
    "full_name": "Admin User",
    "role": "admin",
}
REGISTER_PATIENT = {
    "email": "patient@example.com",
    "password": "password123",
    "full_name": "Patient User",
    "role": "patient",
}
RECORD_DATA = {
    "patient_id": "patient-123",
    "diagnosis": "Hypertension",
    "medications": ["Lisinopril"],
    "allergies": ["Penicillin"],
    "blood_type": "A+",
    "notes": "Patient responding well",
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


@pytest.mark.asyncio
async def test_create_medical_record(
    client: AsyncClient, admin_tokens: dict
) -> None:
    response = await client.post(
        "/api/v1/medical-records",
        json=RECORD_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["diagnosis"] == "Hypertension"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_medical_records(
    client: AsyncClient, admin_tokens: dict
) -> None:
    await client.post(
        "/api/v1/medical-records",
        json=RECORD_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    response = await client.get(
        "/api/v1/medical-records",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_medical_record(
    client: AsyncClient, admin_tokens: dict
) -> None:
    create_resp = await client.post(
        "/api/v1/medical-records",
        json=RECORD_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    rid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/medical-records/{rid}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == rid


@pytest.mark.asyncio
async def test_update_medical_record(
    client: AsyncClient, admin_tokens: dict
) -> None:
    create_resp = await client.post(
        "/api/v1/medical-records",
        json=RECORD_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    rid = create_resp.json()["id"]
    response = await client.patch(
        f"/api/v1/medical-records/{rid}",
        json={"diagnosis": "Updated Diagnosis"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["diagnosis"] == "Updated Diagnosis"


@pytest.mark.asyncio
async def test_delete_medical_record(
    client: AsyncClient, admin_tokens: dict
) -> None:
    create_resp = await client.post(
        "/api/v1/medical-records",
        json=RECORD_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    rid = create_resp.json()["id"]
    response = await client.delete(
        f"/api/v1/medical-records/{rid}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_patient_cannot_create(
    client: AsyncClient, patient_tokens: dict
) -> None:
    response = await client.post(
        "/api/v1/medical-records",
        json=RECORD_DATA,
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patient_can_view_own_record(
    client: AsyncClient, patient_tokens: dict, admin_tokens: dict
) -> None:
    patient_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    my_uuid_hex = patient_resp.json()["id"].replace("-", "")
    record_data = {
        "patient_id": my_uuid_hex,
        "diagnosis": "Self-view Test",
        "medications": [],
    }
    create_resp = await client.post(
        "/api/v1/medical-records",
        json=record_data,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    rid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/medical-records/{rid}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["diagnosis"] == "Self-view Test"


@pytest.mark.asyncio
async def test_patient_cannot_view_others_record(
    client: AsyncClient, patient_tokens: dict, admin_tokens: dict
) -> None:
    record_data = {
        "patient_id": "some-other-uuid-hex",
        "diagnosis": "Private",
        "medications": [],
    }
    create_resp = await client.post(
        "/api/v1/medical-records",
        json=record_data,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    rid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/medical-records/{rid}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_not_found(
    client: AsyncClient, admin_tokens: dict
) -> None:
    response = await client.get(
        "/api/v1/medical-records/nonexistent-id",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 404
