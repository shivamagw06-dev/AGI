"""Structured knowledge extraction from IR documents (not ML training)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


THEME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("business_model", re.compile(r"business\s+model|how\s+we\s+make\s+money", re.I)),
    ("segments", re.compile(r"segment\s+(revenue|performance)|operating\s+segments", re.I)),
    ("products", re.compile(r"\bproducts?\b|\bsolutions?\b", re.I)),
    ("management", re.compile(r"management\s+(discussion|commentary)|ceo\s+comment", re.I)),
    ("capital_allocation", re.compile(r"capital\s+allocation|buyback|dividend\s+policy", re.I)),
    ("strategy", re.compile(r"\bstrategy\b|strategic\s+priorities", re.I)),
    ("competitive_advantages", re.compile(r"competitive\s+advantage|moat|differentiat", re.I)),
    ("risks", re.compile(r"\brisk\s+factors?\b|\bkey\s+risks\b", re.I)),
    ("guidance", re.compile(r"\bguidance\b|outlook|expect\s+to", re.I)),
    ("capex", re.compile(r"\bcapex\b|capital\s+expenditure", re.I)),
    ("debt", re.compile(r"\bdebt\b|leverage|borrowings", re.I)),
    ("margins", re.compile(r"\bmargin\b|EBITDA\s+margin|operating\s+margin", re.I)),
    ("customers", re.compile(r"\bcustomers?\b|client\s+base", re.I)),
    ("geography", re.compile(r"\bgeography\b|geographic\s+mix|north\s+america|europe|india", re.I)),
]


def extract_document_intelligence(
    entity: str,
    doc: dict[str, Any],
    *,
    raw_bytes: bytes | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    """Produce structured knowledge + citations from a document."""
    body = text or ""
    if not body and raw_bytes:
        # Best-effort text from PDF-ish bytes (no heavy PDF lib required)
        try:
            body = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        if len(body) < 200 and isinstance(raw_bytes, (bytes, bytearray)):
            body = " ".join(
                m.decode("ascii", errors="ignore")
                for m in re.findall(rb"[\x20-\x7e]{5,}", raw_bytes[:500_000])
            )

    themes: dict[str, Any] = {}
    citations: list[dict[str, Any]] = []
    for key, pat in THEME_PATTERNS:
        m = pat.search(body[:200_000] if body else "")
        if m:
            start = max(0, m.start() - 80)
            end = min(len(body), m.end() + 160)
            snippet = re.sub(r"\s+", " ", body[start:end]).strip()
            themes[key] = {"present": True, "snippet": snippet[:280]}
            citations.append({"theme": key, "quote": snippet[:200], "doc_url": doc.get("url"), "doc_type": doc.get("doc_type")})

    # Numeric soft extracts
    metrics: dict[str, Any] = {}
    for label, pat in (
        ("revenue_mention", re.compile(r"revenue[^0-9]{0,20}([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", re.I)),
        ("margin_mention", re.compile(r"(?:EBITDA|operating)\s+margin[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)\s*%", re.I)),
        ("capex_mention", re.compile(r"capex[^0-9]{0,20}([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", re.I)),
    ):
        m = pat.search(body or "")
        if m:
            metrics[label] = m.group(1)

    out = {
        "entity": entity.upper(),
        "kind": "document_intelligence",
        "doc_type": doc.get("doc_type"),
        "doc_url": doc.get("url"),
        "themes": themes,
        "metrics": metrics,
        "relationships": [
            {"from": entity.upper(), "to": t, "type": "discusses"} for t in themes.keys()
        ],
        "citations": citations[:40],
        "embeddings_ready": True,
        "confidence": round(min(0.95, 0.35 + 0.05 * len(themes)), 3),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "learning_mode": "structured_extraction_not_ml_training",
    }
    try:
        from continuous_gather_learn import persist as cgl_persist

        # Merge into entity knowledge extract
        prior = cgl_persist.get_knowledge_extract(entity) or {}
        docs_intel = list(prior.get("documents") or [])
        docs_intel.append(out)
        prior = {
            **prior,
            "entity": entity.upper(),
            "documents": docs_intel[-50:],
            "document_themes": sorted({k for d in docs_intel for k in (d.get("themes") or {})}),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        cgl_persist.put_knowledge_extract(entity, prior)
        # Soft embed
        try:
            from continuous_gather_learn.embeddings import embed_knowledge_extract

            embed_knowledge_extract(entity, prior)
        except Exception:
            pass
    except Exception:
        pass
    return out
