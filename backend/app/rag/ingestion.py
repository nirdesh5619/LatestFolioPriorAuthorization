import os

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories import GuidelineRepository
from app.rag.chunker import chunk_section_text, parse_guideline_document
from app.rag.embeddings import embed_texts
from app.rag.faiss_store import FaissStore

logger = get_logger(__name__)


def _condition_from_filename(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    return stem.replace("_guideline", "").replace("_", " ").strip()


def _guideline_id_from_filename(filename: str) -> str:
    stem = os.path.splitext(filename)[0].upper().replace("_", "-")
    return f"{stem}-DEMO"


def ingest_guidelines(
    db: Session,
    guidelines_dir: str | None = None,
    store: FaissStore | None = None,
) -> dict:
    settings = get_settings()
    guidelines_dir = guidelines_dir or settings.guidelines_dir
    store = store or FaissStore()

    repo = GuidelineRepository(db)

    texts_for_embedding: list[str] = []
    metadata_records: list[dict] = []

    files = sorted(f for f in os.listdir(guidelines_dir) if f.endswith(".txt"))
    if not files:
        logger.warning("No guideline documents found in %s", guidelines_dir)

    for filename in files:
        path = os.path.join(guidelines_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        condition = _condition_from_filename(filename)
        parsed = parse_guideline_document(raw_text, condition=condition)
        guideline_id = _guideline_id_from_filename(filename)

        existing = repo.get_by_guideline_id(guideline_id)
        if existing is None:
            guideline_row = repo.create(
                {
                    "guideline_id": guideline_id,
                    "title": parsed.title,
                    "organization": parsed.organization,
                    "version": parsed.version,
                    "publication_date": None,
                    "condition": parsed.condition,
                    "source_file": filename,
                }
            )
        else:
            guideline_row = existing

        chunk_counter = 0
        for section_chunk in parsed.chunks:
            sub_chunks = chunk_section_text(section_chunk.text)
            for sub_text in sub_chunks:
                chunk_counter += 1
                chunk_id = f"{guideline_id}-{chunk_counter:03d}"

                repo.create_chunk(
                    {
                        "guideline_id": guideline_row.id,
                        "chunk_id": chunk_id,
                        "text": sub_text,
                        "section": section_chunk.section,
                        "page": section_chunk.page,
                        "metadata_json": "{}",
                    }
                )

                texts_for_embedding.append(sub_text)
                metadata_records.append(
                    {
                        "chunk_id": chunk_id,
                        "guideline_id": guideline_id,
                        "guideline_title": parsed.title,
                        "section": section_chunk.section,
                        "page": section_chunk.page,
                        "source": filename,
                        "condition": parsed.condition,
                        "text": sub_text,
                    }
                )

    if texts_for_embedding:
        vectors = embed_texts(texts_for_embedding)
        store.build(vectors, metadata_records)
        logger.info("Ingested %d guideline chunks from %d files", len(texts_for_embedding), len(files))

    return {
        "files_processed": len(files),
        "chunks_indexed": len(texts_for_embedding),
    }
