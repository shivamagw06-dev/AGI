"""Research continuity / change detection vs prior AGI house view."""

from __future__ import annotations

from typing import Any

from app.rsp.models import ChangeDetection, EvidenceStatement


def detect_changes(
    *,
    house_view: dict[str, Any] | None,
    evidence: list[EvidenceStatement],
    kip_context: dict[str, Any] | None,
) -> ChangeDetection:
    changed: list[str] = []
    same: list[str] = []
    invalidated: list[str] = []
    strengthens: list[str] = []
    weakens: list[str] = []

    if house_view:
        changed.extend(list(house_view.get("what_changed") or [])[:10])
        same.extend(list(house_view.get("what_remained_correct") or [])[:10])
        invalidated.extend(list(house_view.get("failed_assumptions") or [])[:10])
        for c in house_view.get("catalysts_occurred") or []:
            strengthens.append(f"Catalyst occurred: {c}")
        for line in house_view.get("thesis_evolution") or []:
            if "→" in str(line):
                changed.append(str(line))

    kip_changes = (kip_context or {}).get("what_changed_since_last_report") or []
    for c in kip_changes:
        if str(c) not in changed:
            changed.append(str(c))

    for e in evidence:
        t = e.statement.lower()
        if e.house_view_alignment == "aligned" and e.score >= 0.55:
            strengthens.append(e.statement[:240])
        if e.house_view_alignment == "contrary":
            weakens.append(e.statement[:240])
        if any(w in t for w in ("invalidate", "broke", "failed assumption", "thesis broken")):
            invalidated.append(e.statement[:240])
        if any(w in t for w in ("unchanged", "intact", "remains", "stable thesis")):
            same.append(e.statement[:240])

    # Engine-driven weaken/strengthen hints via source tags already in evidence
    return ChangeDetection(
        what_changed=_uniq(changed)[:15],
        what_stayed_the_same=_uniq(same)[:15],
        invalidated_previous_research=_uniq(invalidated)[:15],
        strengthens_thesis=_uniq(strengthens)[:15],
        weakens_thesis=_uniq(weakens)[:15],
    )


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for i in items:
        k = i.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(i.strip())
    return out
