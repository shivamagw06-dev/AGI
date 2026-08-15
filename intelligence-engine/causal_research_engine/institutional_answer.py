"""Deterministic client-answer sections from governed CRE outputs."""
from __future__ import annotations
import re
from typing import Any

_NUMBER = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?\s*(?:%|bps|crore|cr|x)?", re.I)

def _label(value: Any) -> str:
    return str(value or "").replace("_", " ").strip()

def _paths(chains: list[dict[str, Any]], entity: str, *, max_depth: int = 4) -> list[list[dict[str, Any]]]:
    outgoing: dict[str, list[dict[str, Any]]] = {}
    incoming: dict[str, list[dict[str, Any]]] = {}
    for row in chains:
        outgoing.setdefault(str(row.get("cause")), []).append(row)
        incoming.setdefault(str(row.get("effect")), []).append(row)
    targets = {entity, entity.upper()}
    results: list[list[dict[str, Any]]] = []
    # Company questions need upstream paths ending at the company. Macro/driver
    # questions need downstream paths beginning at the driver.
    if any(str(row.get("effect")) in targets for row in chains):
        def walk_back(node: str, path: list[dict[str, Any]], seen: set[str]) -> None:
            parents = incoming.get(node) or []
            if not parents or len(path) >= max_depth:
                if path: results.append(list(reversed(path)))
                return
            for row in parents:
                cause = str(row.get("cause"))
                if cause in seen: continue
                walk_back(cause, path + [row], seen | {cause})
        walk_back(entity.upper(), [], {entity.upper()})
    else:
        def walk_forward(node: str, path: list[dict[str, Any]], seen: set[str]) -> None:
            children = outgoing.get(node) or []
            if not children or len(path) >= max_depth:
                if path: results.append(path)
                return
            for row in children:
                effect = str(row.get("effect"))
                if effect in seen: continue
                walk_forward(effect, path + [row], seen | {effect})
        walk_forward(entity, [], {entity})
    return sorted(results, key=lambda path: (-len(path), -sum(float(x.get("confidence") or 0) for x in path)))

def _path_text(path: list[dict[str, Any]]) -> str:
    if not path: return ""
    parts = [_label(path[0].get("cause"))]
    for row in path:
        arrow = "↓" if row.get("direction") == "NEGATIVE" else "↑" if row.get("direction") == "POSITIVE" else "→"
        parts.append(f"{arrow} {_label(row.get('effect'))}")
    return " ".join(parts)

def compose_cre_sections(*, question: str, causal_pack: dict[str, Any], evidence_text: str = "") -> dict[str, Any]:
    chains = [x for x in (causal_pack.get("chains") or []) if isinstance(x, dict)]
    contradictions = [x for x in (causal_pack.get("contradictions") or []) if isinstance(x, dict)]
    asserted = {re.sub(r"[\s,]", "", x.group(0)).lower() for x in _NUMBER.finditer(question or "")}
    supported = {re.sub(r"[\s,]", "", x.group(0)).lower() for x in _NUMBER.finditer(evidence_text or "")}
    hypothetical = bool(re.search(r"\b(what (?:happens|would happen) if|if|assume|scenario)\b", question or "", re.I))
    unsupported = [] if hypothetical else sorted(asserted - supported)
    if not chains:
        return {
            "direct_conclusion": ["Insufficient governed causal evidence to determine this reliably."],
            "evidence_gaps": ["No validated company-specific causal pathway was retrieved."],
            "confidence": "LOW", "premise_challenge": unsupported,
        }
    entity = str(causal_pack.get("entity") or "")
    strongest = sorted(chains, key=lambda x: float(x.get("confidence") or 0), reverse=True)[:8]
    assembled_paths = _paths(chains, entity)
    pathways = [_path_text(path) for path in assembled_paths[:6]] or [
        f"{_label(x.get('cause'))} -> {_label(x.get('effect'))}: {_label(x.get('mechanism'))}" for x in strongest[:5]
    ]
    counters = []
    for row in strongest:
        for counter in row.get("counter_effects") or []:
            if isinstance(counter, dict):
                counters.append(f"{_label(counter.get('effect'))}: {_label(counter.get('mechanism'))}")
    monitoring = list(dict.fromkeys(
        _label(node)
        for path in assembled_paths[:6]
        for row in path
        for node in (row.get("cause"), row.get("effect"))
        if node and str(node).upper() != entity.upper() and not str(node).startswith("sector_")
    )) or list(dict.fromkeys(_label(x.get("effect")) for x in strongest if x.get("effect")))
    avg_confidence = sum(float(x.get("confidence") or 0) for x in strongest) / len(strongest)
    band = "HIGH" if avg_confidence >= .75 and not contradictions else "MEDIUM" if avg_confidence >= .5 else "LOW"
    q = (question or "").lower()
    if any(term in q for term in ("not attractive", "invalidate", "go wrong", "risk")):
        conclusion = f"The thesis would weaken if the key pathway reverses or fails: {pathways[0]}"
    elif any(term in q for term in ("improve", "more attractive", "strengthen")):
        conclusion = f"The thesis improves when this pathway is confirmed: {pathways[0]}"
    elif "market" in q and any(term in q for term in ("assuming", "pricing", "priced")):
        conclusion = "The causal graph alone cannot establish what the market is pricing in; valuation-implied assumptions are required."
    else:
        conclusion = f"The most relevant governed pathway is {pathways[0]}"
    if unsupported:
        conclusion = f"The question contains an unverified numeric premise ({', '.join(unsupported)}). " + conclusion
    return {
        "direct_conclusion": [conclusion],
        "why": pathways[:3],
        "financial_transmission": pathways,
        "bull_case": [x for x in pathways if any(k in x.lower() for k in ("revenue", "margin", "roe", "cash flow", "multiple"))][:3],
        "bear_case": counters[:3] or ["The pathway may fail if its stated conditions or time lag do not hold."],
        "market_may_be_missing": ["Evidence is not sufficient to assert a market expectation without valuation-implied assumptions."],
        "what_changes_view": counters[:3] or ["New evidence that contradicts the strongest causal mechanism."],
        "monitoring": monitoring[:8],
        "evidence_gaps": ["Unresolved causal contradictions remain."] if contradictions else [],
        "confidence": band, "premise_challenge": unsupported,
        "execution_eligible": False, "generated_by": "AGI_CRE_DETERMINISTIC",
    }
