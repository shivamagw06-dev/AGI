"""Portfolio Office recommendation engine — Review/Research/Monitor language only. Never Buy/Sell/Execute."""

from __future__ import annotations

from typing import Any

from app.schemas.models import PortfolioPackage, PortfolioRecommendation, PortfolioSnapshot


FORBIDDEN = ("buy", "sell", "execute", "purchase", "liquidate", "add shares", "trim shares")


def _safe_title(verb: str, subject: str) -> str:
    return f"{verb} {subject}".strip()


def generate_recommendations(
    snapshot: PortfolioSnapshot,
    *,
    sector_exposure: dict[str, float],
    holding_research: list[dict[str, Any]],
    diversification_score: int | None,
    research_score: int | None,
    risk_score: int | None,
) -> list[PortfolioRecommendation]:
    recs: list[PortfolioRecommendation] = []

    # Concentration
    top_sector, top_w = (None, 0.0)
    if sector_exposure:
        top_sector, top_w = next(iter(sector_exposure.items()))
    if top_sector and top_w >= 0.35:
        recs.append(
            PortfolioRecommendation(
                priority="high" if top_w >= 0.45 else "medium",
                verb="Research",
                title=_safe_title("Research", f"{top_sector} concentration"),
                reason=f"Sector weight in {top_sector} is {top_w:.0%} of stated portfolio weights.",
                evidence=[f"sector_exposure.{top_sector}={top_w:.4f}"],
                confidence=70,
                symbols=[h.symbol for h in snapshot.holdings if (h.sector or "Unclassified") == top_sector][:5],
                supporting_research=["Portfolio weight map from ingested holdings"],
            )
        )

    # Single-name concentration
    for h in snapshot.holdings:
        if (h.weight or 0) >= 0.20:
            recs.append(
                PortfolioRecommendation(
                    priority="high" if (h.weight or 0) >= 0.30 else "medium",
                    verb="Review",
                    title=_safe_title("Review", f"{h.symbol} position size"),
                    reason=f"{h.symbol} is {(h.weight or 0):.0%} of stated weights — concentration risk may warrant diversification research.",
                    evidence=[f"{h.symbol}.weight={h.weight}"],
                    confidence=65,
                    symbols=[h.symbol],
                    supporting_research=["Holding weight from portfolio ingestion"],
                )
            )

    # Research coverage gaps / confidence declines
    low_conf = [r for r in holding_research if r.get("confidence") is not None and r["confidence"] < 45]
    for row in low_conf[:4]:
        recs.append(
            PortfolioRecommendation(
                priority="high",
                verb="Review",
                title=_safe_title("Review", f"{row.get('symbol')} research confidence"),
                reason="Holding research confidence is low or incomplete — revisit assumptions.",
                evidence=[f"{row.get('symbol')}.confidence={row.get('confidence')}"],
                confidence=int(row.get("confidence") or 40),
                symbols=[str(row.get("symbol"))],
                supporting_research=[row.get("run_id") or "equity child research"],
            )
        )

    missing = [r for r in holding_research if r.get("missing")]
    if missing:
        recs.append(
            PortfolioRecommendation(
                priority="medium",
                verb="Investigate",
                title=_safe_title("Investigate", "missing holding research"),
                reason=f"{len(missing)} holdings lack completed research packages.",
                evidence=[f"{m.get('symbol')}: {m.get('missing')}" for m in missing[:5]],
                confidence=55,
                symbols=[str(m.get("symbol")) for m in missing[:8]],
                supporting_research=["Equity desk child runs"],
            )
        )

    if diversification_score is not None and diversification_score < 45:
        recs.append(
            PortfolioRecommendation(
                priority="medium",
                verb="Consider",
                title=_safe_title("Consider", "diversification review"),
                reason="Diversification score is weak based on sector weight dispersion of stated holdings.",
                evidence=[f"diversification_score={diversification_score}"],
                confidence=60,
                symbols=[h.symbol for h in snapshot.holdings[:6]],
                supporting_research=["Sector exposure map"],
            )
        )

    if risk_score is not None and risk_score >= 70:
        recs.append(
            PortfolioRecommendation(
                priority="high",
                verb="Monitor",
                title=_safe_title("Monitor", "elevated portfolio risk factors"),
                reason="Aggregated risk factors across holdings are elevated relative to available evidence.",
                evidence=[f"risk_score={risk_score}"],
                confidence=58,
                symbols=[h.symbol for h in snapshot.holdings[:5]],
                supporting_research=["Holding risk lists from research packages"],
            )
        )

    if research_score is not None and research_score < 50:
        recs.append(
            PortfolioRecommendation(
                priority="medium",
                verb="Research",
                title=_safe_title("Research", "portfolio coverage quality"),
                reason="Average research coverage/confidence across holdings is limited.",
                evidence=[f"research_score={research_score}"],
                confidence=55,
                symbols=[],
                supporting_research=["Holding research rollup"],
            )
        )

    # Energy / oil heuristic from sector labels only
    energy_w = sum(v for k, v in sector_exposure.items() if any(x in k.lower() for x in ("energy", "oil", "gas")))
    if energy_w >= 0.20:
        recs.append(
            PortfolioRecommendation(
                priority="medium",
                verb="Monitor",
                title=_safe_title("Monitor", "oil / energy exposure"),
                reason=f"Energy-related sector weights total {energy_w:.0%} — macro oil moves may matter.",
                evidence=[f"energy_related_weight={energy_w:.4f}"],
                confidence=62,
                symbols=[h.symbol for h in snapshot.holdings if h.sector and any(x in h.sector.lower() for x in ("energy", "oil", "gas"))][:5],
                supporting_research=["Sector labels from holdings"],
            )
        )

    # Sanitize language
    clean: list[PortfolioRecommendation] = []
    for rec in recs:
        blob = f"{rec.title} {rec.reason}".lower()
        if any(w in blob for w in FORBIDDEN):
            continue
        clean.append(rec)
    return clean[:12]


def build_action_center(recommendations: list[PortfolioRecommendation]) -> dict[str, list[dict[str, Any]]]:
    center = {"high": [], "medium": [], "low": []}
    for rec in recommendations:
        center.setdefault(rec.priority, []).append(
            {
                "id": rec.recommendation_id,
                "priority": rec.priority,
                "verb": rec.verb,
                "title": rec.title,
                "reason": rec.reason,
                "confidence": rec.confidence,
                "symbols": rec.symbols,
                "evidence": rec.evidence,
            }
        )
    return center


def attach_to_package(pack: PortfolioPackage) -> PortfolioPackage:
    recs = generate_recommendations(
        pack.portfolio,
        sector_exposure=pack.sector_exposure,
        holding_research=pack.holding_research,
        diversification_score=pack.diversification_score,
        research_score=pack.research_score,
        risk_score=pack.risk_score,
    )
    pack.recommendations = recs
    pack.action_center = build_action_center(recs)
    return pack
