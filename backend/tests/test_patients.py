from app.core.exceptions import InvalidPayloadError, PatientNotFoundError
from app.schemas.patient import PatientCreate
from app.services.patient_service import PatientService

VALID_PATIENT = {
    "patient_identifier": "TEST-001",
    "age": 56,
    "gender": "male",
    "weight_kg": 91,
    "height_cm": 172,
    "smoking_status": "former",
    "systolic_bp": 148,
    "diastolic_bp": 92,
    "heart_rate": 78,
    "total_cholesterol": 225,
    "ldl": 148,
    "hdl": 39,
    "triglycerides": 210,
    "hba1c": 7.8,
    "fasting_glucose": 158,
    "medical_history": ["type_2_diabetes", "hypertension"],
    "current_medications": ["metformin"],
    "allergies": [],
}


def test_create_and_get_patient(db_session):
    service = PatientService(db_session)
    created = service.create_patient(PatientCreate(**VALID_PATIENT))

    assert created.id is not None
    assert created.patient_identifier == "TEST-001"
    assert created.medical_history == ["type_2_diabetes", "hypertension"]

    fetched = service.get_patient(created.id)
    assert fetched.patient_identifier == "TEST-001"
    assert fetched.bmi is None  # not supplied, agent computes it later


def test_duplicate_identifier_rejected(db_session):
    service = PatientService(db_session)
    service.create_patient(PatientCreate(**VALID_PATIENT))

    try:
        service.create_patient(PatientCreate(**VALID_PATIENT))
        assert False, "expected InvalidPayloadError"
    except InvalidPayloadError:
        pass


def test_get_missing_patient_raises(db_session):
    service = PatientService(db_session)
    try:
        service.get_patient(9999)
        assert False, "expected PatientNotFoundError"
    except PatientNotFoundError:
        pass


def test_list_patients(db_session):
    service = PatientService(db_session)
    service.create_patient(PatientCreate(**VALID_PATIENT))
    other = dict(VALID_PATIENT)
    other["patient_identifier"] = "TEST-002"
    service.create_patient(PatientCreate(**other))

    patients = service.list_patients()
    assert len(patients) == 2


def test_patient_api_crud(client):
    create_resp = client.post("/api/v1/patients", json=VALID_PATIENT)
    assert create_resp.status_code == 201
    patient_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/patients/{patient_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["patient_identifier"] == "TEST-001"

    list_resp = client.get("/api/v1/patients")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    missing_resp = client.get("/api/v1/patients/99999")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["error"] == "PATIENT_NOT_FOUND"
