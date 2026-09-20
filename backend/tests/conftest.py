import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_DATA_DIR = ROOT / "tests" / "_test_data"
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

TEST_DB_PATH = TEST_DATA_DIR / "test_clinical_guidelines.db"
TEST_FAISS_INDEX = TEST_DATA_DIR / "index.faiss"
TEST_FAISS_META = TEST_DATA_DIR / "metadata.json"

for path in (TEST_DB_PATH, TEST_FAISS_INDEX, TEST_FAISS_META):
    if path.exists():
        path.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["FAISS_INDEX_PATH"] = str(TEST_FAISS_INDEX)
os.environ["FAISS_METADATA_PATH"] = str(TEST_FAISS_META)

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.rag.embeddings as embeddings_module  # noqa: E402
import app.rag.ingestion as ingestion_module  # noqa: E402
import app.rag.retriever as retriever_module  # noqa: E402
from tests.fake_embeddings import (  # noqa: E402
    fake_embed_query,
    fake_embed_texts,
    fake_get_embedding_dimension,
)

# Replace the real (network-dependent) embedding model with a deterministic
# hashed bag-of-words vectorizer everywhere it is used, before any test runs
# or the FastAPI app starts up.
embeddings_module.embed_texts = fake_embed_texts
embeddings_module.embed_query = fake_embed_query
embeddings_module.get_embedding_dimension = fake_get_embedding_dimension
ingestion_module.embed_texts = fake_embed_texts
retriever_module.embed_query = fake_embed_query

from app.db.database import Base  # noqa: E402


@pytest.fixture()
def db_session():
    """An isolated in-memory SQLite session, independent of the app's global engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """A TestClient wired to the isolated db_session fixture instead of the real DB file."""
    from fastapi.testclient import TestClient

    from app.db.database import get_db
    from app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
