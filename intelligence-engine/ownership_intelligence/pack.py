"""Ownership Pack v2 builder — master timeline + XBRL detail + QoQ + intelligence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ownership_intelligence.dates import fiscal_quarter_label
from ownership_intelligence.intelligence import build_intelligence_layer
from ownership_intelligence.master import quarter_timeline
from ownership_intelligence.schema import (
    ENGINE_CODE,
    FRESHNESS_SLA_DAYS,
    MIN_HISTORY_QUARTERS,
    OWNERSHIP_FIELDS,
    VERSION,
)
from ownership_intelligence.trends import build_qoq_series, qoq_deltas
from ownership_intelligence.xbrl import enrich_quarter_with_xbrl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _age_days(iso_date: str | None) -> float | None:
    if not iso_date:
        return None
    try:
        dt = datetime.strptime(iso_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
    except ValueError:
        return None


def _ownership_slice(row: dict[str, Any]) -> dict[str, Any]:
    slice_: dict[str, Any] = {k: row.get(k) for k in OWNERSHIP_FIELDS}
    slice_["promoter_pledge"] = row.get("promoter_pledge")
    slice_["promoter_pledge_pct"] = row.get("promoter_pledge_pct")
    slice_["period_end"] = row.get("period_end")
    slice_["quarter_label"] = row.get("quarter_label") or fiscal_quarter_label(row.get("period_end"))
    slice_["filing_date"] = row.get("filing_date")
    slice_["source"] = row.get("detail_source") or row.get("source") or "nse"
    slice_["xbrl_url"] = row.get("xbrl_url")
    return slice_


def build_ownership_pack(
    symbol: str,
    *,
    force: bool = False,
    xbrl_quarters: int = 4,
    opener=None,
    injected_master: list[dict[str, Any]] | None = None,
    injected_xbrl_by_period: dict[str, bytes | str] | None = None,
    skip_xbrl: bool = False,
) -> dict[str, Any]:
    """Full Ownership Pack v2 for one ticker."""
    key = (symbol or "").upper()
    t0 = datetime.now(timezone.utc)
    timeline = quarter_timeline(key, opener=opener, injected=injected_master)
    quarters = list(timeline.get("quarters") or [])
    errors: list[str] = []
    if timeline.get("error"):
        errors.append(str(timeline["error"]))

    # Enrich newest N quarters with XBRL detail
    enriched: list[dict[str, Any]] = []
    xbrl_map = injected_xbrl_by_period or {}
    for i, q in enumerate(quarters):
        if skip_xbrl or i >= max(0, int(xbrl_quarters)):
            enriched.append(dict(q))
            continue
        period = q.get("period_end") or ""
        injected = xbrl_map.get(period) or xbrl_map.get(str(q.get("period_raw") or ""))
        try:
            enriched.append(
                enrich_quarter_with_xbrl(q, opener=opener, injected_xbrl=injected)
            )
        except Exception as exc:  # noqa: BLE001
            row = dict(q)
            row["xbrl_error"] = f"{type(exc).__name__}:{str(exc)[:120]}"
            enriched.append(row)
            errors.append(f"xbrl:{period}:{exc}")

    current = enriched[0] if enriched else None
    previous = enriched[1] if len(enriched) > 1 else None
    qoq = qoq_deltas(current, previous) if current else {"available": False, "deltas_pp": {}}
    qoq_series = build_qoq_series(enriched, limit=8)

    age = _age_days((current or {}).get("period_end"))
    stale = age is not None and age > float(FRESHNESS_SLA_DAYS)
    freshness = {
        "as_of_quarter": (current or {}).get("period_end"),
        "quarter_label": (current or {}).get("quarter_label"),
        "filing_date": (current or {}).get("filing_date"),
        "age_days": round(age, 1) if age is not None else None,
        "sla_days": FRESHNESS_SLA_DAYS,
        "stale": stale,
        "within_sla": (age is not None and not stale),
    }

    ownership = _ownership_slice(current) if current else {k: None for k in OWNERSHIP_FIELDS}
    history = [_ownership_slice(r) for r in enriched]
    intel = (
        build_intelligence_layer(current or {}, qoq=qoq, history=enriched, freshness=freshness)
        if current
        else {
            "ownership_quality": 0.0,
            "observations": [],
            "reasoning": "Ownership pack unavailable",
            "not_a_recommendation": True,
        }
    )

    core_ok = bool(
        current
        and (
            current.get("promoter") is not None
            or current.get("fii") is not None
            or current.get("public") is not None
        )
    )
    detail_ok = bool(
        current
        and current.get("fii") is not None
        and current.get("dii") is not None
        and current.get("mutual_funds") is not None
    )

    latency_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    evidence = []
    if current:
        evidence.append(
            f"NSE shareholding as of {current.get('period_end')} "
            f"(promoter={current.get('promoter')}, fii={current.get('fii')}, "
            f"dii={current.get('dii')}, mf={current.get('mutual_funds')})"
        )
        if current.get("xbrl_url"):
            evidence.append(f"XBRL source: {current.get('xbrl_url')}")
    for o in (intel.get("observations") or [])[:4]:
        evidence.append(o)

    lineage = [
        {"source": "nse_master", "ref": key, "quarters": len(quarters)},
    ]
    if current and current.get("xbrl_url"):
        lineage.append({"source": "nse_xbrl", "ref": current.get("xbrl_url")})

    return {
        "ok": core_ok,
        "detail_ok": detail_ok,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": key,
        "ownership": ownership,
        # Flat keys for readiness_gate compatibility (promoter / fii present)
        "promoter": ownership.get("promoter"),
        "promoter_group": ownership.get("promoter_group"),
        "public": ownership.get("public"),
        "fii": ownership.get("fii"),
        "dii": ownership.get("dii"),
        "mutual_funds": ownership.get("mutual_funds"),
        "insurance": ownership.get("insurance"),
        "banks": ownership.get("banks"),
        "pension": ownership.get("pension"),
        "aif": ownership.get("aif"),
        "government": ownership.get("government"),
        "retail": ownership.get("retail"),
        "others": ownership.get("others"),
        "employee_trusts": ownership.get("employee_trusts"),
        "promoter_pledge": ownership.get("promoter_pledge"),
        "promoter_pledge_pct": ownership.get("promoter_pledge_pct"),
        "as_of_quarter": ownership.get("period_end"),
        "quarter_label": ownership.get("quarter_label"),
        "filing_date": ownership.get("filing_date"),
        "quarter_history": history,
        "history_count": len(history),
        "history_meets_minimum": len(history) >= min(MIN_HISTORY_QUARTERS, 1),
        "qoq": qoq,
        "qoq_series": qoq_series,
        "intelligence": intel,
        "score": intel.get("ownership_quality"),
        "evidence": evidence,
        "confidence": intel.get("ownership_confidence") or 0.0,
        "freshness": freshness,
        "lineage": lineage,
        "source": {
            "master": "nse_corporate_share_holdings_master",
            "detail": "nse_shp_xbrl",
            "mode": timeline.get("mode"),
        },
        "raw_current": {
            k: current.get(k)
            for k in (
                "period_raw",
                "record_id",
                "isin",
                "name",
                "xbrl_url",
                "xbrl_ok",
                "xbrl_error",
                "remarks",
            )
        }
        if current
        else {},
        "errors": errors,
        "force": bool(force),
        "skip_xbrl": bool(skip_xbrl),
        "latency_ms": latency_ms,
        "generated_at": _now(),
        "missing": not core_ok,
        "fabricated": False,
    }
