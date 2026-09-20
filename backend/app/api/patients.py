from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.patient import PatientCreate, PatientRead
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientRead, status_code=201)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)) -> PatientRead:
    return PatientService(db).create_patient(payload)


@router.get("", response_model=list[PatientRead])
def list_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[PatientRead]:
    return PatientService(db).list_patients(skip=skip, limit=limit)


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, db: Session = Depends(get_db)) -> PatientRead:
    return PatientService(db).get_patient(patient_id)
