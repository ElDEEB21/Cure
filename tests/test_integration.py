import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.audit_log import AuditLog
from tests.conftest import TestSessionLocal

REGISTER_ADMIN = {
    "email": "int_admin@example.com",
    "password": "password123",
    "full_name": "Integration Admin",
    "role": "admin",
}
REGISTER_PATIENT_USER = {
    "email": "int_patient@example.com",
    "password": "password123",
    "full_name": "Integration Patient",
    "role": "patient",
}
REGISTER_NURSE = {
    "email": "int_nurse@example.com",
    "password": "password123",
    "full_name": "Integration Nurse",
    "role": "nurse",
}
PATIENT_DATA = {
    "date_of_birth": "1990-01-15",
    "gender": "female",
    "phone": "+1234567890",
    "address": "123 Main St",
    "emergency_contact": "Jane Doe",
}
APPOINTMENT_BASE = {
    "scheduled_at": "2026-06-20T10:00:00Z",
    "duration_minutes": 30,
    "service_type": "checkup",
    "notes": "Integration test appointment",
    "location_lat": 25.5,
    "location_lng": 47.5,
}


@pytest.mark.asyncio
async def test_full_integration_flow(client: AsyncClient) -> None:
    # 1. Register admin user
    admin_resp = await client.post(
        "/api/v1/auth/register", json=REGISTER_ADMIN
    )
    assert admin_resp.status_code == 201
    admin_id = admin_resp.json()["id"]

    # 2. Register nurse user
    nurse_resp = await client.post(
        "/api/v1/auth/register", json=REGISTER_NURSE
    )
    assert nurse_resp.status_code == 201
    nurse_id = nurse_resp.json()["id"]

    # 3. Register patient user
    patient_resp = await client.post(
        "/api/v1/auth/register", json=REGISTER_PATIENT_USER
    )
    assert patient_resp.status_code == 201
    patient_user_id = patient_resp.json()["id"]

    # 4. Login as admin
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_ADMIN["email"],
            "password": REGISTER_ADMIN["password"],
        },
    )
    assert admin_login.status_code == 200
    admin_tokens = admin_login.json()
    admin_access = admin_tokens["access_token"]

    # 5. Create patient profile (admin creates for the patient user)
    patient_resp = await client.post(
        "/api/v1/patients",
        json={"user_id": patient_user_id, **PATIENT_DATA},
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert patient_resp.status_code == 201
    patient_id = patient_resp.json()["id"]
    assert patient_resp.json()["gender"] == "female"

    # 6. Create medical record (admin)
    med_rec_resp = await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_user_id.replace("-", ""),
            "diagnosis": "Hypertension",
            "medications": ["Lisinopril"],
            "allergies": ["Penicillin"],
            "blood_type": "A+",
            "notes": "Initial diagnosis",
        },
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert med_rec_resp.status_code == 201
    med_rec_id = med_rec_resp.json()["id"]
    assert med_rec_resp.json()["diagnosis"] == "Hypertension"

    # 7. Create clinical note (admin)
    note_resp = await client.post(
        "/api/v1/clinical-notes",
        json={
            "patient_id": patient_user_id.replace("-", ""),
            "author_id": admin_id.replace("-", ""),
            "note_type": "progress",
            "content": "Patient responding well to treatment",
            "tags": ["hypertension", "follow-up"],
        },
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert note_resp.status_code == 201
    note_id = note_resp.json()["id"]
    assert note_resp.json()["note_type"] == "progress"

    # 8. Schedule appointment (admin)
    appt_resp = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_user_id,
            "nurse_id": nurse_id,
            **APPOINTMENT_BASE,
        },
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert appt_resp.status_code == 201
    appt_id = appt_resp.json()["id"]
    assert appt_resp.json()["status"] == "scheduled"

    # 9. Confirm appointment
    confirm_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    # 10. Start appointment (in_progress)
    start_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"

    # 11. Complete appointment
    complete_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    # 12. Login as patient
    patient_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PATIENT_USER["email"],
            "password": REGISTER_PATIENT_USER["password"],
        },
    )
    assert patient_login.status_code == 200
    patient_tokens = patient_login.json()
    patient_access = patient_tokens["access_token"]

    # 13. Verify patient can view own data
    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {patient_access}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == REGISTER_PATIENT_USER["email"]

    # 14. Patient can view own patient profile
    pt_resp = await client.get(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": f"Bearer {patient_access}"},
    )
    assert pt_resp.status_code == 200

    # 15. Patient can view own medical record
    mr_resp = await client.get(
        f"/api/v1/medical-records/{med_rec_id}",
        headers={"Authorization": f"Bearer {patient_access}"},
    )
    assert mr_resp.status_code == 200

    # 16. Patient can view own clinical note
    cn_resp = await client.get(
        f"/api/v1/clinical-notes/{note_id}",
        headers={"Authorization": f"Bearer {patient_access}"},
    )
    assert cn_resp.status_code == 200

    # 17. Patient can view own appointment
    appt_get_resp = await client.get(
        f"/api/v1/appointments/{appt_id}",
        headers={"Authorization": f"Bearer {patient_access}"},
    )
    assert appt_get_resp.status_code == 200

    # 18. Log admin out, verify token blacklist
    admin_logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": admin_tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert admin_logout.status_code == 200
    assert admin_logout.json()["message"] == "Successfully logged out"

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": admin_tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 401

    # 19. Verify audit logs were created (patient can't view, but admin could)
    async with TestSessionLocal() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "auth.register")
        )
        logs = result.scalars().all()
        assert len(logs) >= 3

        result2 = await session.execute(
            select(AuditLog).where(AuditLog.action == "appointment.schedule")
        )
        appt_log = result2.scalar_one_or_none()
        assert appt_log is not None
        assert appt_log.resource_type == "appointment"
