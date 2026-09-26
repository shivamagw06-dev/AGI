"""Analog search: Evidence Graph + question → ranked historical memories."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.quality.gates import evaluate_memory_pack
from institutional_analog_intelligence.regime_memory.classify import classify_regimes
from institutional_analog_intelligence.registry.index import list_memories
from institutional_analog_intelligence.replay.filter import filter_memories
from institutional_analog_intelligence.schema import IMAI_VERSION, MODULE_CODE
from institutional_analog_intelligence.similarity.engine import score_similarity


def _entities_from_context(
    question: str,
    evidence_graph: dict[str, Any] | None,
    playbook: dict[str, Any] | None,
) -> list[str]:
    out: list[str] = []
    for e in (evidence_graph or {}).get("entities") or []:
        out.append(str(e))
    # Light ticker/entity cues from question
    low = (question or "").lower()
    for tok in ("hdfcbank", "icicibank", "infy", "tcs", "reliance", "asian paints", "titan", "sbin"):
        if tok in low:
            out.append(tok.replace(" ", "").upper() if " " not in tok else tok.title())
    if "private bank" in low or "banks" in low or "bank " in low:
        out.append("banks")
    if "rbi" in low:
        out.append("RBI")
    pb_ents = (playbook or {}).get("entities") or []
    for e in pb_ents:
        out.append(str(e))
    # Dedupe preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for e in out:
        key = e.upper()
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    return deduped


def _industries_from_context(
    question: str,
    evidence_graph: dict[str, Any] | None,
    playbook: dict[str, Any] | None,
) -> list[str]:
    out: list[str] = []
    low = (question or "").lower()
    mapping = [
        (("bank", "nbfc", "credit"), "banks"),
        (("it ", "infy", "tcs", "software"), "it_services"),
        (("oil", "crude", "energy"), "energy"),
        (("steel", "metal"), "metals"),
        (("cement",), "cement"),
        (("paint",), "paints"),
        (("jewellery", "titan"), "consumer"),
    ]
    for cues, ind in mapping:
        if any(c in low for c in cues):
            out.append(ind)
    cat = str((playbook or {}).get("category") or "").lower()
    if "bank" in cat:
        out.append("banks")
    for e in (evidence_graph or {}).get("entities") or []:
        el = str(e).lower()
        if "bank" in el:
            out.append("banks")
    return list(dict.fromkeys(out))


def _surface_bullets(memories: list[dict[str, Any]], *, max_items: int = 5) -> list[str]:
    out: list[str] = []
    for m in memories[:max_items]:
        period = m.get("time_period") or "?"
        sim = m.get("similarity_score")
        sim_s = f"{float(sim):.1f}" if isinstance(sim, (int, float)) else "n/a"
        out.append(
            f"{m.get('memory_id')}: {m.get('title')} ({period}; similarity {sim_s}/100; "
            f"confidence {m.get('confidence')}). Outcome: {m.get('outcome_summary')}"
        )
    return out


def _comparison_block(memories: list[dict[str, Any]]) -> dict[str, Any]:
    if not memories:
        return {
            "similarities": [],
            "differences": [],
            "known_outcomes": [],
            "confidence": None,
        }
    sims: list[str] = []
    for m in memories:
        for lesson in m.get("lessons_learned") or []:
            sims.append(str(lesson))
    diffs = [str(x) for m in memories for x in (m.get("limitations") or [])]
    outcomes = [str(m.get("outcome_summary")) for m in memories if m.get("outcome_summary")]
    confs = [float(m["confidence"]) for m in memories if isinstance(m.get("confidence"), (int, float))]
    return {
        "similarities": sims[:6],
        "differences": diffs[:6],
        "known_outcomes": outcomes[:6],
        "confidence": round(sum(confs) / len(confs), 3) if confs else None,
    }


def retrieve_memories(
    *,
    question: str,
    evidence_graph: dict[str, Any] | None = None,
    playbook: dict[str, Any] | None = None,
    as_of: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Soft-wire entry: find validated historical analogues ranked by similarity.

    Never fabricates analogues — only seeded memories with evidence_ids.
    """
    playbook_id = (playbook or {}).get("playbook_id")
    regimes = classify_regimes(
        question=question,
        evidence_graph=evidence_graph,
        playbook_id=playbook_id if isinstance(playbook_id, str) else None,
    )
    entities = _entities_from_context(question, evidence_graph, playbook)
    industries = _industries_from_context(question, evidence_graph, playbook)

    candidates, dropped = filter_memories(list_memories(), as_of=as_of)

    scored: list[dict[str, Any]] = []
    for raw in candidates:
        score, reasons = score_similarity(
            raw,
            question=question,
            entities=entities,
            industries=industries,
            regimes=regimes,
            playbook_id=playbook_id if isinstance(playbook_id, str) else None,
            evidence_graph=evidence_graph,
            as_of=as_of,
        )
        if score < 12.0:
            continue
        row = dict(raw)
        row["similarity_score"] = float(score)
        row["similarity_reasons"] = reasons
        scored.append(row)

    scored.sort(key=lambda m: (-float(m.get("similarity_score") or 0), m.get("memory_id") or ""))
    top = scored[: max(1, min(int(top_k), 12))] if scored else []

    pack = {
        "module": MODULE_CODE,
        "version": IMAI_VERSION,
        "imai_version": IMAI_VERSION,
        "status": "ok" if top else "no_analog_match",
        "question": question,
        "as_of": as_of,
        "regimes": regimes,
        "entities_used": entities,
        "industries_used": industries,
        "candidate_count": len(candidates),
        "dropped_future_count": len(dropped),
        "scored_count": len(scored),
        "memories": top,
        "top_memory_ids": [m.get("memory_id") for m in top],
        "surface_bullets": _surface_bullets(top),
        "comparison": _comparison_block(top),
        "have_we_seen_this_before": bool(top),
        "reasoning_changed": False,
        "knowledge_factory_changed": False,
        "governance_changed": False,
        "invented_analogues": False,
        "note": (
            "Institutional Memory & Analog Intelligence augments Evidence Graph with "
            "validated historical analogues. Memory never replaces reasoning."
        ),
    }
    pack["quality"] = evaluate_memory_pack(pack, as_of=as_of)
    if pack["quality"].get("status") == "fail":
        pack["status"] = "quality_fail"
    return pack
