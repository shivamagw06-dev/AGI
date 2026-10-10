"""Filing timeline — append-only institutional memory events."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import TimelineEvent


def build_timeline(
    docs: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for f in facts:
        by_doc.setdefault(f.get("doc_id") or "", []).append(f)

    events: list[TimelineEvent] = []
    for doc in sorted(docs, key=lambda d: d.get("as_of") or ""):
        doc_id = doc.get("doc_id") or ""
        flist = by_doc.get(doc_id) or []
        metrics = sorted({f["metric"] for f in flist if f.get("category") == "financial"})
        mgmt = next((f["value"] for f in flist if f.get("category") == "management"), "")
        risks = [str(f["metric"]) for f in flist if f.get("category") == "risk"]
        guidance = [str(f["value"]) for f in flist if f.get("metric") == "Guidance_Status"]
        cap = [str(f["metric"]) for f in flist if f.get("category") == "capital"]
        summary = (
            f"{doc.get('company') or doc.get('ticker')} {doc.get('doc_type')} "
            f"{doc.get('period')}: {doc.get('title')}"
        )
        events.append(
            TimelineEvent(
                event_id=f"tl:{doc_id}",
                ticker=str(doc.get("ticker") or ""),
                doc_id=doc_id,
                as_of=str(doc.get("as_of") or ""),
                period=str(doc.get("period") or ""),
                summary=summary,
                metrics=metrics,
                management_view=str(mgmt)[:240],
                risks=risks,
                guidance=guidance,
                capital_allocation=cap,
                evidence_links=[doc.get("url") or ""] if doc.get("url") else [doc_id],
            )
        )
    return [e.to_dict() for e in events]
