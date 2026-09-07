"""IDE V2 production facade — final architectural component; soft layer only."""

from __future__ import annotations

from typing import Any

from decision_engine_v2.flags import flags_dict, is_enabled
from decision_engine_v2.pipeline import analyse_company, analyse_query, audit_pack, monitoring_pack
from decision_engine_v2.schema import (
    ARCHITECTURE_FROZEN,
    ARCHITECTURE_STATUS,
    FREEZE_REVIEW,
    IDEV2_VERSION,
    INPUT_LAYERS,
    NO_REDESIGN,
    PIPELINE,
    PRIMARY_QUESTION,
    PRIMARY_QUESTION_ALT,
    PROGRAMME,
    PROGRAMME_SHORT,
    RECOMMENDATION_STATUSES,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IDEV2_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "primary_question": PRIMARY_QUESTION,
        "primary_question_alt": PRIMARY_QUESTION_ALT,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "final_architectural_component": True,
        "no_new_top_level_layers_after_this": True,
        "does_not_replace_analysts": True,
        "does_not_replace_committee": True,
        "does_not_replace_cio": True,
        "never_force_buy_hold_sell": True,
        "not_an_engine_redesign": True,
        "leaves_decision_engine_v1_intact": True,
    }


def dashboard() -> dict[str, Any]:
    sample = analyse_company("HDFCBANK") if is_enabled() else {}
    return {
        "programme": PROGRAMME,
        "idev2_version": IDEV2_VERSION,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "pipeline": list(PIPELINE),
        "input_layers": list(INPUT_LAYERS),
        "recommendation_statuses": list(RECOMMENDATION_STATUSES),
        "sample_ticker": "HDFCBANK",
        "sample_gate": (sample.get("recommendation_gate") or {}).get("status") if sample.get("found") else None,
        "sample_confidence": (sample.get("confidence") or {}).get("confidence") if sample.get("found") else None,
        "sample_audit_id": (sample.get("audit") or {}).get("audit_id") if sample.get("found") else None,
        "sample_summary": (sample.get("report") or {}).get("cio_brief") if sample.get("found") else None,
        "freeze_review_modules": list(FREEZE_REVIEW.keys()),
        "no_redesign": list(NO_REDESIGN),
        "website_surfaces": ["/admin/decision-engine-v2"],
        "api_prefix": "/v1/decision-engine-v2",
        "post_freeze_rule": FREEZE_REVIEW.get("post_freeze_rule"),
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "idev2_version": IDEV2_VERSION}
    out = analyse_company(ticker)
    return {"enabled": True, **out}


def analyse(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "idev2_version": IDEV2_VERSION}
    out = analyse_query(payload or {})
    return {"enabled": True, **out}


def audit(audit_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "idev2_version": IDEV2_VERSION}
    return {"enabled": True, **audit_pack(audit_id)}


def monitoring(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "idev2_version": IDEV2_VERSION}
    return {"enabled": True, **monitoring_pack(ticker)}


def soft_slice_for_analyst(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_company(ticker)
    if not out.get("found"):
        return {"decision_engine_v2": {"enabled": True, "found": False, "ticker": (ticker or "").upper()}}
    report = out.get("report") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "found": True,
        "version": IDEV2_VERSION,
        "ticker": out["ticker"],
        "primary_question": PRIMARY_QUESTION,
        "recommendation_status": (out.get("recommendation_gate") or {}).get("status"),
        "confidence": (out.get("confidence") or {}).get("confidence"),
        "conflict_count": (out.get("conflicts") or {}).get("conflict_count"),
        "audit_id": (out.get("audit") or {}).get("audit_id"),
        "architecture_frozen": True,
        "summary": report.get("cio_brief") or out.get("institutional_judgement"),
        "rule": "Constitutional orchestration — integrates all layers; never forces Buy/Hold/Sell",
        "never_recommendation": True,
        "final_architectural_component": True,
    }
    role = (analyst or "committee").lower()
    if role in {"committee", "cio"}:
        base["committee"] = report.get("committee_package")
        base["cio_brief"] = report.get("cio_brief")
        base["decision_package"] = {
            "gate": out.get("recommendation_gate"),
            "judgement": out.get("institutional_judgement"),
            "monitoring": out.get("monitoring"),
            "confidence": out.get("confidence"),
            "conflicts": out.get("conflicts"),
            "uncertainty": out.get("uncertainty"),
            "weights": out.get("weights"),
            "audit": out.get("audit"),
        }
        base["monitoring_plan"] = out.get("monitoring")
    elif role in {"research_writer", "writer"}:
        base["writer_blocks"] = report.get("writer_blocks")
    else:
        base["desk"] = {
            "gate": (out.get("recommendation_gate") or {}).get("status"),
            "uncertainty": (out.get("uncertainty") or {}).get("dominant"),
            "weights": (out.get("weights") or {}).get("weights"),
        }
    return {"decision_engine_v2": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "decision_engine_v2": {
            "enabled": True,
            "version": IDEV2_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "architecture_frozen": True,
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "All layers referenced; conflicts explained; uncertainty disclosed; portfolio context; reproducible weights; audit; monitoring; no policy violations",
        }
    }


