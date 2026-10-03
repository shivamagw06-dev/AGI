"""Thesis builder — compose the single institutional core thesis statement."""

from __future__ import annotations

from typing import Any


def _entity_label(payload: dict[str, Any], question: str) -> str:
    ere = payload.get("entity_resolution")
    if isinstance(ere, dict):
        body = ere.get("entity_resolution") if isinstance(ere.get("entity_resolution"), dict) else ere
        primary = body.get("primary_entity") if isinstance(body.get("primary_entity"), dict) else {}
        name = str(
            (primary or {}).get("canonical_name")
            or (primary or {}).get("name")
            or body.get("canonical_name")
            or body.get("name")
            or ""
        ).strip()
        if name:
            return name
    q = (question or "").strip()
    for prefix in ("Should I buy ", "Should I sell ", "What are the risks in ", "Analyse ", "Analyze "):
        if q.startswith(prefix):
            return q[len(prefix) :].rstrip("?").strip() or "The subject"
    if "nifty" in q.lower():
        return "Nifty IT" if " it" in q.lower() else "The index"
    return "The subject"


def _strength_phrase(pillar: dict[str, Any]) -> str:
    name = pillar["pillar"].lower()
    verdict = pillar.get("verdict")
    if verdict == "Strong":
        return f"strong {name}"
    if verdict == "Constructive":
        return f"constructive {name}"
    if verdict == "Weak":
        return f"weak {name}"
    return f"neutral {name}"


def build_core_thesis(
    *,
    question: str,
    payload: dict[str, Any],
    pillars: list[dict[str, Any]],
    conviction: dict[str, Any],
    contradictions: dict[str, Any],
) -> dict[str, Any]:
    entity = _entity_label(payload, question)
    ranked = sorted(pillars, key=lambda p: -float(p["strength"]))
    strong = [p for p in ranked if p.get("verdict") in ("Strong", "Constructive")][:3]
    weak = [p for p in ranked if p.get("verdict") == "Weak"][:2]

    strengths = ", ".join(_strength_phrase(p) for p in strong) or "mixed fundamental signals"
    overall = float(conviction.get("overall") or 0.5)

    if overall >= 0.68:
        stance = f"{entity} remains a structurally superior candidate"
    elif overall >= 0.55:
        stance = f"{entity} remains a constructive but not unqualified candidate"
    elif overall >= 0.45:
        stance = f"{entity} presents a balanced case with no decisive edge"
    else:
        stance = f"{entity} does not currently support a positive institutional case"

    caveat = ""
    if weak:
        caveat = f", although {', '.join(_strength_phrase(p) for p in weak)} constrains the case"
    elif contradictions.get("strongest_contradicting_evidence"):
        top = contradictions["strongest_contradicting_evidence"][0]
        caveat = f", although evidence that {str(top.get('text'))[:90].lower()} narrows the margin of safety"

    statement = f"{stance} on the basis of {strengths}{caveat}."

    return {
        "statement": statement,
        "entity": entity,
        "stance_conviction": round(overall, 4),
        "leading_pillars": [p["pillar"] for p in strong],
        "constraining_pillars": [p["pillar"] for p in weak],
        "single_sentence": True,
    }


def build_thesis_breaking_conditions(
    pillars: list[dict[str, Any]],
    contradictions: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ranked = sorted(pillars, key=lambda p: -float(p["strength"]))
    for p in ranked[:2]:
        out.append(
            {
                "condition": f"{p['pillar']} strength falls below 45% on verified evidence",
                "pillar": p["pillar"],
                "current_strength_pct": p["strength_pct"],
                "monitoring_evidence": [e.get("text") for e in (p.get("evidence") or [])[:2]],
                "severity": "Thesis breaking",
            }
        )
    top_challenge = (contradictions.get("strongest_contradicting_evidence") or [{}])[0]
    if top_challenge.get("text"):
        out.append(
            {
                "condition": f"Confirmation that {str(top_challenge['text'])[:120]}",
                "pillar": None,
                "severity": "Thesis breaking",
                "monitoring_evidence": [top_challenge.get("text")],
            }
        )
    return out[:4]
