from fastapi import APIRouter

from app.api.v1.endpoints import (
    appointments,
    audit_logs,
    auth,
    clinical_notes,
    medical_records,
    patients,
    users,
)

router = APIRouter(prefix="")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(patients.router)
router.include_router(medical_records.router)
router.include_router(clinical_notes.router)
router.include_router(appointments.router)
router.include_router(audit_logs.router)
