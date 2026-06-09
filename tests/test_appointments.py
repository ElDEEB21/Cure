import pytest
from httpx import AsyncClient

REGISTER_PATIENT = {
    "email": "appt_patient@example.com",
    "password": "password123",
    "full_name": "Appt Patient",
    "role": "patient",
}
REGISTER_NURSE = {
    "email": "appt_nurse@example.com",
    "password": "password123",
    "full_name": "Appt Nurse",
    "role": "nurse",
}
REGISTER_ADMIN = {
    "email": "appt_admin@example.com",
    "password": "password123",
    "full_name": "Appt Admin",
    "role": "admin",
}

APPOINTMENT_BASE = {
    "scheduled_at": "2026-06-10T10:00:00Z",
    "duration_minutes": 30,
    "service_type": "checkup",
    "notes": "Routine checkup",
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
async def nurse_id(client: AsyncClient, nurse_tokens: dict) -> str:
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {nurse_tokens['access_token']}"},
    )
    return resp.json()["id"]


@pytest.fixture
async def patient_id(client: AsyncClient, patient_tokens: dict) -> str:
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_appointment(
    client: AsyncClient, admin_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "scheduled"
    assert data["service_type"] == "checkup"
    assert data["patient_id"] == patient_id
    assert data["nurse_id"] == nurse_id
    assert "id" in data


@pytest.mark.asyncio
async def test_nurse_can_create_appointment(
    client: AsyncClient, nurse_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {nurse_tokens['access_token']}"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_patient_cannot_create_appointment(
    client: AsyncClient, patient_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_appointments_with_filter(
    client: AsyncClient, admin_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    response = await client.get(
        f"/api/v1/appointments?nurse_id={nurse_id}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_status_transitions(
    client: AsyncClient, admin_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    appt_id = create_resp.json()["id"]

    confirm_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    start_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"

    complete_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_invalid_status_transition(
    client: AsyncClient, admin_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    appt_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancellation_with_reason(
    client: AsyncClient, admin_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    appt_id = create_resp.json()["id"]

    cancel_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "cancelled", "cancellation_reason": "Patient unavailable"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
    assert cancel_resp.json()["cancellation_reason"] == "Patient unavailable"


@pytest.mark.asyncio
async def test_nurse_conflict_detection(
    client: AsyncClient, admin_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )

    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 400
    assert "conflicting" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_role_enforcement_patient_view_only_own(
    client: AsyncClient,
    admin_tokens: dict,
    nurse_tokens: dict,
    patient_tokens: dict,
    nurse_id: str,
    patient_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    appt_id = create_resp.json()["id"]

    other_patient_resp = await client.get(
        f"/api/v1/appointments/{appt_id}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert other_patient_resp.status_code == 200

    other_patient_data = {
        "email": "other_appt_patient@example.com",
        "password": "password123",
        "full_name": "Other Patient",
        "role": "patient",
    }
    await client.post("/api/v1/auth/register", json=other_patient_data)
    other_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": other_patient_data["email"],
            "password": other_patient_data["password"],
        },
    )
    other_tokens = other_login.json()

    response = await client.get(
        f"/api/v1/appointments/{appt_id}",
        headers={"Authorization": f"Bearer {other_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_availability_check(
    client: AsyncClient, admin_tokens: dict, nurse_id: str
) -> None:
    response = await client.get(
        "/api/v1/appointments/availability",
        params={"nurse_id": nurse_id, "date": "2026-06-10"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "available_slots" in data
    assert len(data["available_slots"]) > 0


@pytest.mark.asyncio
async def test_appointment_not_found(
    client: AsyncClient, admin_tokens: dict
) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/v1/appointments/{fake_id}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_geographical_constraint(
    client: AsyncClient, admin_tokens: dict, nurse_id: str, patient_id: str
) -> None:
    response = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
            "location_lat": 30.0,
            "location_lng": 31.0,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 400
    assert "latitude" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patient_can_view_own_appointment(
    client: AsyncClient,
    admin_tokens: dict,
    patient_tokens: dict,
    nurse_id: str,
    patient_id: str,
) -> None:
    create_resp = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    appt_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/appointments/{appt_id}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == appt_id
