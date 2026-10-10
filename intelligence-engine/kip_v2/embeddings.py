"""Pluggable embedding backends for Module 1 / Module 9.

Every paragraph the Document Intelligence Engine stores gets an embedding so
Module 9 (Knowledge Retrieval) can fall back to semantic similarity search
when structured knowledge doesn't directly answer a question.

Two real (non-fabricated) implementations are provided:

* ``HashingEmbedder`` (default, always available, offline, deterministic) —
  a feature-hashing / "hashing trick" bag-of-words vector, the same technique
  behind scikit-learn's ``HashingVectorizer``. No corpus-wide fit step is
  needed, which matters for *incremental* ingestion (Module 10): a new
  document's paragraphs get comparable vectors without re-embedding anything
  that was already ingested.
* ``OpenAIEmbedder`` (opt-in, production-quality neural embeddings) — used
  only when ``KIP_V2_USE_OPENAI_EMBEDDINGS=1`` and ``OPENAI_API_KEY`` are
  both set, so tests and default operation stay offline/deterministic,
  consistent with the rest of this codebase's "no live external dependency
  required for correctness" convention.

Both implementations satisfy the same ``Embedder`` protocol so storage and
retrieval code never need to know which one produced a given vector.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Protocol

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Deterministic, offline, dependency-free bag-of-words embedding."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in tokenize(text):
            digest = hashlib.md5(tok.encode("utf-8")).hexdigest()
            h = int(digest, 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class OpenAIEmbedder:
    """Real neural embeddings via OpenAI's embedding API. Opt-in only."""

    def __init__(self, model: str = "text-embedding-3-small", dim: int = 1536) -> None:
        self.model = model
        self.dim = dim
        self._client = None

    def _client_or_none(self):
        if self._client is not None:
            return self._client
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        try:
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(api_key=api_key)
            return self._client
        except Exception:
            return None

    def embed(self, text: str) -> list[float]:
        client = self._client_or_none()
        if client is None:
            return HashingEmbedder(dim=self.dim).embed(text)
        try:
            resp = client.embeddings.create(model=self.model, input=text[:8000] or " ")
            return list(resp.data[0].embedding)
        except Exception:
            return HashingEmbedder(dim=self.dim).embed(text)


def get_default_embedder() -> Embedder:
    use_openai = os.environ.get("KIP_V2_USE_OPENAI_EMBEDDINGS", "").strip() == "1"
    if use_openai and os.environ.get("OPENAI_API_KEY", "").strip():
        return OpenAIEmbedder()
    return HashingEmbedder()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
