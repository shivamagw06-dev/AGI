"""ILM production facade — soft institutional layer, no redesign."""

from __future__ import annotations

from typing import Any

from institutional_memory.committee_memory.engine import committee_history
from institutional_memory.flags import flags_dict, is_enabled
from institutional_memory.forecast_memory.engine import forecast_history
from institutional_memory.pipeline import analyse_company, learning_update as learning_update_pipeline
from institutional_memory.portfolio_memory.engine import portfolio_history
from institutional_memory.schema import (
    ARCHITECTURE_STATUS,
    ILM_VERSION,
    NO_REDESIGN,
    PIPELINE,
    PRIMARY_QUESTION,
    PRIMARY_QUESTION_ALT,
    PROGRAMME,
    PROGRAMME_SHORT,
)
from institutional_memory.store.corpus import company_ids, list_portfolios
from institutional_memory.thesis_memory.engine import thesis_history
from institutional_memory.versioning.rules import assert_append_only


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ILM_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "primary_question_alt": PRIMARY_QUESTION_ALT,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "includes_mistake_intelligence": True,
        "not_passive_storage": True,
        "active_learning": True,
        "not_an_engine_redesign": True,
        "never_recommendation": True,
    }


def dashboard() -> dict[str, Any]:
    sample = analyse_company("HDFCBANK")
    return {
        "programme": PROGRAMME,
        "ilm_version": ILM_VERSION,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "pipeline": list(PIPELINE),
        "companies": company_ids(),
        "portfolios": list_portfolios(),
        "sample_ticker": "HDFCBANK",
        "sample_lesson_count": ((sample.get("learning") or {}).get("institutional_learning") or {}).get(
            "lesson_count"
        )
        if sample.get("found")
        else None,
        "sample_mistake_count": (sample.get("mistakes") or {}).get("mistake_count") if sample.get("found") else None,
        "sample_summary": (sample.get("report") or {}).get("executive_summary") if sample.get("found") else None,
        "includes_mistake_intelligence": True,
        "no_redesign": list(NO_REDESIGN),
        "website_surfaces": ["/admin/institutional-memory"],
        "api_prefix": "/v1/ilm",
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ilm_version": ILM_VERSION}
    out = analyse_company(ticker)
    return {"enabled": True, **out}


def thesis(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ilm_version": ILM_VERSION}
    out = thesis_history(ticker)
    return {"enabled": True, "ilm_version": ILM_VERSION, **out}


def committee(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ilm_version": ILM_VERSION}
    out = committee_history(ticker)
    return {"enabled": True, "ilm_version": ILM_VERSION, **out}


def forecast(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ilm_version": ILM_VERSION}
    out = forecast_history(ticker)
    return {"enabled": True, "ilm_version": ILM_VERSION, **out}


def portfolio(portfolio_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ilm_version": ILM_VERSION}
    out = portfolio_history(portfolio_id)
    return {"enabled": True, "ilm_version": ILM_VERSION, **out}


def learning_update(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ilm_version": ILM_VERSION}
    out = learning_update_pipeline(payload or {})
    return {"enabled": True, **out}


def soft_slice_for_analyst(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_company(ticker)
    if not out.get("found"):
        return {"institutional_memory": {"enabled": True, "found": False, "ticker": (ticker or "").upper()}}
    report = out.get("report") or {}
    learning = (out.get("learning") or {}).get("institutional_learning") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "found": True,
        "version": ILM_VERSION,
        "ticker": out["ticker"],
        "primary_question": PRIMARY_QUESTION,
        "lesson_count": learning.get("lesson_count"),
        "thinking_improved": learning.get("thinking_improved"),
        "mistake_count": (out.get("mistakes") or {}).get("mistake_count"),
        "summary": report.get("executive_summary"),
        "rule": "Active institutional learning — classify mistakes, preserve versions, update knowledge",
        "never_recommendation": True,
        "includes_mistake_intelligence": True,
    }
    role = (analyst or "committee").lower()
    if role in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["cio_brief"] = report.get("cio_brief")
        base["institutional_learning"] = learning
        base["mistake_intelligence"] = out.get("mistakes")
        base["accuracy"] = out.get("accuracy")
    elif role in {"research_writer", "writer"}:
        base["writer_blocks"] = report.get("writer_blocks")
    elif role in {"financial", "business", "risk", "macro", "sector", "valuation"}:
        base["desk"] = {
            "thesis_evolution": (out.get("thesis") or {}).get("evolution"),
            "forecast_history": (out.get("forecasts") or {}).get("history"),
            "lessons": learning.get("what_improved"),
            "mistakes": (out.get("mistakes") or {}).get("dominant_error_types"),
        }
    else:
        base["desk"] = {"summary": base["summary"], "lessons": learning.get("what_improved")}
    base["portfolio_office"] = report.get("portfolio_office")
    return {"institutional_memory": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "institutional_memory": {
            "enabled": True,
            "version": ILM_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "quality_gates_passed": quality_gates().get("passed"),
            "includes_mistake_intelligence": True,
            "rule": "No overwrite; versioned forecasts/decisions; accuracy/lessons/confidence evolution; MIE classifies mistakes",
        }
    }


def soft_slice_for_stack() -> dict[str, Any]:
    return soft_slice_for_irs()


def quality_gates() -> dict[str, Any]:
    out = analyse_company("HDFCBANK")
    theses = (out.get("thesis") or {}).get("theses") or []
    forecasts = (out.get("forecasts") or {}).get("forecasts") or []
    decisions = (out.get("committee") or {}).get("decisions") or []
    evidence = out.get("evidence") or {}
    confidence = out.get("confidence") or {}
    learning = out.get("learning") or {}
    mistakes = out.get("mistakes") or {}
    accuracy = out.get("accuracy") or {}
    thesis_gate = assert_append_only(theses)
    forecast_gate = assert_append_only(forecasts)
    committee_gate = assert_append_only(decisions)
    checks = {
        "enabled": is_enabled(),
        "company_found": bool(out.get("found")),
        "no_thesis_overwritten": bool((out.get("thesis") or {}).get("no_overwrite")) and thesis_gate.get("no_overwrite"),
        "every_forecast_versioned": bool((out.get("forecasts") or {}).get("every_forecast_versioned"))
        and forecast_gate.get("append_only"),
        "every_committee_decision_preserved": bool(committee_gate.get("append_only")) and len(decisions) >= 1,
        "accuracy_continuously_updated": bool(accuracy.get("continuously_updated"))
        and accuracy.get("forecast_accuracy") is not None,
        "lessons_generated_after_outcomes": bool(
            (learning.get("institutional_learning") or {}).get("lesson_count", 0) >= 1
        ),
        "historical_evidence_retained": bool(evidence.get("historical_evidence_retained")),
        "confidence_evolution_recorded": bool(confidence.get("confidence_evolution_recorded")),
        "mistake_intelligence_classifies_errors": bool(mistakes.get("mistake_count", 0) >= 1)
        and bool(mistakes.get("dominant_error_types")),
        "flags": flags_dict().get("INSTITUTIONAL_MEMORY") is True,
        "not_engine_redesign": bool(out.get("not_an_engine_redesign")),
        "active_learning_not_passive_archive": bool(out.get("active_learning")) and bool(out.get("not_passive_storage")),
    }
    return {"passed": all(checks.values()), "checks": checks, "ilm_version": ILM_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    sample = analyse_company("HDFCBANK")
    lessons = ((sample.get("learning") or {}).get("lessons") or [])[:5]
    lesson_rows = "".join(f"<li>{l.get('date')}: {l.get('lesson')}</li>" for l in lessons)
    mistakes = ((sample.get("mistakes") or {}).get("mistakes") or [])[:6]
    mist_rows = "".join(
        f"<tr><td>{m.get('error_type')}</td><td>{m.get('example')}</td><td>{m.get('lesson')}</td></tr>"
        for m in mistakes
    )
    theses = ((sample.get("thesis") or {}).get("evolution") or [])
    thesis_rows = "".join(
        f"<tr><td>{t.get('date')}</td><td>{t.get('stance')}</td><td>{t.get('confidence')}</td><td>{t.get('outcome')}</td></tr>"
        for t in theses
    )
    return f"""<!doctype html>
<html><head><title>ILM — Institutional Learning & Memory</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Institutional Learning & Memory Engine</h1>
<p>Primary question: <em>{PRIMARY_QUESTION}</em> — includes Mistake Intelligence (MIE).</p>
<div class="card">
  <div>Version: {dash.get('ilm_version')}</div>
  <div>Companies: {', '.join(dash.get('companies') or [])}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>HDFCBANK — thesis history</h2>
<table><thead><tr><th>Date</th><th>Stance</th><th>Confidence</th><th>Outcome</th></tr></thead>
<tbody>{thesis_rows}</tbody></table>
</div>
<div class="card"><h2>Lessons learned</h2><ul>{lesson_rows}</ul>
<p>{(sample.get('report') or {}).get('cio_brief')}</p></div>
<div class="card"><h2>Mistake Intelligence</h2>
<table><thead><tr><th>Type</th><th>Example</th><th>Lesson</th></tr></thead>
<tbody>{mist_rows}</tbody></table>
</div>
<p>API: /v1/ilm/* · Flag: INSTITUTIONAL_MEMORY · Active learning, not an archive</p>
</body></html>"""
