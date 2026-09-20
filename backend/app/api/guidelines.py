from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories import GuidelineRepository

router = APIRouter(prefix="/guidelines", tags=["guidelines"])


@router.get("")
def list_guidelines(db: Session = Depends(get_db)) -> list[dict]:
    guidelines = GuidelineRepository(db).list()
    return [
        {
            "guideline_id": g.guideline_id,
            "title": g.title,
            "organization": g.organization,
            "version": g.version,
            "condition": g.condition,
            "source_file": g.source_file,
        }
        for g in guidelines
    ]
