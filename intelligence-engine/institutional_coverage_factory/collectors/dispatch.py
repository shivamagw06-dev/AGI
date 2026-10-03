"""Dispatch missing collectors for a company, then KIL integrate + rescore."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from institutional_coverage_factory.config import load_config
from institutional_coverage_factory.schema import EVIDENCE_CLASSES

COLLECTOR_IDS = (
    "annual_reports",
    "quarterly_results",
    "investor_presentations",
    "transcripts",
    "shareholding",
    "corporate_actions",
    "guidance",
    "segment_data",
)

_COLLECTOR_IMPORTS = {
    "annual_reports": "institutional_coverage_factory.collectors.annual_reports",
    "quarterly_results": "institutional_coverage_factory.collectors.quarterly_results",
    "investor_presentations": "institutional_coverage_factory.collectors.investor_presentations",
    "transcripts": "institutional_coverage_factory.collectors.transcripts",
    "shareholding": "institutional_coverage_factory.collectors.shareholding",
    "corporate_actions": "institutional_coverage_factory.collectors.corporate_actions",
    "guidance": "institutional_coverage_factory.collectors.guidance",
    "segment_data": "institutional_coverage_factory.collectors.segment_data",
}


def run_collector(collector_id: str, ticker: str) -> Dict[str, Any]:
    import importlib

    mod_name = _COLLECTOR_IMPORTS.get(collector_id)
    if not mod_name:
        return {"ok": False, "collector": collector_id, "error": "unknown_collector"}
    mod = importlib.import_module(mod_name)
    return mod.collect(ticker)


def collectors_for_missing(missing_classes: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for class_id in missing_classes:
        meta = EVIDENCE_CLASSES.get(class_id) or {}
        cid = meta.get("collector")
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def dispatch_collectors(
    ticker: str,
    *,
    missing_classes: Optional[List[str]] = None,
    integrate: bool = True,
) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    cfg = load_config()
    missing = list(missing_classes or [])
    if not missing:
        from institutional_coverage_factory.scorer.score import score_evidence_classes

        missing = list(score_evidence_classes(t).get("missing_classes") or [])

    planned = collectors_for_missing(missing)
    # Cap parallel collectors per company
    max_n = int(cfg.get("max_parallel_collectors") or 20)
    planned = planned[:max_n]

    results: List[Dict[str, Any]] = []
    for cid in planned:
        try:
            results.append(run_collector(cid, t))
        except Exception as exc:
            results.append({"ok": False, "collector": cid, "ticker": t, "error": str(exc)[:200]})

    kil_out = None
    if integrate:
        try:
            from institutional_evidence.integration.layer import integrate_company

            kil_out = integrate_company(t, trigger_repair=True)
        except Exception as exc:
            kil_out = {"ok": False, "error": str(exc)[:200]}

    from institutional_coverage_factory.scorer.score import score_evidence_classes
    from institutional_coverage_factory.validator.icc import evaluate_icc

    score = score_evidence_classes(t)
    icc = evaluate_icc(t, score=score, kil=kil_out if isinstance(kil_out, dict) else None)

    return {
        "ok": True,
        "ticker": t,
        "missing_before": missing,
        "collectors_planned": planned,
        "collector_results": results,
        "collectors_ok": sum(1 for r in results if r.get("ok")),
        "collectors_failed": sum(1 for r in results if not r.get("ok")),
        "kil": {
            "ok": bool((kil_out or {}).get("ok", True)) if kil_out else None,
            "coverage_state": ((kil_out or {}).get("coverage_state") or {}).get("coverage_state")
            if isinstance(kil_out, dict)
            else None,
            "period_count": (kil_out or {}).get("period_count") if isinstance(kil_out, dict) else None,
        },
        "score": score,
        "icc": icc,
    }
