"""AIP-08 House View evolution tracking (replay L4 shadow labels)."""

from __future__ import annotations

from app.aip.models import HouseViewEvolution, HouseViewEvolutionPoint
from app.validation.models import ReplayDaySlice


def track_house_view_evolution(
    ticker: str,
    days: list[ReplayDaySlice],
) -> HouseViewEvolution:
    sym = ticker.upper()
    points: list[HouseViewEvolutionPoint] = []
    prior: str | None = None
    changes = 0
    for day in sorted(days, key=lambda d: d.as_of):
        if sym not in day.l4_scores:
            continue
        label = day.l4_labels.get(sym, "Neutral")
        score = float(day.l4_scores[sym])
        conf = float(day.confidences.get(sym, 0.5))
        changed = prior is not None and label != prior
        if changed:
            changes += 1
        points.append(
            HouseViewEvolutionPoint(
                as_of=day.as_of,
                label=label,
                score=score,
                confidence=conf,
                changed=changed,
                prior_label=prior,
            )
        )
        prior = label
    return HouseViewEvolution(
        ticker=sym,
        points=points,
        n_changes=changes,
        source="replay_l4_shadow",
    )
