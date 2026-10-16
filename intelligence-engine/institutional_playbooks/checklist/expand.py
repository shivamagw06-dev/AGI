"""Expand playbook checklist into guided analytical steps for reasoning packs / ICE."""

from __future__ import annotations

from typing import Any


def expand_checklist(
    playbook: dict[str, Any],
    *,
    evidence_domains: list[str] | None = None,
) -> dict[str, Any]:
    """Mark checklist steps pending/covered based on soft evidence domain presence."""
    domains = {d.lower() for d in (evidence_domains or [])}
    steps_out = []
    covered = 0
    for step in playbook.get("checklist") or []:
        label = str(step.get("label") or "")
        status = "pending"
        # Soft coverage heuristic — does not invent facts
        tokens = [t for t in label.lower().replace("/", " ").split() if len(t) > 3]
        if domains and any(tok in " ".join(domains) or any(tok in d for d in domains) for tok in tokens[:3]):
            status = "evidence_hint"
            covered += 1
        steps_out.append(
            {
                "step_id": step.get("step_id"),
                "label": label,
                "required": bool(step.get("required", True)),
                "status": status,
            }
        )
    total = len(steps_out) or 1
    return {
        "playbook_id": playbook.get("playbook_id"),
        "steps": steps_out,
        "n_steps": len(steps_out),
        "n_evidence_hints": covered,
        "coverage_pct": int(round(100.0 * covered / total)),
        "incomplete": covered < total,
        "fabricated": False,
    }


def guided_procedure(playbook: dict[str, Any]) -> dict[str, Any]:
    """Ordered multi-step analytical procedure (guides reasoning, does not replace it)."""
    steps = list(playbook.get("procedure") or [])
    # Prefer procedure; fall back to checklist labels
    if not steps:
        steps = [str(s.get("label")) for s in (playbook.get("checklist") or [])]
    chain = []
    for i, label in enumerate(steps):
        chain.append(
            {
                "order": i + 1,
                "label": label,
                "is_conclusion": str(label).strip().lower() in {"conclusion", "ic recommendation"},
            }
        )
    return {
        "playbook_id": playbook.get("playbook_id"),
        "name": playbook.get("name"),
        "steps": chain,
        "n_steps": len(chain),
        "arrow_text": " → ".join(str(s) for s in steps),
        "guides_reasoning": True,
        "replaces_reasoning": False,
        "fabricated": False,
    }


def checklist_bullets(selection: dict[str, Any], *, max_items: int = 12) -> list[str]:
    """Render checklist / procedure as analysis bullets for ICE."""
    bullets: list[str] = []
    primary = selection.get("playbook_name") or (selection.get("primary") or {}).get("name")
    if primary:
        bullets.append(f"Analytical playbook: {primary}")
    proc = selection.get("procedure") or {}
    arrow = proc.get("arrow_text")
    if arrow:
        bullets.append(f"Procedure: {arrow}")
    steps = (selection.get("checklist") or {}).get("steps") or []
    for step in steps[:max_items]:
        mark = "□" if step.get("status") == "pending" else "▣"
        bullets.append(f"{mark} {step.get('label')}")
    mistakes = selection.get("common_mistakes") or []
    if mistakes:
        bullets.append(f"Common mistake to avoid: {mistakes[0]}")
    return bullets[: max_items + 3]
