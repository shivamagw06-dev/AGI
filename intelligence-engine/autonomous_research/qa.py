"""P6.9 Institutional QA — block incomplete / non-reproducible reports."""

from __future__ import annotations

from typing import Any

from autonomous_research.schema import QA_CHECKS
from autonomous_research.util import as_float


def run_qa(
    draft: dict[str, Any],
    *,
    company_pack: dict[str, Any] | None = None,
    min_confidence: float = 40.0,
) -> dict[str, Any]:
    checks = []
    pack = company_pack or {}
    mem = pack.get("memory") if isinstance(pack.get("memory"), dict) else {}
    graph = pack.get("knowledge_graph") if isinstance(pack.get("knowledge_graph"), dict) else {}

    # Evidence completeness
    sections = draft.get("sections") or []
    backed = sum(1 for s in sections if s.get("evidence_backed"))
    evidence_ok = bool(sections) and backed >= max(3, len(sections) // 2)
    checks.append(_check("evidence_completeness", evidence_ok, f"{backed}/{len(sections)} sections evidence-backed"))

    mem_ver = draft.get("memory_version") or mem.get("memory_version")
    checks.append(_check("company_memory_version", mem_ver is not None, f"memory_version={mem_ver}"))

    delta_present = draft.get("delta_status") is not None or bool((pack.get("memory_delta")))
    checks.append(_check("knowledge_delta_version", delta_present, f"delta_status={draft.get('delta_status')}"))

    graph_ok = bool(graph.get("n_nodes")) or any(s.get("id") == "graph_context" and s.get("evidence") for s in sections)
    checks.append(_check("graph_consistency", graph_ok, f"graph_nodes={graph.get('n_nodes')}"))

    citations = draft.get("citations") or []
    checks.append(_check("citation_availability", len(citations) >= 3, f"citations={len(citations)}"))

    # Deterministic replay proxy: draft ok + memory version + no BUY/SELL language
    blob = str(draft).upper()
    no_rec = "BUY " not in blob and "SELL " not in blob and not draft.get("issues_recommendations")
    replay_ok = bool(draft.get("ok")) and mem_ver is not None and no_rec
    checks.append(_check("deterministic_replay", replay_ok, "draft+memory_version+no_recommendation_language"))

    conf = as_float(draft.get("confidence"))
    # confidence may be 0-1 or 0-100
    if conf is not None and conf <= 1.0:
        conf = conf * 100.0
    conf_ok = conf is None or conf >= min_confidence
    checks.append(_check("confidence_threshold", conf_ok, f"confidence={conf}, min={min_confidence}"))

    passed = all(c["pass"] for c in checks)
    return {
        "approved": False,  # QA pass ≠ governance approval
        "qa_pass": passed,
        "blocked": not passed,
        "checks": checks,
        "check_ids": list(QA_CHECKS),
        "failures": [c for c in checks if not c["pass"]],
        "governance_status": "qa_passed_pending_approval" if passed else "qa_rejected",
        "issues_recommendations": False,
    }


def qa_batch(
    drafts: list[dict[str, Any]],
    company_packs: list[dict[str, Any]],
) -> dict[str, Any]:
    by_entity = {p.get("entity"): p for p in company_packs}
    results = []
    for d in drafts:
        p = by_entity.get(d.get("entity"))
        results.append({"company": d.get("company"), "entity": d.get("entity"), "qa": run_qa(d, company_pack=p)})
    return {
        "n": len(results),
        "passed_n": sum(1 for r in results if r["qa"].get("qa_pass")),
        "blocked_n": sum(1 for r in results if r["qa"].get("blocked")),
        "results": results,
    }


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"id": name, "pass": bool(ok), "detail": detail}
