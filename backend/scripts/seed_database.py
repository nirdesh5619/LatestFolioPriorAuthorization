"""Seed the database with synthetic demo patients.

Usage:
    python scripts/seed_database.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.database import SessionLocal, init_db
from app.db.repositories import PatientRepository

logger = get_logger(__name__)


def seed_patients(db: Session, seed_file: str) -> int:
    repo = PatientRepository(db)

    with open(seed_file, "r", encoding="utf-8") as f:
        patients = json.load(f)

    created = 0
    for patient_data in patients:
        if repo.get_by_identifier(patient_data["patient_identifier"]) is not None:
            continue
        repo.create(patient_data)
        created += 1

    logger.info("Seeded %d new synthetic patients (of %d total in seed file).", created, len(patients))
    return created


def main() -> None:
    configure_logging()
    settings = get_settings()
    init_db()

    db = SessionLocal()
    try:
        seed_patients(db, settings.patients_seed_file)
    finally:
        db.close()


if __name__ == "__main__":
    main()
