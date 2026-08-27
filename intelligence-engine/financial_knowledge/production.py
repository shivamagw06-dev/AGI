"""FKB-01 Mission Control / API façades."""

from __future__ import annotations

from typing import Any

from financial_knowledge.registry import knowledge
from financial_knowledge.schema import (
    ISSUES_RECOMMENDATIONS,
    PHASE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    v = knowledge.validate()
    return {
        "status": "ok" if v.get("ok") else "degraded",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "phase": PHASE,
        "role": "institutional_financial_knowledge_base",
        "performs_analysis": False,
        "is_llm": False,
        "is_parser": False,
        "is_warehouse": False,
        "read_only": True,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "validation": v,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    v = knowledge.validate()
    counts = v.get("counts") or {}
    return {
        "status": "ok" if v.get("ok") else "degraded",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "metrics_loaded": counts.get("metrics"),
        "ratios_loaded": counts.get("ratios"),
        "relationships_loaded": counts.get("relationships"),
        "thresholds_loaded": counts.get("thresholds"),
        "glossary_loaded": counts.get("glossary"),
        "sectors_loaded": counts.get("sectors"),
        "confidence_modifiers_loaded": counts.get("confidence_modifiers"),
        "validation_status": "passed" if v.get("ok") else "failed",
        "validation_errors": v.get("errors") or [],
        "issues_recommendations": False,
        "buy_sell": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def metrics() -> dict[str, Any]:
    rows = knowledge.list_metrics()
    return {"ok": True, "n": len(rows), "metrics": rows, "version": VERSION}


def ratios() -> dict[str, Any]:
    rows = knowledge.list_ratios()
    return {"ok": True, "n": len(rows), "ratios": rows, "version": VERSION}


def relationships() -> dict[str, Any]:
    rows = knowledge.list_relationships()
    return {"ok": True, "n": len(rows), "relationships": rows, "version": VERSION}


def glossary() -> dict[str, Any]:
    rows = knowledge.list_glossary()
    return {"ok": True, "n": len(rows), "glossary": rows, "version": VERSION}


def thresholds(*, sector: str | None = None) -> dict[str, Any]:
    if sector:
        rows = [knowledge.threshold(t["id"], sector=sector) for t in knowledge.list_thresholds()]
        rows = [r for r in rows if r]
    else:
        rows = knowledge.list_thresholds()
    return {"ok": True, "n": len(rows), "thresholds": rows, "sector": sector, "version": VERSION}


def soft_slice_mission_control() -> dict[str, Any]:
    d = dashboard()
    return {
        "status": d.get("status"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "metrics_loaded": d.get("metrics_loaded"),
        "ratios_loaded": d.get("ratios_loaded"),
        "relationships_loaded": d.get("relationships_loaded"),
        "thresholds_loaded": d.get("thresholds_loaded"),
        "validation_status": d.get("validation_status"),
        "issues_recommendations": False,
        "buy_sell": False,
    }


def admin_page() -> str:
    d = dashboard()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>FKB-01 Financial Knowledge Base</title>
<style>
body{{font-family:ui-sans-serif,system-ui;margin:2rem;background:#0b1220;color:#e5eefc}}
h1{{font-size:1.4rem}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;margin:1.5rem 0}}
.card{{background:#121a2b;border:1px solid #243047;border-radius:12px;padding:1rem}}
.muted{{color:#8aa0c0;font-size:.85rem}} .ok{{color:#4ade80}} .bad{{color:#fbbf24}}
</style></head><body>
<p class="muted">FKB-01 · Institutional Financial Knowledge Base · {d.get('version')}</p>
<h1>Canonical financial knowledge (read-only)</h1>
<p class="muted">Definitions only — no analysis, no BUY/SELL, no warehouse mutations.</p>
<div class="grid">
  <div class="card"><div class="muted">Metrics</div><div style="font-size:1.8rem">{d.get('metrics_loaded')}</div></div>
  <div class="card"><div class="muted">Ratios</div><div style="font-size:1.8rem">{d.get('ratios_loaded')}</div></div>
  <div class="card"><div class="muted">Relationships</div><div style="font-size:1.8rem">{d.get('relationships_loaded')}</div></div>
  <div class="card"><div class="muted">Thresholds</div><div style="font-size:1.8rem">{d.get('thresholds_loaded')}</div></div>
  <div class="card"><div class="muted">Glossary</div><div style="font-size:1.8rem">{d.get('glossary_loaded')}</div></div>
  <div class="card"><div class="muted">Validation</div><div class="{'ok' if d.get('validation_status')=='passed' else 'bad'}" style="font-size:1.2rem;margin-top:.5rem">{d.get('validation_status')}</div></div>
</div>
<p class="muted">APIs: /v1/knowledge/metrics · ratios · relationships · glossary · thresholds · health · dashboard</p>
</body></html>"""
