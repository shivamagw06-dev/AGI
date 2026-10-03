"""Valuation narrative engine — observations only (never BUY/SELL)."""

from __future__ import annotations

from typing import Any

from valuation_intelligence.schema import HistoricalBand, RelativeMetric


_FORBIDDEN = (
    "buy",
    "sell",
    "accumulate",
    "reduce",
    "overweight",
    "underweight",
    "recommend",
    "target price",
    "price target",
)


def _clean(line: str) -> str | None:
    low = line.lower()
    if any(tok in low for tok in _FORBIDDEN):
        return None
    return line


def build_narrative(
    *,
    relative: dict[str, RelativeMetric],
    historical: dict[str, HistoricalBand],
    quality: dict[str, float | None],
    growth: dict[str, Any],
) -> tuple[str, list[str]]:
    observations: list[str] = []

    pe_rel = relative.get("pe")
    if pe_rel and pe_rel.premium_pct is not None:
        if pe_rel.premium_pct > 5:
            observations.append("Trading above peer median valuation.")
            if any("Higher ROE" in r for r in pe_rel.reasons):
                observations.append("Premium supported by superior ROE.")
            if any("Higher EPS CAGR" in r for r in pe_rel.reasons):
                observations.append("Premium supported by stronger earnings growth.")
            if any("Lower leverage" in r for r in pe_rel.reasons):
                observations.append("Premium supported by capital efficiency.")
            if pe_rel.premium_pct > 25:
                observations.append("Valuation appears stretched relative to earnings trajectory.")
        elif pe_rel.premium_pct < -5:
            observations.append("Trading below peer median valuation.")
            if any("Lower EPS CAGR" in r for r in pe_rel.reasons):
                observations.append("Discount reflects slower growth.")
            if any("Lower ROE" in r for r in pe_rel.reasons):
                observations.append("Discount reflects weaker profitability versus peers.")
        else:
            observations.append("Valuation broadly in line with peer median.")

    pb_rel = relative.get("pb")
    if pb_rel and pb_rel.premium_pct is not None and abs(pb_rel.premium_pct) > 8:
        if pb_rel.premium_pct > 0:
            observations.append("Price-to-book premium versus peer median.")
        else:
            observations.append("Price-to-book discount versus peer median.")

    roe = quality.get("roe")
    if isinstance(roe, (int, float)):
        peer_roe_rel = relative.get("roe")
        if peer_roe_rel and peer_roe_rel.peer_median is not None:
            if roe > peer_roe_rel.peer_median * 1.05:
                observations.append("Margin and return profile stronger than sector average.")
            elif roe < peer_roe_rel.peer_median * 0.95:
                observations.append("Return on equity trails peer median.")

    ebitda_m = quality.get("ebitda_margin")
    if isinstance(ebitda_m, (int, float)) and ebitda_m > 0:
        observations.append(f"EBITDA margin currently {ebitda_m:.1f}%.")

    pe_hist = historical.get("pe")
    if pe_hist and pe_hist.percentile is not None:
        if pe_hist.percentile >= 80:
            observations.append(
                f"Historical valuation near cycle highs ({pe_hist.percentile:.0f}th percentile of own history)."
            )
        elif pe_hist.percentile <= 20:
            observations.append(
                f"Historical valuation near cycle lows ({pe_hist.percentile:.0f}th percentile of own history)."
            )
        else:
            observations.append(
                f"Current PE at the {pe_hist.percentile:.0f}th percentile of its own trading history."
            )

    # Deduplicate + sanitize
    seen: set[str] = set()
    clean_obs: list[str] = []
    for line in observations:
        c = _clean(line)
        if c and c not in seen:
            seen.add(c)
            clean_obs.append(c)

    # Headline stance (observation, not recommendation)
    stance = "in line with peers"
    if pe_rel and pe_rel.premium_pct is not None:
        if pe_rel.premium_pct > 10 and any("supported" in o.lower() for o in clean_obs):
            stance = "premium justified"
        elif pe_rel.premium_pct > 10:
            stance = "premium versus peers"
        elif pe_rel.premium_pct < -10:
            stance = "discount versus peers"

    if pe_hist and pe_hist.percentile is not None and pe_hist.percentile >= 85:
        stance = "historically elevated"

    return stance, clean_obs[:8]
