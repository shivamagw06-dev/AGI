"""Module 8 — Market Concepts."""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "market"

MARKET_CONCEPTS: dict[str, ConceptCard] = {
    "bull_market": ConceptCard(
        "bull_market", M, "Bull Market",
        "A sustained period of rising asset prices, typically defined as a broad market index rising 20%+ from a recent low, accompanied by widespread investor optimism.",
        business_meaning="Bull markets are usually associated with economic expansion, rising corporate earnings, and easing financial conditions, though they can also form on liquidity/speculation alone.",
        interpretation="Valuations tend to expand (multiples rise faster than earnings) in the later stages of a bull market, which is when discipline about what one is paying for future growth matters most.",
        related_concepts=("bear_market", "volatility", "risk_premium"),
    ),
    "bear_market": ConceptCard(
        "bear_market", M, "Bear Market",
        "A sustained period of falling asset prices, typically defined as a broad market index falling 20%+ from a recent high, accompanied by widespread investor pessimism.",
        business_meaning="Bear markets are usually triggered or accompanied by recession fears, earnings downgrades, tightening financial conditions, or a systemic shock.",
        interpretation="Valuation multiples tend to compress faster than earnings actually fall in the early stages of a bear market, as risk premiums rise and sentiment deteriorates ahead of confirmed fundamental damage.",
        related_concepts=("bull_market", "volatility", "risk_premium"),
    ),
    "risk_premium": ConceptCard(
        "risk_premium", M, "Risk Premium",
        "The additional expected return investors demand for holding a riskier asset over a risk-free alternative.",
        business_meaning="Risk premiums exist for equities (Equity Risk Premium), corporate credit (Credit Spread), emerging markets (Country Risk Premium), and illiquid assets (Liquidity Premium) — each compensating for a distinct source of risk.",
        interpretation="Risk premiums widen during periods of uncertainty and narrow during calm, complacent periods — they are a key, often underappreciated driver of valuation multiples independent of any change in fundamentals.",
        related_concepts=("equity_risk_premium", "credit_spread", "cost_of_equity"),
    ),
    "yield_curve": ConceptCard(
        "yield_curve", M, "Yield Curve",
        "A plot of government bond yields across different maturities, from short-term to long-term.",
        business_meaning="The shape of the yield curve reflects market expectations for future growth, inflation, and central bank policy — a normal upward-sloping curve compensates lenders for locking up money longer.",
        interpretation="An inverted yield curve (short-term yields above long-term yields) has historically been one of the most reliable leading indicators of an approaching economic slowdown or recession.",
        related_concepts=("nominal_rates", "real_rates", "inflation", "duration"),
    ),
    "duration": ConceptCard(
        "duration", M, "Duration",
        "A measure of a bond's (or bond portfolio's) sensitivity to changes in interest rates, expressed roughly as the number of years it takes to recoup the bond's price through its cash flows.",
        business_meaning="Longer-duration bonds see much larger price swings for a given change in interest rates than shorter-duration bonds — duration is the primary driver of interest-rate risk in fixed income.",
        interpretation="A 1% rise in rates causes a bond's price to fall by approximately its duration percentage — an 8-year duration bond falls roughly 8% for a 1% rate rise, all else equal.",
        related_concepts=("yield_curve", "nominal_rates", "real_rates"),
    ),
    "inflation": ConceptCard(
        "inflation", M, "Inflation",
        "The rate at which the general price level of goods and services in an economy rises over time, eroding the purchasing power of money.",
        business_meaning="Inflation affects companies unevenly: pricing-power businesses can pass costs through and even benefit, while businesses with fixed-price long-term contracts or high input-cost sensitivity can see margins compressed.",
        interpretation="Rising inflation typically pushes central banks to raise interest rates, which raises the discount rate used in valuation and tends to compress equity multiples, especially for long-duration growth stocks.",
        related_concepts=("nominal_rates", "real_rates", "pricing_power"),
    ),
    "real_rates": ConceptCard(
        "real_rates", M, "Real Interest Rates",
        "Interest rates adjusted for inflation — the actual growth in purchasing power an investor earns, not just the nominal number.",
        formula="Real Rate ≈ Nominal Rate − Inflation Rate",
        business_meaning="Real rates, not nominal rates, drive real economic decisions (borrowing, investing) because they reflect the true cost/return after accounting for eroding purchasing power.",
        interpretation="Negative real rates (nominal rates below inflation) effectively penalize cash savers and tend to push capital toward riskier assets in search of a positive real return.",
        related_concepts=("nominal_rates", "inflation", "risk_free_rate"),
    ),
    "nominal_rates": ConceptCard(
        "nominal_rates", M, "Nominal Interest Rates",
        "The stated interest rate on a loan, bond, or deposit, without adjusting for inflation.",
        formula="Nominal Rate ≈ Real Rate + Expected Inflation",
        business_meaning="What is typically quoted in the market (a bond's coupon, a bank's advertised deposit rate) — always needs to be compared against inflation expectations to judge true economic return.",
        related_concepts=("real_rates", "inflation", "risk_free_rate", "yield_curve"),
    ),
    "volatility": ConceptCard(
        "volatility", M, "Volatility",
        "A statistical measure of how much an asset's price fluctuates over time, typically expressed as the standard deviation of returns.",
        business_meaning="Higher volatility means a wider range of possible outcomes and is generally associated with higher perceived risk, though it is not the only measure of true fundamental risk.",
        interpretation="Volatility can spike from pure sentiment/liquidity shifts even when a company's underlying fundamentals are unchanged — distinguishing 'noise' volatility from fundamentally-driven price moves is a core analyst skill.",
        related_concepts=("beta", "systematic_risk", "risk_premium"),
    ),
    "systematic_risk": ConceptCard(
        "systematic_risk", M, "Systematic Risk",
        "Risk inherent to the entire market or economy — macro, interest-rate, or geopolitical risk that cannot be diversified away by holding more stocks.",
        business_meaning="Beta measures a stock's sensitivity to this market-wide, undiversifiable risk — it is the only risk the CAPM says investors should be compensated for bearing.",
        interpretation="Because systematic risk cannot be diversified away, it commands a risk premium; unsystematic (company-specific) risk theoretically does not, since a diversified investor can eliminate it.",
        related_concepts=("beta", "unsystematic_risk", "diversification"),
    ),
    "unsystematic_risk": ConceptCard(
        "unsystematic_risk", M, "Unsystematic (Idiosyncratic) Risk",
        "Risk specific to an individual company or industry — a factory fire, a management scandal, a lost customer — that does not affect the broader market.",
        business_meaning="Can be substantially reduced or eliminated by holding a diversified portfolio of many uncorrelated stocks, unlike systematic/market risk.",
        interpretation="Concentrated portfolios bear more unsystematic risk than diversified ones for the same expected return — this is the core argument for diversification.",
        related_concepts=("systematic_risk", "diversification", "beta"),
    ),
    "diversification": ConceptCard(
        "diversification", M, "Diversification",
        "Spreading investment capital across multiple, imperfectly-correlated assets to reduce a portfolio's overall (unsystematic) risk without necessarily sacrificing expected return.",
        business_meaning="Diversification works because the specific risks of individual holdings partially offset each other — the portfolio's volatility can be lower than the average volatility of its individual components.",
        interpretation="Diversification benefits shrink as correlation between holdings rises — during systemic crises, correlations across asset classes tend to spike toward 1.0, reducing diversification's protective effect exactly when it is needed most.",
        related_concepts=("systematic_risk", "unsystematic_risk", "correlation"),
    ),
    "correlation": ConceptCard(
        "correlation", M, "Correlation",
        "A statistical measure (from -1 to +1) of how two assets' returns move together over time.",
        business_meaning="Diversification benefit depends on correlation, not just the number of holdings — adding more assets with correlation near +1 to each other provides little real risk reduction.",
        interpretation="Correlations across asset classes are not fixed — they tend to rise sharply during systemic stress events, a phenomenon sometimes called 'correlation going to one'.",
        related_concepts=("diversification", "systematic_risk"),
    ),
    "sharpe_ratio": ConceptCard(
        "sharpe_ratio", M, "Sharpe Ratio",
        "A measure of risk-adjusted return: how much excess return (over the risk-free rate) an investment generates per unit of volatility (risk) taken.",
        formula="Sharpe Ratio = (Portfolio Return − Risk-Free Rate) / Portfolio Standard Deviation",
        business_meaning="Lets investors compare strategies with different risk levels on a like-for-like basis — a lower-return strategy with much lower volatility can have a superior Sharpe Ratio to a higher-return, higher-volatility one.",
        interpretation="A rising Sharpe Ratio over time reflects genuinely improving risk-adjusted skill; a high Sharpe Ratio achieved via leverage on a low-volatility strategy can mask hidden tail risk not captured by standard deviation.",
        related_concepts=("volatility", "risk_free_rate", "alpha"),
    ),
    "alpha": ConceptCard(
        "alpha", M, "Alpha",
        "The excess return of an investment or strategy relative to what would be expected given its risk (beta) exposure to the market.",
        formula="Alpha = Actual Return − [Risk-Free Rate + Beta × (Market Return − Risk-Free Rate)]",
        business_meaning="Positive alpha represents genuine skill-based outperformance beyond simply taking on more market risk; a portfolio can have a high raw return with zero or negative alpha if that return is fully explained by beta.",
        interpretation="Consistent, statistically significant alpha over long periods and many market cycles is rare — most apparent alpha over short periods is attributable to luck, unrewarded risk factors, or survivorship bias.",
        related_concepts=("beta", "sharpe_ratio", "systematic_risk"),
    ),
}
