"""CIO-01 Mission Control / API façades — comparison orchestration only."""

from __future__ import annotations

from typing import Any

from comparative_intelligence.flags import flags_dict, is_enabled
from comparative_intelligence import store as cio_store
from comparative_intelligence.schema import (
    CIO01_PRODUCT,
    CIO01_RECOMMENDATION_POLICY,
    CIO01_SPEC,
    CIO01_SUBSYSTEM,
    CIO01_VERSION,
    CIO01_WORKSTREAM_ID,
    COMPARISON_TYPES,
    DEFAULT_COMPARE_MODULES,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGI_COMPARATIVE_INTELLIGENCE",
        "workstream_id": CIO01_WORKSTREAM_ID,
        "product": CIO01_PRODUCT,
        "subsystem": CIO01_SUBSYSTEM,
        "version": CIO01_VERSION,
        "role": "comparison_orchestration_layer",
        "compares_only": True,
        "never_recalculates": True,
        "never_rescores": True,
        "never_invents_conclusions": True,
        "not_fire_07": True,
        "buy_sell": False,
        "valuation": False,
        "dcf": False,
        "forecast": False,
        "comparison_types": list(COMPARISON_TYPES),
        "default_modules": list(DEFAULT_COMPARE_MODULES),
        "consumes": [
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FIRE-04",
            "FIRE-05",
            "FIRE-06",
            "IO-01 collectors",
            "financial_warehouse",
            "derived_metrics",
            "FKB",
        ],
        "recommendation_policy": CIO01_RECOMMENDATION_POLICY,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": CIO01_SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    h = health()
    m = cio_store.metrics()
    return {
        "status": h["status"],
        "workstream_id": CIO01_WORKSTREAM_ID,
        "version": CIO01_VERSION,
        "compares_only": True,
        "buy_sell": False,
        "panels": m.get("panels") or {},
        "metrics": m,
        "note": "Cross-company boards via /comparative-intelligence/compare",
        "spec": CIO01_SPEC,
        "as_of": now_iso(),
    }


def compare_companies(
    tickers: list[str],
    *,
    question: str | None = None,
    comparison_type: str | None = None,
    modules: list[str] | None = None,
    series_maps: dict[str, dict[str, list[dict[str, Any]]]] | None = None,
    documents_map: dict[str, list[dict[str, Any]]] | None = None,
    prebuilt_map: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": CIO01_WORKSTREAM_ID,
            "version": CIO01_VERSION,
        }
    from comparative_intelligence.coordinator import compare

    icr = compare(
        tickers=tickers,
        question=question,
        comparison_type=comparison_type,
        modules=modules,
        series_maps=series_maps,
        documents_map=documents_map,
        prebuilt_map=prebuilt_map,
    )
    cio_store.record_icr(icr)
    pack = {
        "ok": True,
        "enabled": True,
        "workstream_id": CIO01_WORKSTREAM_ID,
        "product": CIO01_PRODUCT,
        "version": CIO01_VERSION,
        "compares_only": True,
        "buy_sell": False,
        "valuation": False,
        "icr": icr,
        "tickers": icr.get("tickers"),
        "comparison_type": icr.get("comparison_type"),
        "modules_invoked": icr.get("modules_invoked"),
        "sections": icr.get("sections"),
        "key_differences": icr.get("key_differences"),
        "confidence": icr.get("confidence"),
        "evidence_references": icr.get("evidence_references"),
        "assembly_ms": icr.get("assembly_ms"),
        "routing": icr.get("routing"),
        "guardrails": icr.get("guardrails"),
    }
    try:
        from platform_event_bus.publisher import soft_publish
        from platform_event_bus.schema import EVENT_COMPARISON_COMPLETED

        soft_publish(
            EVENT_COMPARISON_COMPLETED,
            producer="cio-01",
            payload={
                "tickers": icr.get("tickers"),
                "comparison_type": icr.get("comparison_type"),
                "modules_invoked": icr.get("modules_invoked"),
                "assembly_ms": icr.get("assembly_ms"),
            },
        )
    except Exception:
        pass
    return pack


def query(
    *,
    tickers: list[str] | None = None,
    question: str = "",
    comparison_type: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from comparative_intelligence.routing import extract_tickers

    resolved = extract_tickers(question, explicit=tickers)
    return compare_companies(
        resolved,
        question=question,
        comparison_type=comparison_type,
        **kwargs,
    )


def as_office_response(
    pack: dict[str, Any],
    *,
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap a native CIO pack in the shared OfficeResponse contract."""
    from office_sdk.adapters import wrap_cio_response

    return wrap_cio_response(pack, request=request)


def soft_slice_mission_control(tickers: list[str] | None = None) -> dict[str, Any]:
    m = cio_store.metrics()
    base = {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": CIO01_WORKSTREAM_ID,
        "product": CIO01_PRODUCT,
        "version": CIO01_VERSION,
        "compares_only": True,
        "buy_sell": False,
        "panels": m.get("panels") or {},
        "metrics": m,
    }
    if tickers and len(tickers) >= 2:
        pack = compare_companies(list(tickers))
        icr = pack.get("icr") if isinstance(pack.get("icr"), dict) else {}
        base["last_tickers"] = icr.get("tickers")
        base["last_comparison_type"] = icr.get("comparison_type")
        m2 = cio_store.metrics()
        base["panels"] = m2.get("panels") or {}
        base["metrics"] = m2
    return base


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>CIO-01 Comparative Intelligence</title></head>
<body>
<h1>CIO-01 — Comparative Intelligence Office</h1>
<pre>{h}</pre>
<p>Comparison only. No BUY/SELL. No new analysis. Not FIRE-07.</p>
</body></html>"""
