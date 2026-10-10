"""Evidence Explorer — searchable institutional evidence across Top-20 packs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def search_evidence(
    *,
    q: str = "",
    ticker: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    from institutional_coverage_factory.universe import top20_tickers

    tickers = [ticker.upper()] if ticker else top20_tickers()
    query = str(q or "").strip().lower()
    dtype = (document_type or "").strip().lower() or None
    rows: List[Dict[str, Any]] = []

    for t in tickers:
        try:
            from institutional_evidence.research_pack.builder import (
                build_institutional_research_pack,
            )

            pack = build_institutional_research_pack(t)
        except Exception:
            continue
        items = ((pack.get("evidence") or {}).get("registry") or {}).get("items") or []
        for it in items:
            dt = str(it.get("document_type") or "")
            src = str(it.get("source") or "")
            did = str(it.get("document_id") or "")
            blob = f"{t} {dt} {src} {did}".lower()
            if dtype and dtype not in dt.lower():
                continue
            if query and query not in blob:
                continue
            rows.append(
                {
                    "ticker": t,
                    "document_id": did,
                    "document_type": dt,
                    "source": src,
                    "status": it.get("status"),
                    "hash": (it.get("hash") or it.get("checksum") or "")[:16] or None,
                    "published_at": it.get("published_at"),
                    "entity_id": it.get("entity_id"),
                    "knowledge_version": pack.get("knowledge_version"),
                    "claim_safe": pack.get("claim_safe"),
                    "research_ready": pack.get("research_ready"),
                }
            )
            if len(rows) >= max(1, min(int(limit), 200)):
                break
        if len(rows) >= max(1, min(int(limit), 200)):
            break

    return {
        "ok": True,
        "count": len(rows),
        "query": q,
        "ticker": ticker,
        "document_type": document_type,
        "items": rows,
    }


def evidence_detail(ticker: str, document_id: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    did = str(document_id or "").strip()
    found = search_evidence(ticker=t, limit=200)
    hit = next((i for i in found.get("items") or [] if i.get("document_id") == did), None)
    graph = None
    try:
        from institutional_evidence.production import get_evidence_graph

        graph = get_evidence_graph(t)
    except Exception as exc:
        graph = {"error": str(exc)[:160]}
    return {
        "ok": True,
        "ticker": t,
        "document_id": did,
        "evidence": hit,
        "lineage": {
            "company": t,
            "document": did,
            "knowledge_graph": graph,
            "note": "Trace: Company → Evidence → Claims → Research Pack → Portfolio",
        },
    }


def global_search(q: str, *, limit: int = 30) -> Dict[str, Any]:
    """Cross-scope search: companies, evidence, versions, packs."""
    query = str(q or "").strip()
    if not query:
        return {"ok": True, "query": "", "results": {"companies": [], "evidence": [], "knowledge_versions": [], "research_packs": []}}

    from institutional_evidence.schema import PHASE1_TOP20

    ql = query.lower()
    companies = [
        {"ticker": r["ticker"], "company": r["company"], "sector": r.get("sector")}
        for r in PHASE1_TOP20
        if ql in r["ticker"].lower() or ql in r["company"].lower()
    ][:limit]

    evidence = search_evidence(q=query, limit=limit).get("items") or []

    versions = []
    try:
        from institutional_evidence.integration.versioning.snapshots import list_snapshots

        snaps = list_snapshots(limit=20).get("snapshots") or []
        versions = [
            s
            for s in snaps
            if ql in str(s.get("knowledge_version") or "").lower()
            or ql in str(s.get("run_id") or "").lower()
        ][:limit]
    except Exception:
        pass

    packs = []
    for c in companies[:10]:
        packs.append(
            {
                "ticker": c["ticker"],
                "type": "research_pack",
                "href": f"/v1/iep/pack/{c['ticker']}",
            }
        )

    return {
        "ok": True,
        "query": query,
        "results": {
            "companies": companies,
            "evidence": evidence,
            "knowledge_versions": versions,
            "research_packs": packs,
            "documents": evidence,
            "claims": [],
        },
    }
