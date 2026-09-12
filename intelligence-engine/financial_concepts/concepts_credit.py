"""Module 7 — Credit Concepts."""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "credit"

CREDIT_CONCEPTS: dict[str, ConceptCard] = {
    "debt_service_coverage": ConceptCard(
        "debt_service_coverage", M, "Debt Service Coverage Ratio (DSCR)",
        "How many times over a company's operating cash flow can cover its total debt service — both interest AND scheduled principal repayment.",
        formula="DSCR = Operating Cash Flow (or EBITDA) / (Interest Expense + Scheduled Principal Repayments)",
        business_meaning="A stricter, more complete solvency check than interest coverage alone, since principal repayments are a real cash obligation just as much as interest.",
        interpretation="DSCR below 1.0x means the company cannot service its scheduled debt from operating cash flow alone and must refinance, draw down cash reserves, or raise new capital.",
        related_concepts=("interest_coverage", "fixed_charge_coverage", "refinancing_risk"),
    ),
    "debt_maturity": ConceptCard(
        "debt_maturity", M, "Debt Maturity (Profile)",
        "The schedule of when a company's outstanding debt obligations come due for repayment or refinancing.",
        business_meaning="A 'wall' of debt maturing in a single year concentrates refinancing risk — if credit markets are stressed or the company's credit quality has deteriorated at that moment, refinancing can become expensive or impossible.",
        interpretation="A well-laddered maturity profile (debt spread evenly across many future years) is materially safer than a concentrated maturity wall, even at the same total debt level.",
        related_concepts=("refinancing_risk", "liquidity", "credit_ratings"),
    ),
    "liquidity": ConceptCard(
        "liquidity", M, "Liquidity",
        "A company's or market's ability to meet short-term obligations or convert assets to cash quickly without significant loss of value.",
        formula="Common proxies: Current Ratio = Current Assets / Current Liabilities; Quick Ratio excludes inventory",
        business_meaning="For a company, liquidity determines whether it can survive a short-term shock (a bad quarter, a funding-market freeze) without being forced into distressed asset sales or default.",
        interpretation="A company can be solvent (assets exceed liabilities long-term) yet still fail from a liquidity crunch if it cannot meet near-term cash obligations — liquidity and solvency are related but distinct risks.",
        related_concepts=("cash_flow_coverage_ratio", "refinancing_risk"),
    ),
    "refinancing_risk": ConceptCard(
        "refinancing_risk", M, "Refinancing Risk",
        "The risk that a company will be unable to roll over maturing debt on acceptable terms — or at all — when it comes due.",
        business_meaning="Even a fundamentally healthy operating business can be forced into default or a distressed capital raise purely from a mismatch between debt maturities and available credit-market conditions.",
        interpretation="Refinancing risk rises sharply for companies with concentrated debt maturities, weakening credit metrics, or dependence on volatile short-term funding markets.",
        related_concepts=("debt_maturity", "liquidity", "credit_ratings", "default_risk"),
    ),
    "covenants": ConceptCard(
        "covenants", M, "Covenants (Debt Covenants)",
        "Contractual conditions in a loan or bond agreement that restrict a borrower's actions (e.g. maximum leverage, minimum interest coverage) to protect lenders.",
        business_meaning="Covenant breaches can trigger technical default even if the company is still making all scheduled payments — lenders can then demand immediate repayment or force restructuring.",
        interpretation="A company operating close to its covenant thresholds has materially less financial flexibility than the headline leverage ratio alone suggests, since even a modest earnings miss can trigger a breach.",
        related_concepts=("interest_coverage", "credit_ratings", "default_risk"),
    ),
    "credit_ratings": ConceptCard(
        "credit_ratings", M, "Credit Ratings",
        "An independent agency's (e.g. S&P, Moody's, Fitch, CRISIL) assessment of a borrower's ability and willingness to meet its debt obligations, expressed as a letter-grade scale.",
        business_meaning="Ratings directly affect a company's cost of debt — a downgrade typically widens credit spreads and raises future borrowing costs, sometimes triggering covenant-linked rate step-ups.",
        interpretation="A ratings downgrade is often a lagging confirmation of deteriorating fundamentals already visible in coverage ratios and leverage trends, rather than new information for a diligent analyst.",
        related_concepts=("default_risk", "cost_of_debt", "credit_spread", "covenants"),
    ),
    "default_risk": ConceptCard(
        "default_risk", M, "Default Risk",
        "The probability that a borrower will fail to make a scheduled interest or principal payment on its debt obligations.",
        business_meaning="Compensated for in the market via credit spreads — riskier borrowers must offer a higher yield over the risk-free rate to attract lenders.",
        interpretation="Default risk should be assessed through both a solvency lens (leverage, coverage ratios) and a liquidity lens (near-term maturities, access to funding) — either alone can miss the real risk.",
        related_concepts=("probability_of_default", "credit_spread", "credit_ratings", "loss_given_default"),
    ),
    "probability_of_default": ConceptCard(
        "probability_of_default", M, "Probability of Default (PD)",
        "The statistical likelihood that a borrower will default on its debt obligations within a given time horizon.",
        business_meaning="A core input (alongside Loss Given Default and Exposure at Default) to expected credit loss models used by banks and rating agencies.",
        related_concepts=("default_risk", "loss_given_default", "credit_ratings"),
    ),
    "loss_given_default": ConceptCard(
        "loss_given_default", M, "Loss Given Default (LGD)",
        "The proportion of an exposure a lender expects to lose if a borrower actually defaults, after accounting for recoveries (collateral, seniority, restructuring).",
        formula="Expected Loss = Probability of Default × Loss Given Default × Exposure at Default",
        business_meaning="A senior secured loan typically has much lower LGD than a subordinated unsecured bond to the same borrower — seniority and collateral materially change the recovery outcome even for the same default event.",
        related_concepts=("probability_of_default", "seniority", "collateral", "recovery_rate"),
    ),
    "recovery_rate": ConceptCard(
        "recovery_rate", M, "Recovery Rate",
        "The percentage of a defaulted debt's face value that creditors actually recover, typically through restructuring, asset sales, or liquidation.",
        formula="Recovery Rate = 1 − Loss Given Default",
        business_meaning="Recovery rates vary widely by seniority and collateral — senior secured debt often recovers 60-80%+, while unsecured subordinated debt can recover very little.",
        related_concepts=("loss_given_default", "seniority", "collateral"),
    ),
    "seniority": ConceptCard(
        "seniority", M, "Seniority (of Debt)",
        "The priority order in which different classes of debt (and equity) are repaid in a bankruptcy or liquidation.",
        business_meaning="Senior secured lenders are repaid first from specific pledged assets; senior unsecured next; subordinated debt after that; equity holders are repaid only if anything remains.",
        interpretation="Two bonds from the same issuer can carry very different risk and pricing purely due to where they sit in the seniority stack, independent of the issuer's overall credit quality.",
        related_concepts=("subordination", "collateral", "recovery_rate"),
    ),
    "subordination": ConceptCard(
        "subordination", M, "Subordination",
        "Debt that ranks below other, more senior claims in priority of repayment — subordinated creditors are paid only after senior creditors are made whole.",
        business_meaning="Subordinated debt compensates for its lower repayment priority with a higher coupon/yield versus senior debt from the same issuer.",
        related_concepts=("seniority", "recovery_rate", "credit_spread"),
    ),
    "collateral": ConceptCard(
        "collateral", M, "Collateral",
        "Specific assets pledged by a borrower to secure a loan, which the lender can seize and sell if the borrower defaults.",
        business_meaning="Secured lending (backed by collateral) carries materially lower loss-given-default than unsecured lending, and therefore typically commands a lower interest rate.",
        related_concepts=("seniority", "loss_given_default", "recovery_rate"),
    ),
    "credit_spread": ConceptCard(
        "credit_spread", M, "Credit Spread",
        "The extra yield a corporate (or other non-government) bond offers over a comparable-maturity risk-free government bond, compensating investors for default risk.",
        formula="Credit Spread = Corporate Bond Yield − Risk-Free Rate (matched maturity)",
        business_meaning="Widening credit spreads for a specific issuer signal the market perceives rising default risk, often ahead of an actual rating-agency downgrade.",
        interpretation="Credit spreads widen across the whole market during periods of macro/liquidity stress even for fundamentally unchanged issuers — always separate issuer-specific spread moves from market-wide risk-aversion moves.",
        related_concepts=("default_risk", "credit_ratings", "cost_of_debt", "risk_free_rate"),
    ),
}
