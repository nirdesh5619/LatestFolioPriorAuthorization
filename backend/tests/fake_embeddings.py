"""Deterministic, dependency-free stand-in for the real sentence-transformers model.

Tests must not require network access to download a model, so we use a hashed
bag-of-words vectorizer that still produces meaningful lexical-overlap similarity
for the purposes of exercising retrieval and orchestration logic.
"""

import hashlib
import re

import numpy as np

FAKE_DIM = 4096


def _fake_vector(text: str) -> np.ndarray:
    vec = np.zeros(FAKE_DIM, dtype="float32")
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % FAKE_DIM
        vec[idx] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec.astype("float32")


def fake_embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, FAKE_DIM), dtype="float32")
    return np.stack([_fake_vector(t) for t in texts]).astype("float32")


def fake_embed_query(query: str) -> np.ndarray:
    return _fake_vector(query)


def fake_get_embedding_dimension() -> int:
    return FAKE_DIM
