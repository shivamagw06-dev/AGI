"""Investment narrative variants: one sentence, paragraph and one-page brief."""

from __future__ import annotations

from typing import Any


def build_narratives(
    core_thesis: dict[str, Any],
    pillars: list[dict[str, Any]],
    contradictions: dict[str, Any],
    catalysts: list[dict[str, Any]],
    conviction: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    sentence = str(core_thesis.get("statement") or "")
    ranked = sorted(pillars, key=lambda p: -float(p.get("strength") or 0))
    leaders = ranked[:3]
    top_support = (contradictions.get("strongest_supporting_evidence") or [{}])[0].get(
        "text"
    )
    top_challenge = (
        contradictions.get("strongest_contradicting_evidence") or [{}]
    )[0].get("text")
    top_catalysts = [c.get("event") for c in catalysts[:3]]

    paragraph = (
        f"{sentence} The thesis is led by "
        + ", ".join(
            f"{p['pillar']} ({p['strength_pct']}%)" for p in leaders
        )
        + f". Overall conviction is {conviction.get('overall_pct')}% and the thesis state is {status}. "
        + (
            f"The strongest support is {top_support}. " if top_support else ""
        )
        + (
            f"The principal challenge is {top_challenge}. " if top_challenge else ""
        )
        + (
            f"Key catalyst windows are {', '.join(top_catalysts)}."
            if top_catalysts
            else ""
        )
    )
    one_page = {
        "headline": sentence,
        "investment_case": paragraph,
        "pillar_case": [
            {
                "pillar": p["pillar"],
                "verdict": p.get("verdict"),
                "strength_pct": p.get("strength_pct"),
                "key_evidence": [e.get("text") for e in (p.get("evidence") or [])[:2]],
            }
            for p in ranked
        ],
        "principal_contradictions": [
            c.get("text") for c in (contradictions.get("major") or [])[:4]
        ],
        "catalyst_windows": [
            {
                "event": c.get("event"),
                "polarity": c.get("polarity"),
                "timing": c.get("expected_timing"),
                "probability_pct": c.get("probability_pct"),
            }
            for c in catalysts[:6]
        ],
        "committee_question": "Does the integrated evidence justify retaining this thesis under consideration?",
    }
    return {
        "one_sentence": sentence,
        "one_paragraph": paragraph,
        "one_page": one_page,
        "formats": ["one_sentence", "one_paragraph", "one_page"],
    }
