"""Module 1 — Historical Intelligence.

Produces validated historical series + analytics for valuation and
quality metrics. Prefer PIL pack series; fall back to institutional seeds.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.institutional_evidence.analytics import analyse_series
from institutional_reasoning.institutional_evidence.provenance import metric_provenance, now_iso
from institutional_reasoning.institutional_evidence.quality import score_metric
from institutional_reasoning.institutional_evidence.seeds import (
    INFY_EXTRA,
    pe_series_for,
    sector_meta,
)

HISTORICAL_VERSION = "historical-intelligence-v1.0.0"

# Metric producers required by Phase 2 Module 1
REQUIRED_PRODUCERS = (
    "PE",
    "EV_EBITDA",
    "PB",
    "ROE",
    "ROIC",
    "Revenue_Growth",
    "EBITDA_Margin",
    "Net_Margin",
    "FCF",
    "Cash_Conversion",
    "Debt",
    "Capex",
)


def _pil_points(entity_id: str, metric: str) -> tuple[dict[str, float] | None, str]:
    """Load points from PIL peer packs when available."""
    try:
        from peer_intelligence.historical.series import history_for
        from peer_intelligence.peer_database.store import normalize_ticker

        t = normalize_ticker(entity_id)
        hist = history_for(t, metric)
        for row in hist.get("series") or []:
            pts = row.get("points") or {}
            if pts:
                return {str(k): float(v) for k, v in pts.items()}, str(
                    row.get("source") or "peer_intelligence"
                )
    except Exception:
        pass
    return None, ""


def _kf_points(entity_id: str, metric: str) -> tuple[dict[str, float] | None, str, str, dict[str, Any]]:
    """Soft feed from Knowledge Factory validated objects (never raw APIs)."""
    try:
        from knowledge_factory.adapter import historical_points_from_kf

        return historical_points_from_kf(entity_id, metric)
    except Exception:
        return None, "", "", {}


def _derived_points(entity_id: str, metric: str) -> tuple[dict[str, float] | None, str, str, dict[str, Any]]:
    """Preferred source: metrics computed from primitives, with audit trail."""
    # Knowledge Factory validated objects first (Track 1 soft feed).
    pts, provider, data_class, meta = _kf_points(entity_id, metric)
    if pts and len(pts) >= 1:
        return pts, provider or "knowledge_factory", data_class or "derived", meta
    try:
        from institutional_reasoning.fundamentals.derivations import derive_series
        from institutional_reasoning.iki.applicability import infer_sector

        series = derive_series(entity_id, metric, sector=infer_sector(entity_id, None))
        if series.get("found") and series.get("points"):
            return (
                {str(k): float(v) for k, v in series["points"].items()},
                "derived_producer",
                "derived",
                {
                    "formula": series.get("formula"),
                    "derived_from": series.get("derived_from"),
                    "audit": series.get("audit"),
                    "rejected_periods": series.get("rejected_periods"),
                    "reproducible": True,
                },
            )
    except Exception:
        pass
    return None, "", "", {}


def _resolve_pe_points(entity_id: str) -> tuple[dict[str, float] | None, str, str]:
    """Return (points, provider, data_class). Derived first, then packs, then seeds."""
    pts, provider, data_class, _ = _derived_points(entity_id, "PE")
    if pts and len(pts) >= 3:
        return pts, provider, data_class
    pts, src = _pil_points(entity_id, "PE")
    if pts and len(pts) >= 3:
        return pts, src or "peer_intelligence", "seed_panel"
    seed = pe_series_for(entity_id)
    if seed:
        return seed, "institutional_seed", "institutional_seed"
    return None, "", ""


def produce_metric_history(
    entity_id: str,
    metric: str,
    *,
    current: float | None = None,
) -> dict[str, Any]:
    """One historical producer output: Entity → Series → Validated → Coverage → Quality."""
    eid = str(entity_id or "").upper()
    provider = "institutional_seed"
    data_class = "institutional_seed"
    points: dict[str, float] | None = None
    derivation: dict[str, Any] = {}

    if metric == "PE":
        points, provider, data_class = _resolve_pe_points(eid)
        if data_class == "derived":
            _, _, _, derivation = _derived_points(eid, "PE")
    else:
        # Derived producers take precedence over any stored panel.
        pts, prov, dclass, deriv = _derived_points(eid, metric)
        if pts:
            points, provider, data_class, derivation = pts, prov, dclass, deriv
        else:
            pts, src = _pil_points(eid, metric)
            if pts:
                points, provider, data_class = pts, src or "peer_intelligence", "seed_panel"
            elif eid == "INFY" and metric in INFY_EXTRA:
                points = dict(INFY_EXTRA[metric])
            elif eid == "INFY" and metric == "FCF":
                # Map FCF_Margin seed as FCF proxy series for coverage
                points = dict(INFY_EXTRA.get("FCF_Margin") or {})

    analytics = analyse_series(points, current=current)
    as_of = now_iso()
    series_n = int(analytics.get("n") or 0)
    hist_avg = analytics.get("average") if analytics.get("found") else None
    hist_med = analytics.get("median") if analytics.get("found") else None
    pctile = analytics.get("historical_percentile") if analytics.get("found") else None
    cur = current if current is not None else analytics.get("latest")

    quality = score_metric(
        value=hist_avg,
        entity_id=eid,
        metric_entity=eid,
        provider=provider if points else None,
        as_of=as_of,
        series_n=series_n,
        expected_n=10,
        data_class=data_class,
        validated=bool(points and series_n >= 3),
        consistency_ok=bool(
            analytics.get("found")
            and analytics.get("historical_high") is not None
            and analytics.get("historical_low") is not None
            and analytics["historical_high"] >= analytics["historical_low"]
        ),
    )

    validated = bool(quality.get("accept_for_framework") and analytics.get("found"))
    provenance = metric_provenance(
        field=f"historical_{metric.lower()}",
        value=hist_avg,
        entity_id=eid,
        provider=provider or "missing",
        method="series_average",
        validated=validated,
        quality=quality.get("score"),
        as_of=as_of,
        data_class=data_class or "missing",
        extra={"series_n": series_n, "metric": metric},
    )

    return {
        "entity": eid,
        "metric": metric,
        "series": points or {},
        "analytics": analytics,
        "validated": validated,
        "coverage": round(min(1.0, series_n / 10.0), 4) if series_n else 0.0,
        "quality": quality,
        "provenance": provenance,
        "current": cur,
        "historical_average": hist_avg,
        "historical_median": hist_med,
        "historical_percentile": pctile,
        "historical_version": HISTORICAL_VERSION,
        "sector_meta": sector_meta(eid),
        "derivation": derivation,
        "derived": data_class == "derived",
    }


def produce_historical_intelligence(
    entity_id: str,
    *,
    current_pe: float | None = None,
) -> dict[str, Any]:
    """Run all Module 1 producers for an entity."""
    eid = str(entity_id or "").upper()
    producers = {
        m: produce_metric_history(eid, m, current=current_pe if m == "PE" else None)
        for m in REQUIRED_PRODUCERS
    }
    pe = producers.get("PE") or {}
    return {
        "entity": eid,
        "producers": producers,
        "pe": pe,
        "historical_pe": pe.get("historical_average"),
        "historical_median_pe": pe.get("historical_median"),
        "historical_percentile": pe.get("historical_percentile"),
        "current_pe": pe.get("current") if pe.get("current") is not None else current_pe,
        "validated": bool(pe.get("validated")),
        "coverage": pe.get("coverage") or 0.0,
        "quality": pe.get("quality"),
        "historical_version": HISTORICAL_VERSION,
    }
