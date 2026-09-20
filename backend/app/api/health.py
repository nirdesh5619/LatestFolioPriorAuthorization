from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.rag.faiss_store import get_faiss_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    db_status = "UP"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "DOWN"

    store = get_faiss_store()
    vector_status = "UP" if store.exists() else "DOWN"

    overall = "UP" if db_status == "UP" and vector_status == "UP" else "DEGRADED"

    return {
        "status": overall,
        "database": db_status,
        "vector_store": vector_status,
    }
