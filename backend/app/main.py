from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import guidelines, health, observability, orchestration, patients, review, search
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.db.database import SessionLocal, init_db
from app.db.repositories import GuidelineRepository, PatientRepository
from app.rag.faiss_store import get_faiss_store
from app.rag.ingestion import ingest_guidelines

configure_logging()
logger = get_logger(__name__)


def _bootstrap() -> None:
    """Idempotent startup: create DB, build FAISS index if missing, seed patients if empty."""
    settings = get_settings()
    init_db()

    db = SessionLocal()
    try:
        guideline_repo = GuidelineRepository(db)
        store = get_faiss_store()

        if not store.exists() or guideline_repo.count_chunks() == 0:
            logger.info("FAISS index or guideline chunks missing - running guideline ingestion.")
            ingest_guidelines(db, settings.guidelines_dir, store)
        else:
            logger.info("FAISS index found with %d guideline chunks - skipping ingestion.", store.size)

        patient_repo = PatientRepository(db)
        if patient_repo.count() == 0:
            logger.info("No patients found - seeding synthetic demo patients.")
            from scripts.seed_database import seed_patients

            seed_patients(db, settings.patients_seed_file)
        else:
            logger.info("Patients already present - skipping seed.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _bootstrap()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "A synthetic, demonstration-only prior-authorization decision-support platform that "
        "orchestrates multiple agents against a local RAG index of demo payer policy criteria. "
        "Not for clinical or coverage-determination use."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


app.include_router(health.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")
app.include_router(guidelines.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(orchestration.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(observability.router, prefix="/api/v1")