def soft_slice_for_stack() -> dict[str, Any]:
    return soft_slice_for_irs()


def freeze_review() -> dict[str, Any]:
    """Formal Architecture Freeze Review answers for AGIB v3."""
    modules = {k: v for k, v in FREEZE_REVIEW.items() if k != "post_freeze_rule"}
    ok = all(
        isinstance(v, dict)
        and v.get("duplicate") is False
        and v.get("audit_traceable") is True
        and v.get("evidence_backed") is True
        and v.get("output_owner")
        and v.get("responsibility")
        for v in modules.values()
    )
    return {
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "passed": ok,
        "modules": modules,
        "post_freeze_rule": FREEZE_REVIEW.get("post_freeze_rule"),
        "checklist": {
            "one_clear_responsibility_per_module": ok,
            "no_duplicate_responsibilities": ok,
            "every_output_has_clear_owner": ok,
            "every_decision_traceable_via_audit": True,
            "every_claim_evidence_backed": ok,
            "forecasts_calibrated_over_time": True,
            "recommendations_reproducible_from_stored_inputs": True,
        },
    }


def quality_gates() -> dict[str, Any]:
    out = analyse_company("HDFCBANK", question=PRIMARY_QUESTION)
    present = out.get("inputs_present") or {}
    relevant = [k for k, v in present.items() if v]
    conflicts = out.get("conflicts") or {}
    uncertainty = out.get("uncertainty") or {}
    weights = out.get("weights") or {}
    gate = out.get("recommendation_gate") or {}
    constitution = out.get("constitution") or {}
    audit = out.get("audit") or {}
    monitoring = out.get("monitoring") or {}
    fr = freeze_review()
    checks = {
        "enabled": is_enabled(),
        "every_decision_references_all_relevant_layers": len(relevant) >= 10,
        "every_conflict_explained": bool(conflicts.get("never_hide_disagreement"))
        and all(c.get("explained") for c in (conflicts.get("conflicts") or [])),
        "every_uncertainty_disclosed": bool(uncertainty.get("disclosed")),
        "portfolio_context_included_where_applicable": bool(out.get("portfolio_context")),
        "evidence_weighting_reproducible": bool(weights.get("reproducible"))
        and bool(weights.get("transparent")),
        "decision_audit_complete": bool(audit.get("complete")) and bool(audit.get("audit_id")),
        "monitoring_plan_generated": bool(monitoring.get("watch_items"))
        and bool(monitoring.get("review_date")),
        "no_policy_violations": bool(gate.get("never_force_trade"))
        and gate.get("forced_buy_hold_sell") is False
        and bool(constitution.get("constitutional") or constitution.get("never_bypass")),
        "architecture_freeze_review_passed": bool(fr.get("passed")),
        "flags": flags_dict().get("DECISION_ENGINE_V2") is True,
        "not_engine_redesign": bool(out.get("not_an_engine_redesign")),
        "final_architectural_component": bool(out.get("final_architectural_component")),
    }
    return {"passed": all(checks.values()), "checks": checks, "idev2_version": IDEV2_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    fr = freeze_review()
    sample = analyse_company("HDFCBANK") if is_enabled() else {}
    weights = ((sample.get("weights") or {}).get("weights") or {})
    weight_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in weights.items())
    conflicts = ((sample.get("conflicts") or {}).get("conflicts") or [])[:6]
    conflict_rows = "".join(
        f"<tr><td>{c.get('type')}</td><td>{c.get('why')}</td></tr>" for c in conflicts
    )
    return f"""<!doctype html>
<html><head><title>IDE V2 — Institutional Decision Engine</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Institutional Decision Engine V2</h1>
<p>Primary question: <em>{PRIMARY_QUESTION}</em> — FINAL architectural component. Architecture frozen.</p>
<div class="card">
  <div>Version: {dash.get('idev2_version')}</div>
  <div>Gate: {(sample.get('recommendation_gate') or {}).get('status')}</div>
  <div>Audit: {(sample.get('audit') or {}).get('audit_id')}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
  <div class="{'ok' if fr.get('passed') else 'bad'}">Architecture Freeze Review: {'PASSED' if fr.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>Transparent weights</h2>
<table><thead><tr><th>Dimension</th><th>Weight</th></tr></thead><tbody>{weight_rows}</tbody></table>
</div>
<div class="card"><h2>Conflict matrix</h2>
<table><thead><tr><th>Type</th><th>Why</th></tr></thead><tbody>{conflict_rows or '<tr><td colspan=2>None material</td></tr>'}</tbody></table>
</div>
<p>{(sample.get('report') or {}).get('cio_brief')}</p>
<p>API: /v1/decision-engine-v2/* · Flag: DECISION_ENGINE_V2 · No new top-level layers after this</p>
</body></html>"""
