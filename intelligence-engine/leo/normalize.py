"""Normalise raw fetch bundles into canonical Evidence Objects (never reason on raw APIs)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from leo.schema import RANK_WEIGHTS


def _eid(*parts: str) -> str:
    raw = "|".join(str(p) for p in parts)
    return "leo_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def normalize_bundles(
    bundles: list[dict[str, Any]],
    *,
    ticker: str | None = None,
    plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Convert fetch bundles → canonical evidence objects."""
    now = datetime.now(timezone.utc).isoformat()
    objects: list[dict[str, Any]] = []
    seen: set[str] = set()

    for b in bundles or []:
        etype = b.get("evidence_type") or "news"
        source_id = b.get("source_id") or "unknown"
        title = b.get("title") or etype
        facts = b.get("facts") or []
        if not facts:
            facts = [{"field": "summary", "value_text": title, "confidence": 0.55}]

        for fact in facts:
            field = str(fact.get("field") or "fact")
            value_text = str(fact.get("value_text") or fact.get("value") or "")[:800]
            if not value_text.strip():
                continue
            eid = _eid(source_id, etype, ticker or "", field, value_text[:80])
            if eid in seen:
                continue
            seen.add(eid)
            conf = float(fact.get("confidence") or 0.65)
            # Slight boost for regulatory / company filings
            if source_id in {"nse", "bse", "company_ir"}:
                conf = min(0.92, conf + 0.08)
            objects.append(
                {
                    "evidence_id": eid,
                    "leo_version": "leo-v1.0.0",
                    "evidence_type": etype,
                    "fact_key": field,
                    "value_text": value_text,
                    "value": fact.get("value"),
                    "entity": ticker,
                    "company_symbol": ticker or "",
                    "source_id": source_id,
                    "source_name": source_id.upper(),
                    "title": title,
                    "url": b.get("url") or "",
                    "published": b.get("published") or now,
                    "extracted_facts": facts[:20],
                    "confidence": conf,
                    "verification_status": "unverified",
                    "rank_weight": float(RANK_WEIGHTS.get(etype, 2.5)),
                    "provenance": {
                        "source_id": source_id,
                        "connector": source_id,
                        "url": b.get("url") or "",
                        "fetched_at": now,
                        "orchestrator": "LEO",
                    },
                    "metadata": {
                        "kind": b.get("kind"),
                        "raw_keys": list((b.get("raw") or {}).keys())[:12] if isinstance(b.get("raw"), dict) else [],
                    },
                    "version": 1,
                    "created_at": now,
                }
            )

        # Also emit a document-level evidence object for filings
        if b.get("kind") in {"document", "fundamentals"} or etype in {
            "annual_report",
            "quarterly_results",
            "investor_presentation",
            "earnings_transcript",
        }:
            did = _eid("doc", source_id, etype, ticker or "", title)
            if did not in seen:
                seen.add(did)
                objects.append(
                    {
                        "evidence_id": did,
                        "leo_version": "leo-v1.0.0",
                        "evidence_type": etype,
                        "fact_key": f"document:{etype}",
                        "value_text": title,
                        "value": title,
                        "entity": ticker,
                        "company_symbol": ticker or "",
                        "source_id": source_id,
                        "source_name": source_id.upper(),
                        "title": title,
                        "url": b.get("url") or "",
                        "published": b.get("published") or now,
                        "extracted_facts": facts[:20],
                        "confidence": 0.75 if source_id in {"nse", "bse", "company_ir"} else 0.6,
                        "verification_status": "unverified",
                        "rank_weight": float(RANK_WEIGHTS.get(etype, 2.5)),
                        "provenance": {
                            "source_id": source_id,
                            "connector": source_id,
                            "url": b.get("url") or "",
                            "fetched_at": now,
                            "orchestrator": "LEO",
                            "document": True,
                        },
                        "metadata": {"kind": "document_object"},
                        "version": 1,
                        "created_at": now,
                    }
                )

    return objects
