"""Deterministic Why Now narrative — evidence-backed, company-specific."""

from __future__ import annotations

from typing import Any

from opportunity_intelligence.util import as_float


def build_why_now(
    *,
    entity: str,
    dimensions: dict[str, Any],
    blockers: list[dict[str, Any]],
    catalysts: list[dict[str, Any]],
    delta: dict[str, Any] | None,
    score: float,
    priority: str,
) -> str:
    parts: list[str] = []

    val = dimensions.get("valuation") or {}
    fin = dimensions.get("financial_momentum") or {}
    own = dimensions.get("ownership_momentum") or {}
    sect = dimensions.get("sector_momentum") or {}
    corp = dimensions.get("corporate_momentum") or {}

    val_s = as_float(val.get("score")) or 50
    fin_s = as_float(fin.get("score")) or 50
    own_s = as_float(own.get("score")) or 50

    if val_s >= 60:
        sig = (val.get("signals") or ["Valuation supportive"])[0]
        parts.append(f"Valuation backdrop is constructive ({sig})")
    elif val_s < 40:
        sig = (val.get("signals") or ["Valuation rich"])[0]
        parts.append(f"Valuation is less supportive ({sig})")

    if fin_s >= 60:
        sig = (fin.get("signals") or ["Financial momentum improving"])[0]
        parts.append(f"fundamentals show momentum ({sig})")
    elif fin_s < 40:
        sig = (fin.get("signals") or ["Financial momentum soft"])[0]
        parts.append(f"operating momentum is mixed ({sig})")

    if own_s >= 60:
        sig = (own.get("signals") or ["Ownership improving"])[0]
        parts.append(f"ownership flows are supportive ({sig})")

    if (sect.get("score") or 50) >= 58 and (sect.get("signals") or []):
        parts.append(f"sector/theme context: {sect['signals'][0]}")

    if (corp.get("score") or 50) >= 58 and (corp.get("signals") or []):
        parts.append(f"corporate developments: {corp['signals'][0]}")

    if catalysts:
        high = [c["name"] for c in catalysts if c.get("importance") == "High"]
        names = high or [c["name"] for c in catalysts[:2]]
        parts.append(f"near-term catalysts include {', '.join(names[:3])}")

    if isinstance(delta, dict) and delta.get("status") and delta.get("status") != "UNCHANGED":
        summary = str(delta.get("summary") or "material memory changes")[:160]
        parts.append(f"Knowledge Delta flags change ({summary})")

    if blockers:
        parts.append(
            f"research blockers to weigh: {', '.join(b.get('title') for b in blockers[:2])}"
        )

    if not parts:
        return (
            f"{entity} currently screens as {priority} research priority "
            f"(opportunity score {score:.0f}) with limited differentiated catalysts in compiled memory."
        )

    # Deterministic sentence assembly
    lead = parts[0][0].upper() + parts[0][1:]
    mid = "; ".join(parts[1:])
    tail = f" Overall research priority is {priority} (score {score:.0f})."
    if mid:
        return f"{lead}; {mid}.{tail}"
    return f"{lead}.{tail}"


def strengths_from_dimensions(dimensions: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key, dim in dimensions.items():
        sc = as_float(dim.get("score"))
        if sc is not None and sc >= 60:
            for s in (dim.get("signals") or [])[:2]:
                out.append(s)
            if not dim.get("signals"):
                out.append(f"{key.replace('_', ' ').title()} supportive ({sc:.0f})")
    # Stable unique
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq[:10]
