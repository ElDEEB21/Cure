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
NOTE_DATA = {
    "patient_id": "patient-123",
    "author_id": "author-456",
    "note_type": "progress",
    "content": "Patient shows improvement in mobility",
    "tags": ["physiotherapy", "progress"],
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
async def test_create_clinical_note(
    client: AsyncClient, admin_tokens: dict
) -> None:
    response = await client.post(
        "/api/v1/clinical-notes",
        json=NOTE_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["note_type"] == "progress"
    assert data["content"] == NOTE_DATA["content"]
    assert "id" in data


@pytest.mark.asyncio
async def test_list_clinical_notes(
    client: AsyncClient, admin_tokens: dict
) -> None:
    await client.post(
        "/api/v1/clinical-notes",
        json=NOTE_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    response = await client.get(
        "/api/v1/clinical-notes",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_clinical_note(
    client: AsyncClient, admin_tokens: dict
) -> None:
    create_resp = await client.post(
        "/api/v1/clinical-notes",
        json=NOTE_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    nid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/clinical-notes/{nid}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == nid


@pytest.mark.asyncio
async def test_update_clinical_note(
    client: AsyncClient, admin_tokens: dict
) -> None:
    create_resp = await client.post(
        "/api/v1/clinical-notes",
        json=NOTE_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    nid = create_resp.json()["id"]
    response = await client.patch(
        f"/api/v1/clinical-notes/{nid}",
        json={"content": "Updated note content"},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated note content"


@pytest.mark.asyncio
async def test_delete_clinical_note(
    client: AsyncClient, admin_tokens: dict
) -> None:
    create_resp = await client.post(
        "/api/v1/clinical-notes",
        json=NOTE_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    nid = create_resp.json()["id"]
    response = await client.delete(
        f"/api/v1/clinical-notes/{nid}",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_patient_cannot_create(
    client: AsyncClient, patient_tokens: dict
) -> None:
    response = await client.post(
        "/api/v1/clinical-notes",
        json=NOTE_DATA,
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_not_found(client: AsyncClient, admin_tokens: dict) -> None:
    response = await client.get(
        "/api/v1/clinical-notes/nonexistent-id",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patient_can_view_own_note(
    client: AsyncClient, patient_tokens: dict, admin_tokens: dict
) -> None:
    patient_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    my_uuid_hex = patient_resp.json()["id"].replace("-", "")
    note_data = {
        "patient_id": my_uuid_hex,
        "author_id": "admin",
        "note_type": "consultation",
        "content": "Follow-up required",
        "tags": ["follow-up"],
    }
    create_resp = await client.post(
        "/api/v1/clinical-notes",
        json=note_data,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    nid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/clinical-notes/{nid}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Follow-up required"


@pytest.mark.asyncio
async def test_patient_cannot_view_others_note(
    client: AsyncClient, patient_tokens: dict, admin_tokens: dict
) -> None:
    note_data = {
        "patient_id": "some-other-uuid-hex",
        "author_id": "admin",
        "note_type": "consultation",
        "content": "Private note",
        "tags": [],
    }
    create_resp = await client.post(
        "/api/v1/clinical-notes",
        json=note_data,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    nid = create_resp.json()["id"]
    response = await client.get(
        f"/api/v1/clinical-notes/{nid}",
        headers={"Authorization": f"Bearer {patient_tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_filter_by_note_type(
    client: AsyncClient, admin_tokens: dict
) -> None:
    await client.post(
        "/api/v1/clinical-notes",
        json=NOTE_DATA,
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    response = await client.get(
        "/api/v1/clinical-notes?note_type=progress",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert response.status_code == 200
