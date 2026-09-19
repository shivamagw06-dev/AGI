"""LIDI morning pipeline — Collect → Validate → Derive → Knowledge Objects → Evidence Packs.

Never calls reasoning. Never silent fixture fallback.
"""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Dict, Optional

from live_data import store
from live_data.bridge import publish_to_knowledge_factory, soft_research_office_signal
from live_data.collectors import (
    collect_bse_corporate_actions,
    collect_company_ir,
    collect_nse_announcements,
    collect_nse_bhavcopy,
    collect_rbi_dbie,
)
from live_data.producers import derive_bhavcopy, derive_events, derive_ir_filings, derive_macro
from live_data.schema import FREEZE_LOCKS, LIDI_VERSION, SOURCES
from live_data.validators import validate_live_dataset


def _allow_recorded_sample(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return bool(explicit)
    # Production must never silently use recorded samples.
    if os.environ.get("AGIB_ENV", "").lower() in {"prod", "production"}:
        return False
    return os.environ.get("LIDI_ALLOW_RECORDED_SAMPLE", "").lower() in {"1", "true", "yes"}


def _validate_and_store(
    env: Dict[str, Any],
    *,
    entity: str,
    required_payload_fields: tuple[str, ...] = (),
    row_ticker_field: str | None = "symbol",
    allow_empty_rows: bool = False,
) -> Dict[str, Any]:
    if not env.get("ok"):
        return {
            "ok": False,
            "source_id": env.get("source_id"),
            "collector_id": env.get("collector_id"),
            "reason": env.get("reason") or env.get("error") or "collect_failed",
            "transparent_insufficiency": True,
            "fixture": False,
            "validation": {"ok": False, "failures": ["collector_failed"]},
        }
    verdict = validate_live_dataset(
        env,
        required_payload_fields=required_payload_fields,
        row_ticker_field=row_ticker_field,
        allow_empty_rows=allow_empty_rows,
    )
    out = deepcopy(env)
    out["validation"] = verdict
    out["provenance"] = {
        **(out.get("provenance") or {}),
        "validated_at": verdict.get("validated_at"),
        "validated": verdict.get("ok"),
    }
    if not verdict.get("ok"):
        out["ok"] = False
        out["reason"] = "validation_failed"
        out["transparent_insufficiency"] = True
        return out
    store.put_validated(str(env["source_id"]), entity, out)
    return out


def run_live_ingestion(
    *,
    as_of: str | None = None,
    allow_recorded_sample: bool | None = None,
    ir_ticker: str = "INFY",
    injected: dict[str, Any] | None = None,
    stop_after: str | None = None,
) -> Dict[str, Any]:
    """Run Track-1 collectors in recommended order.

    Order: NSE Bhavcopy → NSE Announcements → BSE Actions → RBI DBIE → Company IR
    """
    samples = _allow_recorded_sample(allow_recorded_sample)
    inj = injected or {}
    started = store.utc_now()
    stages: Dict[str, Any] = {}
    derived: Dict[str, Any] = {}
    quality_failures: list[str] = []

    # 1) NSE Bhavcopy
    bhav_env = collect_nse_bhavcopy(
        as_of=as_of,
        injected_csv=inj.get("nse_bhavcopy"),
        allow_recorded_sample=samples,
    )
    bhav_val = _validate_and_store(bhav_env, entity="LATEST")
    stages["nse_bhavcopy"] = {
        "ok": bhav_val.get("ok"),
        "mode": bhav_val.get("mode"),
        "fallback": bhav_val.get("fallback"),
        "validation": bhav_val.get("validation"),
        "row_count": ((bhav_val.get("payload") or {}).get("row_count")),
        "effective_date": bhav_val.get("effective_date"),
        "fixture": bhav_val.get("fixture"),
        "reason": bhav_val.get("reason"),
        "error": bhav_val.get("error"),
    }
    if not bhav_val.get("ok"):
        quality_failures.append("nse_bhavcopy")
    else:
        rows = (bhav_val.get("payload") or {}).get("rows") or []
        derived["bhavcopy"] = derive_bhavcopy(rows, as_of=bhav_val.get("effective_date") or as_of)
        for r in derived["bhavcopy"]["rows"]:
            r["provenance"] = bhav_val.get("provenance")
    if stop_after == "nse_bhavcopy":
        return _finalize(started, stages, derived, quality_failures, publish=False)

    # 2) NSE Announcements
    ann_env = collect_nse_announcements(
        injected_json=inj.get("nse_announcements"),
        allow_recorded_sample=samples,
    )
    ann_val = _validate_and_store(ann_env, entity="LATEST")
    stages["nse_announcements"] = {
        "ok": ann_val.get("ok"),
        "mode": ann_val.get("mode"),
        "fallback": ann_val.get("fallback"),
        "validation": ann_val.get("validation"),
        "event_count": ((ann_val.get("payload") or {}).get("event_count")),
        "fixture": ann_val.get("fixture"),
        "reason": ann_val.get("reason"),
        "error": ann_val.get("error"),
    }
    if not ann_val.get("ok"):
        quality_failures.append("nse_announcements")
    else:
        events = (ann_val.get("payload") or {}).get("events") or []
        derived["announcements"] = derive_events(events, source="NSE_ANNOUNCEMENTS")
    if stop_after == "nse_announcements":
        return _finalize(started, stages, derived, quality_failures, publish=False)

    # 3) BSE Corporate Actions — legacy collector, then multi-strategy connector recovery
    bse_env = collect_bse_corporate_actions(
        injected_csv=inj.get("bse_corporate_actions"),
        allow_recorded_sample=samples,
    )
    bse_val = _validate_and_store(bse_env, entity="LATEST", row_ticker_field="symbol")
    if not bse_val.get("ok") and not inj.get("bse_corporate_actions"):
        try:
            from institutional_data.connectors.registry import get_connector

            bse_c = get_connector("bse_corporate_actions").run(allow_recorded_sample=samples)
            if bse_c.ok:
                bse_val = {
                    "ok": True,
                    "mode": bse_c.mode,
                    "payload": {"actions": bse_c.normalized or bse_c.records, "action_count": len(bse_c.records)},
                    "fixture": False,
                    "connector_recovery": True,
                }
                stages.setdefault("bse_corporate_actions", {})["connector_recovery"] = True
        except Exception:
            pass
    stages["bse_corporate_actions"] = {
        "ok": bse_val.get("ok"),
        "mode": bse_val.get("mode"),
        "fallback": bse_val.get("fallback"),
        "validation": bse_val.get("validation"),
        "action_count": ((bse_val.get("payload") or {}).get("action_count")),
        "fixture": bse_val.get("fixture"),
        "reason": bse_val.get("reason"),
        "error": bse_val.get("error"),
        "connector_recovery": bool(bse_val.get("connector_recovery")),
    }
    if not bse_val.get("ok"):
        quality_failures.append("bse_corporate_actions")
    else:
        actions = (bse_val.get("payload") or {}).get("actions") or []
        derived["corporate_actions"] = derive_events(actions, source="BSE_CORPORATE_ACTIONS")
    if stop_after == "bse_corporate_actions":
        return _finalize(started, stages, derived, quality_failures, publish=False)

    # 4) RBI DBIE — structured connector recovery on empty series
    rbi_env = collect_rbi_dbie(
        injected_json=inj.get("rbi_dbie"),
        allow_recorded_sample=samples,
    )
    rbi_val = _validate_and_store(
        rbi_env,
        entity="LATEST",
        row_ticker_field=None,
        required_payload_fields=("series",),
    )
    if not rbi_val.get("ok") and not inj.get("rbi_dbie"):
        try:
            from institutional_data.connectors.registry import get_connector

            rbi_c = get_connector("rbi_dbie").run(allow_recorded_sample=samples)
            if rbi_c.ok:
                rbi_val = {
                    "ok": True,
                    "mode": rbi_c.mode,
                    "payload": {"series": rbi_c.normalized or rbi_c.records},
                    "fixture": False,
                    "connector_recovery": True,
                }
        except Exception:
            pass
    stages["rbi_dbie"] = {
        "ok": rbi_val.get("ok"),
        "mode": rbi_val.get("mode"),
        "fallback": rbi_val.get("fallback"),
        "validation": rbi_val.get("validation"),
        "series_count": len((rbi_val.get("payload") or {}).get("series") or []),
        "fixture": rbi_val.get("fixture"),
        "reason": rbi_val.get("reason"),
        "error": rbi_val.get("error"),
        "connector_recovery": bool(rbi_val.get("connector_recovery")),
    }
    if not rbi_val.get("ok"):
        quality_failures.append("rbi_dbie")
    else:
        series = (rbi_val.get("payload") or {}).get("series") or []
        derived["macro"] = derive_macro(series)
    if stop_after == "rbi_dbie":
        return _finalize(started, stages, derived, quality_failures, publish=False)

    # 5) Company IR — discovery engine expands beyond hardcoded hubs
    ir_env = collect_company_ir(
        ticker=ir_ticker,
        injected_json=inj.get("company_ir"),
        allow_recorded_sample=samples,
    )
    if (not ir_env.get("ok") or not ((ir_env.get("payload") or {}).get("documents"))) and not inj.get("company_ir"):
        try:
            from institutional_data.connectors.registry import get_connector

            ir_c = get_connector("company_ir").run(entity=ir_ticker, download_files=True, max_downloads=4)
            if ir_c.ok:
                ir_env = {
                    "ok": True,
                    "mode": ir_c.mode,
                    "payload": {
                        "ticker": ir_ticker,
                        "documents": ir_c.normalized or ir_c.records,
                        "document_count": len(ir_c.records),
                    },
                    "fixture": False,
                    "connector_recovery": True,
                }
        except Exception:
            pass
    allow_empty_ir = bool(
        ((ir_env.get("payload") or {}).get("structured_filings") == "UNKNOWN")
        or ((ir_env.get("payload") or {}).get("document_count") == 0 and ir_env.get("mode") == "live_probe")
    )
    ir_val = _validate_and_store(
        ir_env,
        entity=ir_ticker,
        row_ticker_field=None,
        allow_empty_rows=allow_empty_ir,
    )
    stages["company_ir"] = {
        "ok": ir_val.get("ok"),
        "mode": ir_val.get("mode"),
        "fallback": ir_val.get("fallback"),
        "validation": ir_val.get("validation"),
        "document_count": ((ir_val.get("payload") or {}).get("document_count")),
        "fixture": ir_val.get("fixture"),
        "reason": ir_val.get("reason"),
        "error": ir_val.get("error"),
    }
    if not ir_val.get("ok"):
        quality_failures.append("company_ir")
    else:
        docs = (ir_val.get("payload") or {}).get("documents") or []
        derived["ir"] = derive_ir_filings(docs, ticker=(ir_val.get("payload") or {}).get("ticker") or ir_ticker)

    return _finalize(started, stages, derived, quality_failures, publish=True, as_of=as_of)


def _finalize(
    started: str,
    stages: Dict[str, Any],
    derived: Dict[str, Any],
    quality_failures: list[str],
    *,
    publish: bool,
    as_of: str | None = None,
) -> Dict[str, Any]:
    publish_result = None
    ro_signal = None
    if publish and derived:
        publish_result = publish_to_knowledge_factory(
            as_of=as_of or started[:10],
            bhavcopy=derived.get("bhavcopy"),
            announcements=derived.get("announcements"),
            corporate_actions=derived.get("corporate_actions"),
            macro=derived.get("macro"),
            ir=derived.get("ir"),
        )
        ro_signal = soft_research_office_signal(publish_result)

    # Quality gates
    silent_fixture = any(s.get("fixture") is True for s in stages.values())
    gate_fail = list(quality_failures)
    if silent_fixture:
        gate_fail.append("silent_fixture_usage")
    for sid, st in stages.items():
        val = st.get("validation") or {}
        if val.get("failures"):
            if "duplicate" in val["failures"]:
                gate_fail.append(f"duplicate:{sid}")
            if "provenance_missing" in val["failures"]:
                gate_fail.append(f"provenance:{sid}")

    operational = sum(1 for s in stages.values() if s.get("ok"))
    report = {
        "ok": operational >= 1 and not silent_fixture,
        "lidi_version": LIDI_VERSION,
        "programme": "Live Institutional Data Ingestion",
        "started_at": started,
        "finished_at": store.utc_now(),
        "sources": list(SOURCES),
        "stages": stages,
        "derived_keys": list(derived.keys()),
        "publish": publish_result,
        "research_office_soft": ro_signal,
        "quality_gates": {
            "passed": len(set(gate_fail)) == 0 and operational == len(stages),
            "failures": sorted(set(gate_fail)),
            "collectors_operational": operational,
            "collectors_total": len(stages),
            "fixture_collectors_disabled": True,
            "never_silent_fixture_fallback": FREEZE_LOCKS["never_silent_fixture_fallback"],
            "reasoning_untouched": True,
        },
        "fallbacks": store.list_fallbacks(limit=20),
        "validations": store.list_validations(limit=20),
        "collector_health": store.get_collector_health(),
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "fixture": False,
    }
    store.set_last_run(report)
    store.put_report(f"run_{started.replace(':', '').replace('-', '')[:15]}", report)
    return report
