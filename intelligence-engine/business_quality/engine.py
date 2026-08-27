"""FIRE-06 orchestration — pillar-primary synthesis."""

from __future__ import annotations

from typing import Any

from business_quality.inventory import load_quality_inputs
from business_quality.metrics_util import signals_for
from business_quality.pillars import score_all_pillars
from business_quality.schema import PILLARS, PILLAR_TITLES, VERSION, WORKSTREAM_ID
from business_quality.scoring import assert_language_safe, derive_overall, strengths_weaknesses
from business_quality.weights import load_pillar_weights

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def confidence_board(pillars: dict[str, dict[str, Any]]) -> dict[str, Any]:
    dist = {"High": 0, "Medium": 0, "Low": 0}
    for p in pillars.values():
        c = p.get("confidence") or "Low"
        dist[c] = dist.get(c, 0) + 1
    scored = [p for p in pillars.values() if p.get("score") is not None]
    return {
        "confidence_distribution": dist,
        "pillars_scored": len(scored),
        "pillars_total": len(pillars),
        "evidence_coverage": {
            "pillars_with_evidence": sum(1 for p in pillars.values() if p.get("evidence")),
        },
    }


def build_quality_pack(ticker: str, **kwargs: Any) -> dict[str, Any]:
    inv = load_quality_inputs(ticker, **kwargs)
    series = inv.get("series") or {}
    signals = signals_for(series)
    pillars = score_all_pillars(
        series_map=series,
        signals=signals,
        fire01=inv.get("fire01_findings") or [],
        fire03=inv.get("fire03_facts") or [],
        fire04=inv.get("fire04_findings") or [],
        fire05_score=inv.get("fire05_score"),
        fire05_findings=inv.get("fire05_findings"),
        coverage_pct=inv.get("coverage_pct"),
    )
    weight_pack = load_pillar_weights()
    overall = derive_overall(pillars, weight_pack=weight_pack)
    sw = strengths_weaknesses(pillars)
    conf = confidence_board(pillars)

    findings = [pillars[pid] for pid in PILLARS if pid in pillars]
    lang_hits = assert_language_safe([f.get("narrative") or "" for f in findings])

    pillar_scores = {
        pid: {"title": PILLAR_TITLES.get(pid), "score": (pillars.get(pid) or {}).get("score")}
        for pid in PILLARS
    }

    mc = {
        "quality_score": overall.get("overall_score"),
        "pillar_scores": {pid: pillar_scores[pid]["score"] for pid in PILLARS},
        "confidence": conf.get("confidence_distribution"),
        "evidence_coverage": conf.get("evidence_coverage"),
        "score_trend": None,  # reserved — requires historical BQE snapshots
        "pillars_primary": True,
    }

    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": inv.get("ticker"),
        "pillars": pillars,
        "pillar_scores": pillar_scores,
        "findings": findings,
        "overall": overall,
        "quality_score": overall.get("overall_score"),
        "strengths": sw["strengths"],
        "weaknesses": sw["weaknesses"],
        "confidence": conf,
        "mission_control": mc,
        "weights": weight_pack,
        "language_guard_violations": lang_hits,
        "inputs": {
            "fire01_n": len(inv.get("fire01_findings") or []),
            "fire02_n": len(inv.get("fire02_relationships") or []),
            "fire03_n": len(inv.get("fire03_facts") or []),
            "fire04_n": len(inv.get("fire04_findings") or []),
            "fire05_objectives_n": (inv.get("fire05_score") or {}).get("objectives_tracked"),
            "coverage_pct": inv.get("coverage_pct"),
            "notes": inv.get("notes") or [],
            "metrics_with_series": sorted(k for k, v in series.items() if v),
        },
        "read_only": True,
        "uses_llm": False,
        "buy_sell": False,
        "valuation": False,
        "forecast": False,
        "issues_recommendations": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
        "fire_05_unchanged": True,
        "as_of": now_iso(),
    }
