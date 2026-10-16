"""Risk communication from gaps / disagreements — no invention."""

from __future__ import annotations

from typing import Any

from institutional_communication.styles.institutional import bullet, clean_line


def render_risk_section(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    risk = institutional_answer.get("risk_signals") or {}
    sections = institutional_answer.get("sections") or {}
    risk_bullets = list((sections.get("risks") or {}).get("bullets") or [])
    lines: list[str] = []

    missing = risk.get("missing_domains") or []
    if missing:
        lines.append(bullet(f"Missing evidence domains: {', '.join(map(str, missing))}"))
    softened = risk.get("softened_domains") or []
    if softened:
        lines.append(bullet(f"Softened requirements (alternates present): {', '.join(map(str, softened))}"))
    if risk.get("confidence_penalty"):
        lines.append(bullet(f"Confidence penalty from gaps: {risk.get('confidence_penalty')}"))
    if risk.get("tell_reasoning"):
        lines.append(bullet(clean_line(str(risk.get("tell_reasoning")), max_len=240)))

    for d in risk.get("disagreements") or []:
        lines.append(bullet(f"Alternative interpretation / disagreement: {clean_line(str(d), max_len=200)}"))

    for b in risk_bullets[:6]:
        lb = clean_line(str(b), max_len=220)
        if lb and lb.lower() not in {"no explicit risk-domain evidence retrieved"}:
            lines.append(bullet(lb))

    # Always surface unknowns when thin
    if not missing and not lines:
        lines.append(bullet("No explicit gap penalties recorded; residual uncertainty remains."))
    lines.append(bullet("Unknowns: any conclusion beyond retrieved evidence IDs is unsupported."))

    return {
        "section": "risks",
        "title": "Risks",
        "bullets": lines,
        "visible": True,
    }
