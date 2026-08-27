"""Evidence lineage — every score must answer: where did this come from?"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(payload: Any) -> str:
    try:
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    except Exception:
        raw = str(payload).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _period_guess(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None
    for k in ("period", "period_end", "latest_period", "fiscal_period", "quarter", "as_of"):
        if obj.get(k):
            return str(obj.get(k))[:32]
    recs = obj.get("records") or obj.get("items") or []
    if isinstance(recs, list) and recs:
        last = recs[-1] if isinstance(recs[-1], dict) else {}
        for k in ("period", "period_end", "as_of"):
            if last.get(k):
                return str(last.get(k))[:32]
    return None


def _source_guess(obj: Any, *, default: str = "institutional_store") -> str:
    if not isinstance(obj, dict):
        return default
    for k in ("source", "source_id", "provider", "collector"):
        if obj.get(k):
            return str(obj.get(k))[:80]
    recs = obj.get("records") or []
    if isinstance(recs, list) and recs and isinstance(recs[-1], dict) and recs[-1].get("source"):
        return str(recs[-1].get("source"))[:80]
    return default


def _ingested_guess(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None
    for k in ("ingested_at", "updated_at", "generated_at", "available_from", "as_of"):
        if obj.get(k):
            return str(obj.get(k))[:40]
    return None


def _collector_guess(obj: Any, *, fallback: str) -> str:
    if isinstance(obj, dict):
        for k in ("collector", "collector_id", "pipeline", "hd_version"):
            if obj.get(k):
                return str(obj.get(k))[:80]
    return fallback


def _lineage_row(
    *,
    dimension: str,
    status: str,
    source: str | None,
    period: str | None,
    ingested: str | None,
    verified_hash: str | None,
    collector: str | None,
    confidence_pct: float,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "status": status,
        "source": source,
        "period": period,
        "ingested_at": ingested,
        "verified": f"SHA-256: {(verified_hash or '')[:12]}..." if verified_hash else None,
        "evidence_hash": verified_hash,
        "collector": collector,
        "confidence_pct": round(float(confidence_pct), 1),
        "detail": detail,
        "lineage_complete": bool(source and (period or ingested) and verified_hash),
    }


def build_evidence_lineage(
    *,
    readiness_gate: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Per-dimension lineage board for institutional auditability."""
    gate = readiness_gate if isinstance(readiness_gate, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cid = cid if isinstance(cid, dict) else {}
    leo = live_evidence if isinstance(live_evidence, dict) else {}
    ve = valuation_pack if isinstance(valuation_pack, dict) else {}
    cards = {c.get("key"): c for c in (gate.get("diagnostic_cards") or gate.get("checklist") or []) if isinstance(c, dict)}
    coverage = gate.get("coverage") or {}

    fin = ca.get("financial_intelligence") or {}
    val = ca.get("valuation_intelligence") or {}
    bq = ca.get("business_quality") or {}
    sh = cid.get("shareholding") or cid.get("ownership") or ca.get("shareholding") or {}
    filings = cid.get("filings") or leo.get("evidence_objects") or []

    def status_for(key: str, cov: float) -> str:
        card = cards.get(key) or {}
        if card.get("present"):
            return "Complete"
        if card.get("status") == "outdated":
            return "Outdated"
        if card.get("status") in {"partial", "thin"}:
            return "Partial"
        if cov >= 60:
            return "Partial"
        return "Missing"

    rows = [
        _lineage_row(
            dimension="Financial Statements",
            status=status_for("financials", float(coverage.get("financials") or 0)),
            source=_source_guess(fin, default="financial_connector"),
            period=_period_guess(fin) or cards.get("financials", {}).get("latest_available"),
            ingested=_ingested_guess(fin) or cards.get("financials", {}).get("latest_available"),
            verified_hash=_sha256(fin) if fin else None,
            collector=_collector_guess(fin, fallback="Historical Collector / financial connector"),
            confidence_pct=float(coverage.get("financials") or 0),
        ),
        _lineage_row(
            dimension="Ownership / Shareholding",
            status=status_for("ownership", float(coverage.get("ownership") or 0)),
            source=_source_guess(sh, default="shareholding_connector"),
            period=_period_guess(sh) or cards.get("ownership", {}).get("latest_available"),
            ingested=_ingested_guess(sh) or cards.get("ownership", {}).get("latest_available"),
            verified_hash=_sha256(sh) if sh else None,
            collector=_collector_guess(sh, fallback="Shareholding collector"),
            confidence_pct=float(coverage.get("ownership") or 0),
        ),
        _lineage_row(
            dimension="Valuation",
            status=status_for("valuation", float(coverage.get("valuation") or 0)),
            source=_source_guess(val or ve, default="valuation_intelligence"),
            period=_period_guess(val) or _period_guess(ve) or cards.get("valuation", {}).get("latest_available"),
            ingested=_ingested_guess(val) or _ingested_guess(ve),
            verified_hash=_sha256({"val": val, "ve": ve}) if (val or ve) else None,
            collector=_collector_guess(val or ve, fallback="Valuation intelligence"),
            confidence_pct=float(coverage.get("valuation") or 0),
        ),
        _lineage_row(
            dimension="Business Intelligence",
            status="Complete" if bq.get("business_quality_score") is not None else "Partial",
            source=_source_guess(bq, default="company_analysis"),
            period=_ingested_guess(ca) or _ingested_guess(bq),
            ingested=_ingested_guess(ca) or _ingested_guess(bq),
            verified_hash=_sha256(bq) if bq else None,
            collector="Company Analysis / Business Quality",
            confidence_pct=float(bq.get("coverage_pct") or (90 if bq.get("business_quality_score") is not None else 40)),
        ),
        _lineage_row(
            dimension="Filings / Earnings",
            status=status_for("filings", float(coverage.get("filings") or 0)),
            source=_source_guess({"records": filings} if isinstance(filings, list) else filings, default="exchange_filing"),
            period=_period_guess({"records": filings} if isinstance(filings, list) else filings),
            ingested=_ingested_guess(leo) or cards.get("filings", {}).get("latest_available"),
            verified_hash=_sha256(filings) if filings else None,
            collector=_collector_guess(leo, fallback="LEO / exchange ingest"),
            confidence_pct=float(coverage.get("filings") or 0),
        ),
        _lineage_row(
            dimension="Macro",
            status=status_for("macro", float(coverage.get("macro") or 0)),
            source="macro_intelligence",
            period=_ingested_guess(leo.get("macro") if isinstance(leo.get("macro"), dict) else None),
            ingested=_ingested_guess(leo),
            verified_hash=_sha256({"macro_cov": coverage.get("macro")}),
            collector="Macro / sector intelligence",
            confidence_pct=float(coverage.get("macro") or 0),
        ),
        _lineage_row(
            dimension="Technical",
            status=status_for("technicals", float(coverage.get("technicals") or 0)),
            source=_source_guess(leo.get("quote") or leo.get("market") or {}, default="market_data"),
            period=_ingested_guess(leo.get("quote") if isinstance(leo.get("quote"), dict) else None),
            ingested=_ingested_guess(leo.get("quote") if isinstance(leo.get("quote"), dict) else leo),
            verified_hash=_sha256(leo.get("quote") or leo.get("market") or {}) if leo else None,
            collector="Market data / technical overlay",
            confidence_pct=float(coverage.get("technicals") or 0),
        ),
        _lineage_row(
            dimension="News / Catalysts",
            status=status_for("research", float(coverage.get("news") or 0))
            if float(coverage.get("news") or 0) < 70
            else "Complete",
            source="news_intelligence",
            period=_ingested_guess(leo),
            ingested=_ingested_guess(leo),
            verified_hash=_sha256(leo.get("news") or leo.get("evidence_objects") or []) if leo else None,
            collector="News / catalyst ingest",
            confidence_pct=float(coverage.get("news") or 0),
        ),
    ]

    return {
        "generated_at": _now(),
        "rows": rows,
        "complete_count": sum(1 for r in rows if r.get("status") == "Complete"),
        "lineage_complete_count": sum(1 for r in rows if r.get("lineage_complete")),
        "note": "Lineage answers where each evidence pillar came from — source, period, ingest time, hash, collector.",
    }
