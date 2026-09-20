"""Ingest synthetic guideline documents into SQLite and build the FAISS index.

Usage:
    python scripts/ingest_guidelines.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.database import SessionLocal, init_db
from app.rag.ingestion import ingest_guidelines

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    settings = get_settings()
    init_db()

    db = SessionLocal()
    try:
        result = ingest_guidelines(db, settings.guidelines_dir)
        logger.info("Ingestion complete: %s", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
