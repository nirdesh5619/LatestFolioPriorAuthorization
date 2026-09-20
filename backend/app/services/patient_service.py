from sqlalchemy.orm import Session

from app.core.exceptions import InvalidPayloadError, PatientNotFoundError
from app.db.repositories import PatientRepository
from app.schemas.patient import PatientCreate, PatientRead


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PatientRepository(db)

    def create_patient(self, payload: PatientCreate) -> PatientRead:
        if self.repo.get_by_identifier(payload.patient_identifier):
            raise InvalidPayloadError(
                f"A patient with identifier '{payload.patient_identifier}' already exists."
            )
        row = self.repo.create(payload.model_dump())
        return PatientRead.from_orm_row(row)

    def get_patient(self, patient_id: int) -> PatientRead:
        row = self.repo.get(patient_id)
        if row is None:
            raise PatientNotFoundError(f"Patient with id {patient_id} was not found.")
        return PatientRead.from_orm_row(row)

    def list_patients(self, skip: int = 0, limit: int = 100) -> list[PatientRead]:
        rows = self.repo.list(skip=skip, limit=limit)
        return [PatientRead.from_orm_row(row) for row in rows]
