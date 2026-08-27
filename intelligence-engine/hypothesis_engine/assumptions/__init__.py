"""Assumptions engine — known / unknown / weak / evidence gaps per hypothesis."""

from __future__ import annotations

from typing import Any


def enrich_assumptions(
    hypotheses: list[dict[str, Any]],
    *,
    entity: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ctx = context or {}
    ent = entity or {}
    regime = ctx.get("market_regime") or "unspecified regime"
    out = []
    for h in hypotheses:
        base = dict(h.get("assumptions") or {})
        known = list(base.get("known") or [])
        unknown = list(base.get("unknown") or [])
        weak = list(base.get("weak") or [])
        gaps = list(base.get("evidence_gaps") or [])

        if ent.get("ticker") or ent.get("canonical_name"):
            known.append(f"Canonical entity resolved ({ent.get('ticker') or ent.get('canonical_name')})")
        known.append(f"Market regime context treated as: {regime}")

        for ev in h.get("required_evidence") or []:
            gaps.append(f"Pending verification: {ev}")

        if float(h.get("confidence") or 0) < 0.65:
            weak.append("Initial confidence below institutional comfort band")

        # dedupe
        def _dedupe(xs: list[str]) -> list[str]:
            seen = set()
            res = []
            for x in xs:
                if x not in seen:
                    seen.add(x)
                    res.append(x)
            return res

        out.append(
            {
                **h,
                "assumptions": {
                    "known": _dedupe(known),
                    "unknown": _dedupe(unknown),
                    "weak": _dedupe(weak),
                    "evidence_gaps": _dedupe(gaps),
                },
            }
        )
    return out
