"""Deterministic structured embeddings from knowledge extracts — not ML training."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Any

from continuous_gather_learn import persist as cgl_persist


def _stable_vector(text: str, *, dims: int = 32) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # Expand digest
    raw = digest
    while len(raw) < dims * 4:
        raw += hashlib.sha256(raw).digest()
    vals = []
    for i in range(dims):
        chunk = raw[i * 4 : i * 4 + 4]
        (n,) = struct.unpack(">I", chunk)
        # Map to [-1, 1]
        vals.append((n / 0xFFFFFFFF) * 2.0 - 1.0)
    # L2 normalise
    norm = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [round(v / norm, 6) for v in vals]


def embed_knowledge_extract(entity: str, extract: dict[str, Any] | None = None) -> dict[str, Any]:
    extract = extract or cgl_persist.get_knowledge_extract(entity) or {}
    metrics = extract.get("metrics") or {}
    themes = extract.get("themes") or []
    risks = extract.get("risks") or []
    blob = "|".join(
        [
            str(entity).upper(),
            str(sorted(metrics.items())),
            str(themes)[:400],
            str(risks)[:400],
        ]
    )
    vector = _stable_vector(blob)
    payload = {
        "entity": str(entity).upper(),
        "kind": "structured_knowledge_embedding",
        "dims": len(vector),
        "vector": vector,
        "source": "knowledge_extract",
        "learning_mode": "deterministic_embedding_not_ml_training",
        "metrics_keys": sorted(list(metrics.keys())[:40]),
    }
    cgl_persist.put_embedding(entity, payload)
    return payload
