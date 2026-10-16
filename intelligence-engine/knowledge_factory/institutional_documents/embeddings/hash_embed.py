"""Deterministic local embeddings — no external model dependency.

Produces fixed-dim hash projections for replayable chunk vectors.
Not a neural embedding service; sufficient for institutional search stubs.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import List


DIM = 64
_TOKEN = re.compile(r"[a-z0-9]+", re.I)


def embed_text(text: str, *, dim: int = DIM) -> List[float]:
    vec = [0.0] * dim
    tokens = _TOKEN.findall((text or "").lower())
    if not tokens:
        return vec
    for tok in tokens:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:2], "big") % dim
        sign = 1.0 if h[2] % 2 == 0 else -1.0
        vec[idx] += sign
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]
