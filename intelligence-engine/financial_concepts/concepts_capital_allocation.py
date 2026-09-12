"""Module 6 — Capital Allocation Concepts."""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "capital_allocation"

CAPITAL_ALLOCATION_CONCEPTS: dict[str, ConceptCard] = {
    "roic": ConceptCard(
        "roic", M, "ROIC (Return on Invested Capital)",
        "The return a company generates on all the capital — debt and equity combined — that has been invested in its operating business.",
        formula="ROIC = NOPAT / Invested Capital",
        business_meaning="The single most important capital-efficiency metric because it is capital-structure-neutral (unlike ROE) and directly comparable to WACC to judge value creation.",
        interpretation="ROIC consistently above WACC across a cycle is the clearest quantitative signature of a durable competitive advantage (moat); ROIC below WACC means the business is destroying value even if it reports accounting profit.",
        common_mistakes="Comparing ROIC to ROE as if they measure the same thing — ROE can be inflated by leverage alone, while ROIC strips leverage out.",
        related_concepts=("nopat", "invested_capital", "wacc", "economic_profit", "incremental_roic"),
    ),
    "roce": ConceptCard(
        "roce", M, "ROCE (Return on Capital Employed)",
        "The return a company generates on its long-term capital base — equity plus long-term debt — a widely used capital-efficiency ratio, especially outside the US.",
        formula="ROCE = EBIT / Capital Employed, where Capital Employed = Total Assets − Current Liabilities",
        business_meaning="Similar in spirit to ROIC but calculated from readily available balance-sheet line items (Total Assets, Current Liabilities) rather than requiring the more involved NOPAT/Invested Capital adjustments.",
        interpretation="ROCE can rise while ROE falls when leverage decreases (paying down debt reduces the equity multiplier that inflates ROE) even as underlying operating returns on the full capital base actually improve — the two ratios isolate different effects of a capital-structure change.",
        common_mistakes="Treating ROCE and ROE as interchangeable — ROCE is leverage-neutral (uses EBIT and total capital employed), while ROE is directly affected by financial leverage.",
        related_concepts=("roic", "capital_employed", "dupont_model", "financial_leverage"),
    ),
    "economic_moat": ConceptCard(
        "economic_moat", M, "Economic Moat",
        "A durable competitive advantage that allows a company to sustain above-average returns on capital over a long period, protecting it from competitive erosion.",
        business_meaning="Moats typically come from network effects, switching costs, cost advantages/scale economies, intangible assets (brands, patents, licenses), or efficient-scale niches too small to attract a second competitor.",
        interpretation="The quantitative signature of a moat is ROIC sustained meaningfully above WACC for many years despite competitive pressure — the qualitative source of the moat should explain WHY competitors can't compete that away.",
        common_mistakes="Assuming a company has a moat simply because it is currently profitable or has a well-known brand — a moat must be demonstrated to be durable against specific competitive threats.",
        related_concepts=("roic", "network_effect", "switching_cost", "pricing_power", "barriers_to_entry"),
    ),
    "share_buyback": ConceptCard(
        "share_buyback", M, "Share Buyback",
        "A company repurchasing its own shares from the market, reducing shares outstanding and returning cash to remaining shareholders.",
        business_meaning="Buybacks are value-creating for remaining shareholders only when executed at a price below the company's intrinsic value — buying back overvalued stock destroys value just as surely as a bad acquisition.",
        interpretation="A buyback that lifts EPS by shrinking the share count is not the same as creating economic value — always check the price paid relative to a reasonable estimate of intrinsic value.",
        common_mistakes="Judging a buyback program purely by its size, without assessing the valuation at which the shares were repurchased.",
        related_concepts=("dividend_policy", "capital_recycling", "market_capitalization"),
    ),
    "dividend_policy": ConceptCard(
        "dividend_policy", M, "Dividend Policy",
        "A company's stated or observed approach to returning a portion of profit to shareholders as cash dividends, as opposed to reinvesting it or buying back shares.",
        business_meaning="Reflects management's view on the availability of value-creating reinvestment opportunities — mature, low-growth businesses with limited high-ROIC projects typically favor higher payout, while high-growth businesses retain more capital.",
        interpretation="A dividend cut is one of the strongest negative signals a management team can send — it directly admits the cash flow can no longer safely support the prior payout.",
        related_concepts=("payout_ratio", "dividend_coverage", "dividend_sustainability", "reinvestment_rate"),
    ),
    "capital_recycling": ConceptCard(
        "capital_recycling", M, "Capital Recycling",
        "Selling mature, lower-growth, or non-core assets and redeploying the proceeds into higher-return opportunities — organic growth, acquisitions, or shareholder returns.",
        business_meaning="Active capital recycling signals a management team disciplined about continuously upgrading where capital is deployed, rather than passively holding legacy assets indefinitely.",
        interpretation="Consistent capital recycling into projects earning above the company's incremental ROIC hurdle is a hallmark of superior capital allocation.",
        related_concepts=("roic", "incremental_roic", "reinvestment_rate"),
    ),
    "reinvestment_rate": ConceptCard(
        "reinvestment_rate", M, "Reinvestment Rate",
        "The proportion of a company's profit that is retained and reinvested back into the business, rather than distributed to shareholders.",
        formula="Reinvestment Rate = (Capex + Increase in Working Capital − D&A) / NOPAT, or equivalently 1 − Payout Ratio",
        business_meaning="Combined with ROIC, the reinvestment rate determines a company's sustainable organic growth rate: Growth ≈ Reinvestment Rate × ROIC.",
        interpretation="A high reinvestment rate is only good news if it is paired with a high (and stable or rising) incremental ROIC — high reinvestment at low returns simply compounds value destruction faster.",
        related_concepts=("roic", "incremental_roic", "payout_ratio", "growth_capex"),
    ),
    "payout_ratio": ConceptCard(
        "payout_ratio", M, "Payout Ratio",
        "The proportion of net income a company pays out to shareholders as dividends.",
        formula="Payout Ratio = Total Dividends Paid / Net Income",
        business_meaning="The complement of the reinvestment rate — a company can either return this money to shareholders now or reinvest it for future growth, but not both with the same dollar.",
        interpretation="A sustainably low payout ratio in a high-ROIC business is a sign of good capital discipline (reinvesting where returns are attractive); a very high or rising payout ratio in a business with few growth opportunities can be entirely appropriate.",
        related_concepts=("dividend_coverage", "dividend_sustainability", "reinvestment_rate"),
    ),
    "dividend_sustainability": ConceptCard(
        "dividend_sustainability", M, "Dividend Sustainability",
        "Whether a company's current cash flow generation can comfortably support its dividend payments over time, through both good and challenging periods.",
        business_meaning="Sustainability depends on cash flow coverage (not just accounting earnings coverage), balance-sheet flexibility, and the stability of the underlying business through a cycle.",
        interpretation="A dividend can appear well-covered by current earnings yet be unsustainable if it depends on cyclically high profit that will not persist through a downturn.",
        related_concepts=("dividend_coverage", "payout_ratio", "free_cash_flow"),
    ),
    "acquisition_returns": ConceptCard(
        "acquisition_returns", M, "Acquisition (M&A) Returns",
        "Whether an acquisition creates or destroys value for the acquirer's shareholders, typically judged by whether post-deal ROIC (including the price paid) exceeds the acquirer's cost of capital.",
        business_meaning="The price paid (often including a large control premium) matters as much as the quality of the target business — even a great business can be a value-destroying acquisition if overpaid for.",
        interpretation="M&A that is dilutive to near-term ROIC can still be value-creating if synergies and growth are realized; conversely, EPS-accretive deals can still destroy value if the implied return is below the cost of capital.",
        common_mistakes="Judging acquisition success purely by whether the deal was 'EPS accretive' — accretion/dilution says nothing about whether the price paid earns an adequate return on the capital deployed.",
        related_concepts=("control_premium", "roic", "economic_profit"),
    ),
}
