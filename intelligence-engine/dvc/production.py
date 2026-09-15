"""DVC production bridge — soft validation via MarketDataClient (not an engine)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dvc.enrich import merge_dvc_into_dossier
from dvc.schema import DVC_VERSION
from dvc import store as dvc_store
from dvc.validate import ask_agi_hints, panel_for_company, validate_symbol


def is_dvc_enabled() -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), "dvc", True))
    except Exception:
        return True


def _client():
    from app.core.config import get_settings
    from app.market_data.client import MarketDataClient

    return MarketDataClient.from_settings(get_settings())


def _run(coro):
    from app.core.async_run import run_coro

    return run_coro(coro)


def validate_ticker(ticker: str, *, client: Any | None = None) -> Dict[str, Any]:
    if not is_dvc_enabled():
        return {"enabled": False, "dvc_version": DVC_VERSION, "bypassed": True}
    md = client or _client()
    return _run(validate_symbol(md, ticker))


def get_company_quality(ticker: str) -> Dict[str, Any]:
    row = dvc_store.get_company(ticker)
    if not row:
        return {"enabled": is_dvc_enabled(), "ticker": (ticker or "").upper(), "found": False}
    return {
        "enabled": True,
        "found": True,
        "ticker": row.get("company_id"),
        "quality": row.get("quality"),
        "grades": row.get("grades"),
        "panel": panel_for_company(row),
        "conflicts": row.get("conflicts") or [],
        "missing_fields": row.get("missing_fields") or [],
        "winning_provider": row.get("winning_provider_summary"),
        "updated_at": row.get("updated_at"),
        "dvc_version": DVC_VERSION,
    }


def enrich_cid(ticker: str, *, client: Any | None = None) -> Dict[str, Any]:
    """Run DVC validation and soft-merge audited fields into CID."""
    from cid.coverage import compute_coverage
    from cid.ingest import ensure_dossier
    from cid.store import get_cid_store

    t = (ticker or "").upper()
    if not t:
        return {"enabled": False, "reason": "no_ticker"}
    if not is_dvc_enabled():
        return {"enabled": False, "dvc_version": DVC_VERSION, "bypassed": True}

    pack = validate_ticker(t, client=client)
    store = get_cid_store()
    dossier = store.get(t) or ensure_dossier(t)
    if pack.get("enabled") and pack.get("validated_fields"):
        dossier = merge_dvc_into_dossier(dossier, pack)
        cov = compute_coverage(dossier)
        dossier.update(
            {
                "coverage": cov["coverage"],
                "coverage_score": cov["coverage_score"],
                "coverage_grade": cov["coverage_grade"],
                "missing_evidence": cov["missing_evidence"],
            }
        )
        dossier = store.put(dossier)
    return {
        "enabled": bool(pack.get("enabled")),
        "dvc_version": DVC_VERSION,
        "ticker": t,
        "package": {
            "quality": pack.get("quality"),
            "grades": pack.get("grades"),
            "conflict_summary": pack.get("conflict_summary"),
            "winning_provider": pack.get("winning_provider_summary"),
            "field_count": len(pack.get("validated_fields") or {}),
        },
        "dossier": {
            "ticker": dossier.get("ticker"),
            "research_grade": dossier.get("research_grade"),
            "data_grade": dossier.get("data_grade"),
            "data_quality_panel": dossier.get("data_quality_panel"),
            "dvc": dossier.get("dvc"),
            "validated_fields_count": len(dossier.get("validated_fields") or {}),
        },
        "ask_agi_hints": ask_agi_hints(pack),
    }


def package_for_ask_agi(ticker: str | None, *, client: Any | None = None) -> Dict[str, Any]:
    """Soft Ask AGI attach — load DVC layer; prefer validated canonical values."""
    if not is_dvc_enabled():
        return {"enabled": False, "dvc_version": DVC_VERSION, "bypassed": True}
    t = (ticker or "").upper()
    if not t:
        return {"enabled": True, "ticker": None, "reason": "no_ticker", "dvc_version": DVC_VERSION}

    existing = dvc_store.get_company(t)
    if existing and existing.get("validated_fields"):
        pack = {"enabled": True, **existing}
    else:
        pack = validate_ticker(t, client=client)

    return {
        "enabled": True,
        "dvc_version": DVC_VERSION,
        "ticker": t,
        "validated_fields": pack.get("validated_fields") or {},
        "quality": pack.get("quality"),
        "grades": pack.get("grades"),
        "conflicts": pack.get("conflicts") or [],
        "conflict_summary": pack.get("conflict_summary"),
        "panel": panel_for_company(pack),
        "answer_policy": "validated_canonical_values_only",
        "ask_agi_hints": ask_agi_hints(pack),
        "winning_provider": pack.get("winning_provider_summary"),
    }


def production_dashboard() -> Dict[str, Any]:
    providers = dvc_store.list_provider_health()
    conflicts = dvc_store.list_conflicts(limit=40)
    updates = dvc_store.list_latest_updates(limit=30)
    incomplete = dvc_store.incomplete_companies(limit=30)
    refresh = dvc_store.needing_refresh(limit=30)
    errors = dvc_store.list_validation_errors(limit=40)
    companies = dvc_store.list_companies(limit=100)

    # Coverage heatmap (company × overall/coverage/freshness)
    heatmap = [
        {
            "company_id": c.get("company_id"),
            "coverage": (c.get("quality") or {}).get("coverage"),
            "freshness": (c.get("quality") or {}).get("freshness"),
            "confidence": (c.get("quality") or {}).get("confidence"),
            "consistency": (c.get("quality") or {}).get("consistency"),
            "overall": (c.get("quality") or {}).get("overall"),
            "research_grade": (c.get("grades") or {}).get("research_grade"),
        }
        for c in companies
    ]

    avg_overall = None
    if heatmap:
        vals = [float(h["overall"]) for h in heatmap if h.get("overall") is not None]
        avg_overall = round(sum(vals) / len(vals), 4) if vals else None

    return {
        "programme": "DVC",
        "dvc_version": DVC_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_dvc_enabled(),
        "role": "data_validation_and_consensus",
        "layer": "Market Data → DVC → MarketDataClient → LEO → CID",
        "not_an_engine": True,
        "not_a_provider": True,
        "provider_health": providers,
        "provider_reliability": providers,
        "provider_latency": [
            {"provider": p.get("provider"), "avg_latency_ms": p.get("avg_latency_ms")} for p in providers
        ],
        "coverage_heatmap": heatmap,
        "conflict_queue": conflicts,
        "companies_missing_data": incomplete,
        "consensus_results": [
            {
                "company_id": c.get("company_id"),
                "winning_provider": c.get("winning_provider_summary"),
                "overall": (c.get("quality") or {}).get("overall"),
                "conflicts": len(c.get("conflicts") or []),
            }
            for c in companies[:40]
        ],
        "latest_updates": updates,
        "validation_errors": errors,
        "most_incomplete_companies": incomplete,
        "companies_needing_refresh": refresh,
        "metrics": {
            "companies_tracked": len(companies),
            "open_conflicts": sum(1 for c in conflicts if c.get("status") == "open"),
            "avg_overall_quality": avg_overall,
            "providers_tracked": len(providers),
        },
        "provider_priority": {
            "1": "official_exchange",
            "2": "indianapi",
            "3": "finnhub",
            "4": "fmp",
            "5": "yahoo",
        },
    }


def quality_gates(tickers: List[str] | None = None) -> Dict[str, Any]:
    from dvc.consensus import consensus_for_field
    from dvc.conflicts import detect_conflicts
    from dvc.priority import provider_priority
    from dvc.quality import compute_quality, grade_from_quality

    # Offline authoritative gates
    obs = {
        "last": [
            {"provider": "indianapi", "value": 1245.40},
            {"provider": "finnhub", "value": 1245.35},
            {"provider": "yahoo", "value": 1245.50},
        ],
        "market_cap": [
            {"provider": "indianapi", "value": 1_000_000_000_000},
            {"provider": "yahoo", "value": 1_250_000_000_000},
        ],
    }
    vf_last = consensus_for_field("last", obs["last"], symbol="INFY")
    conflicts = detect_conflicts(obs, company_id="INFY")
    validated = {
        "last": vf_last,
        "market_cap": consensus_for_field("market_cap", obs["market_cap"], symbol="INFY"),
    }
    quality = compute_quality(validated, conflicts=conflicts, observations_by_field=obs, kind="combined")
    grades = grade_from_quality(quality)

    checks = {
        "priority_indianapi_before_yahoo": provider_priority("indianapi") < provider_priority("yahoo"),
        "priority_finnhub_before_fmp": provider_priority("finnhub") < provider_priority("fmp"),
        "consensus_winner_indianapi": vf_last.get("provider") == "indianapi",
        "consensus_has_confidence": float(vf_last.get("confidence") or 0) > 0.9,
        "conflict_detected_on_market_cap": any(c.get("field") == "market_cap" for c in conflicts),
        "quality_scores_present": all(
            k in quality for k in ("coverage", "freshness", "confidence", "consistency", "overall")
        ),
        "grades_present": all(k in grades for k in ("research_grade", "knowledge_grade", "data_grade")),
        "flag_readable": is_dvc_enabled() in (True, False),
        "store_roundtrip": _store_roundtrip_ok(),
    }

    samples = tickers or ["INFY", "HDFCBANK"]
    live_rows = []
    for t in samples:
        row = dvc_store.get_company(t)
        live_rows.append(
            {
                "ticker": t,
                "validated": bool(row and row.get("validated_fields")),
                "overall": (row or {}).get("quality", {}).get("overall") if row else None,
                "conflicts": len((row or {}).get("conflicts") or []) if row else 0,
            }
        )

    return {
        "dvc_version": DVC_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "offline_consensus": {
            "last": vf_last,
            "conflicts": conflicts,
            "quality": quality,
            "grades": grades,
        },
        "tracked_samples": live_rows,
        "note": "Offline consensus/conflict/quality gates are authoritative; live provider sampling is optional.",
    }


def _store_roundtrip_ok() -> bool:
    try:
        from dvc.models import make_validated_field

        pack = {
            "validated_fields": {
                "last": make_validated_field(
                    field="last",
                    value=100.0,
                    provider="indianapi",
                    confidence=0.97,
                    symbol="TESTDVC",
                )
            },
            "conflicts": [],
            "quality": {"overall": 0.9, "coverage": 0.9, "freshness": 0.9, "confidence": 0.97, "consistency": 1.0},
            "grades": {"research_grade": "B", "data_grade": "B", "knowledge_grade": "B"},
            "missing_fields": [],
            "winning_provider_summary": "indianapi",
        }
        dvc_store.upsert_company_validation("TESTDVC", pack)
        got = dvc_store.get_company("TESTDVC")
        return bool(got and (got.get("validated_fields") or {}).get("last", {}).get("value") == 100.0)
    except Exception:
        return False


def success_metrics() -> Dict[str, Any]:
    dash = production_dashboard()
    providers = dash.get("provider_health") or []
    uptimes = [p.get("uptime_pct") for p in providers if p.get("uptime_pct") is not None]
    return {
        "provider_uptime_avg": round(sum(uptimes) / len(uptimes), 2) if uptimes else None,
        "consensus_accuracy_proxy": dash.get("metrics", {}).get("avg_overall_quality"),
        "conflict_resolution_rate": None,  # open queue; resolution tracked when closed
        "coverage_pct": _avg_metric("coverage"),
        "freshness_pct": _avg_metric("freshness"),
        "validation_pct": _avg_metric("validation"),
        "cid_quality": _avg_metric("overall"),
        "open_conflicts": dash.get("metrics", {}).get("open_conflicts"),
        "dvc_version": DVC_VERSION,
    }


def _avg_metric(key: str) -> Optional[float]:
    rows = dvc_store.list_companies(limit=200)
    vals = [float((r.get("quality") or {}).get(key)) for r in rows if (r.get("quality") or {}).get(key) is not None]
    if not vals:
        return None
    return round(100.0 * sum(vals) / len(vals), 2)
