"""Portfolio concentration diagnostics."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_portfolio.portfolio_entities import HoldingRecord, RiskRecord
from institutional_portfolio.exposures import exposures_by_dimension
from institutional_portfolio.portfolio_entities import ExposureRecord


def compute_concentration(holdings: Sequence[HoldingRecord]) -> dict[str, Any]:
    ordered = sorted(holdings, key=lambda h: float(h.weight or 0.0), reverse=True)
    weights = [float(h.weight or 0.0) for h in ordered]
    hhi = sum(w * w for w in weights)
    largest = ordered[0] if ordered else None
    return {
        "number_of_holdings": len(ordered),
        "largest_position": largest.to_dict() if largest else None,
        "top_5_weight": sum(weights[:5]),
        "top_10_weight": sum(weights[:10]),
        "hhi": round(hhi, 6),
        "effective_n": round(1.0 / hhi, 4) if hhi > 0 else 0.0,
    }


def concentration_risks(
    holdings: Sequence[HoldingRecord],
    exposures: Sequence[ExposureRecord],
) -> tuple[RiskRecord, ...]:
    conc = compute_concentration(holdings)
    risks: list[RiskRecord] = []
    largest = conc.get("largest_position") or {}
    lw = float(largest.get("weight") or 0.0)
    if lw >= 0.25:
        risks.append(
            RiskRecord(
                kind="position_concentration",
                label=f"Large position {largest.get('ticker')}",
                severity="high",
                score=lw,
                detail=f"Largest holding weight {lw:.1%}",
            )
        )
    elif lw >= 0.15:
        risks.append(
            RiskRecord(
                kind="position_concentration",
                label=f"Elevated position {largest.get('ticker')}",
                severity="medium",
                score=lw,
                detail=f"Largest holding weight {lw:.1%}",
            )
        )

    sectors = exposures_by_dimension(exposures, "sector")
    if sectors:
        top = sectors[0]
        if top.weight >= 0.60:
            risks.append(
                RiskRecord(
                    kind="sector_concentration",
                    label=f"Sector concentration {top.name}",
                    severity="critical" if top.weight >= 0.80 else "high",
                    score=top.weight,
                    detail=f"Sector weight {top.weight:.1%}",
                )
            )
        elif top.weight >= 0.40:
            risks.append(
                RiskRecord(
                    kind="sector_concentration",
                    label=f"Sector tilt {top.name}",
                    severity="medium",
                    score=top.weight,
                    detail=f"Sector weight {top.weight:.1%}",
                )
            )

    hhi = float(conc.get("hhi") or 0.0)
    if hhi >= 0.25:
        risks.append(
            RiskRecord(
                kind="hhi",
                label="High portfolio HHI",
                severity="high",
                score=hhi,
                detail=f"HHI={hhi:.3f}",
            )
        )
    return tuple(risks)
