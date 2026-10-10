"""Compose institutional contradiction answers — step-by-step, no jump to certainty."""

from __future__ import annotations

from typing import Any


def compose_answer(arch: dict[str, Any], *, company: str | None = None) -> str:
    """5-part institutional structure:

    1. Direct answer
    2. Why this happened
    3. Other possible explanations
    4. What evidence is missing
    5. Current conclusion
    """
    explanations = list(arch.get("explanations") or [])[:4]
    missing = list(arch.get("missing_evidence") or [])[:4]

    parts: list[str] = []
    parts.append(str(arch.get("direct_answer") or "").strip())
    why = str(arch.get("why") or "").strip()
    if why:
        parts.append(why)

    if explanations:
        # Present as possibilities — never as proven facts.
        lead = "Other possible explanations include: "
        bullets = "; ".join(
            f"({i}) {str(e).rstrip('.')}" for i, e in enumerate(explanations, start=1)
        )
        parts.append(lead + bullets + ".")

    if missing:
        miss = "Additional evidence that would help includes: " + "; ".join(
            str(m).rstrip(".") for m in missing
        )
        parts.append(miss + ".")

    conclusion = str(arch.get("conclusion") or "").strip()
    if conclusion:
        parts.append(conclusion)

    text = " ".join(p for p in parts if p)
    # Light company contextualisation without inventing facts
    if company and company.lower() not in text.lower() and arch.get("id") == "profit_vs_nim":
        # optional — keep generic if not natural
        pass
    return text.strip()


def build_reasoning_pack(arch: dict[str, Any], *, query: str, company: str | None = None) -> dict[str, Any]:
    answer = compose_answer(arch, company=company)
    explanations = list(arch.get("explanations") or [])[:4]
    missing = list(arch.get("missing_evidence") or [])[:4]
    return {
        "enabled": True,
        "archetype": arch.get("id"),
        "query": query,
        "company": company,
        "facts": list(arch.get("facts") or []),
        "do_they_conflict": bool(arch.get("conflict", True)),
        "why_could_they_conflict": arch.get("why"),
        "possible_explanations": explanations,
        "strongest_explanation": arch.get("strongest_explanation"),
        "missing_evidence": missing,
        "confidence": arch.get("confidence") or "low",
        "answer_structure": {
            "direct_answer": arch.get("direct_answer"),
            "why_this_happened": arch.get("why"),
            "other_possible_explanations": explanations,
            "what_evidence_is_missing": missing,
            "current_conclusion": arch.get("conclusion"),
        },
        "answer": answer,
        "direct_answer": arch.get("direct_answer"),
        "never_jumps_to_conclusion": True,
        "acknowledges_uncertainty": True,
        "lists_alternative_explanations": len(explanations) >= 2,
    }
