"""Extended Module — Corporate Actions & Capital Markets Mechanics.

Legitimate extensions beyond the Phase 2.6 brief's named terms: the
mechanics analysts need to interpret corporate-action announcements
(buybacks, spin-offs, rights issues) and complex-security dilution, which
sit adjacent to Module 1 (Corporate Finance) and Module 6 (Capital
Allocation) but are distinct enough to warrant their own cards.
"""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "corporate_finance"

CORPORATE_ACTIONS_CONCEPTS: dict[str, ConceptCard] = {
    "spin_off": ConceptCard(
        "spin_off", M, "Spin-off",
        "A corporate action where a company separates a business unit into a new, independently-listed company, distributing shares of the new entity to existing shareholders.",
        business_meaning="Spin-offs are often used to unlock value from a conglomerate discount, let each business be valued and managed on its own merits, and let investors choose their preferred exposure.",
        interpretation="Spin-offs frequently outperform in the years following separation, partly because forced/indifferent institutional selling of the smaller spun-off entity creates a temporary valuation dislocation.",
        related_concepts=("sotp", "carve_out", "control_premium"),
    ),
    "carve_out": ConceptCard(
        "carve_out", M, "Carve-out (Equity Carve-out)",
        "A corporate action where a parent company sells a minority stake of a subsidiary to public investors via an IPO, while retaining majority ownership and control.",
        business_meaning="Lets a parent unlock a market valuation for a subsidiary and raise capital, while still consolidating and controlling that subsidiary's operations and strategy.",
        interpretation="Often a precursor to a full spin-off once the market has separately established a valuation benchmark for the subsidiary.",
        related_concepts=("spin_off", "sotp"),
    ),
    "rights_issue": ConceptCard(
        "rights_issue", M, "Rights Issue",
        "A company offering existing shareholders the right to purchase additional new shares, usually at a discount to the current market price, in proportion to their existing holding.",
        business_meaning="A capital-raising method that, unlike a public offering to new investors, gives existing shareholders first refusal and avoids diluting their proportional ownership if they participate fully.",
        interpretation="A large or urgent rights issue can signal balance-sheet stress; shareholders who do not participate ('let their rights lapse') are diluted.",
        related_concepts=("qip", "capital_structure", "book_value"),
    ),
    "qip": ConceptCard(
        "qip", M, "QIP (Qualified Institutional Placement)",
        "A capital-raising method (common in Indian markets) where a listed company issues new shares or convertible securities directly to institutional investors, without a full public prospectus process.",
        business_meaning="A faster, lower-cost way for a company to raise equity capital than a full public offering, but existing shareholders are diluted without the pre-emptive right offered in a rights issue.",
        related_concepts=("rights_issue", "capital_structure"),
    ),
    "bonus_issue": ConceptCard(
        "bonus_issue", M, "Bonus Issue (Stock Dividend)",
        "A company issuing additional free shares to existing shareholders in proportion to their current holding, funded by capitalizing reserves — no new capital is actually raised.",
        business_meaning="Purely a change in the number of shares outstanding and share price (both scale proportionally) — it does not change a shareholder's proportional ownership or the company's underlying value.",
        interpretation="Sometimes used to improve share-price liquidity/affordability by lowering the per-share price, or as a signal of management confidence, though it creates no fundamental economic value on its own.",
        related_concepts=("stock_split", "market_capitalization"),
    ),
    "stock_split": ConceptCard(
        "stock_split", M, "Stock Split",
        "Dividing each existing share into multiple shares (e.g. a 2-for-1 split), proportionally reducing the price per share while leaving total market value and each shareholder's ownership stake unchanged.",
        business_meaning="Purely cosmetic/mechanical — often done to improve share affordability and trading liquidity for retail investors, with no direct effect on intrinsic value.",
        related_concepts=("bonus_issue", "market_capitalization"),
    ),
    "special_dividend": ConceptCard(
        "special_dividend", M, "Special Dividend",
        "A one-time, non-recurring cash distribution to shareholders, distinct from a company's regular ongoing dividend — often funded by an asset sale, unusually strong cash generation, or excess balance-sheet cash.",
        business_meaning="A way to return capital without committing to a permanently higher regular payout that might need to be cut later if the windfall doesn't recur.",
        related_concepts=("dividend_policy", "capital_recycling", "payout_ratio"),
    ),
    "lbo": ConceptCard(
        "lbo", M, "LBO (Leveraged Buyout)",
        "An acquisition of a company financed with a significant proportion of borrowed money, with the target's own assets and cash flows typically used as collateral for the debt.",
        business_meaning="Private equity sponsors use leverage to amplify equity returns — a business bought with 70% debt needs a much smaller equity check to generate the same dollar return on a successful exit.",
        interpretation="LBO returns depend on three levers: EBITDA growth, multiple expansion at exit, and debt paydown during the holding period — deals reliant purely on financial engineering (leverage/multiple arbitrage) without operational improvement are structurally riskier.",
        related_concepts=("capital_structure", "wacc", "acquisition_returns"),
    ),
    "eps_dilution_mechanics": ConceptCard(
        "eps_dilution_mechanics", M, "Diluted vs. Basic EPS",
        "Basic EPS uses only currently outstanding shares; Diluted EPS additionally assumes conversion of all dilutive securities (stock options, convertible bonds, warrants) into shares.",
        formula="Diluted EPS = Net Income (adjusted for convertible interest/dividends) / (Basic Shares + Dilutive Securities, via Treasury Stock Method)",
        business_meaning="Diluted EPS is the more conservative, complete measure of per-share earnings power, since it reflects the maximum potential share count if all convertible claims were exercised.",
        interpretation="A large and widening gap between basic and diluted EPS signals significant potential future dilution (heavy stock-based compensation, convertible debt) that will pressure per-share metrics even without any change in total net income.",
        related_concepts=("p_e", "share_buyback", "convertible_securities"),
    ),
    "convertible_securities": ConceptCard(
        "convertible_securities", M, "Convertible Securities",
        "Debt or preferred equity instruments that can be converted into a fixed number of common shares at the holder's option, typically at a preset conversion price.",
        business_meaning="Let companies raise capital at a lower coupon/dividend rate than straight debt/preferred, in exchange for giving investors equity upside if the share price rises above the conversion price.",
        interpretation="Convertibles create a form of contingent dilution — analysts must model potential conversion (via diluted EPS) even before it actually occurs, since the market prices in that possibility.",
        related_concepts=("eps_dilution_mechanics", "capital_structure", "subordination"),
    ),
    "minority_interest": ConceptCard(
        "minority_interest", M, "Minority Interest (Non-Controlling Interest)",
        "The portion of a consolidated subsidiary's equity (and profit) that belongs to outside shareholders, not the parent company, when the parent owns less than 100% but still controls the subsidiary.",
        business_meaning="Consolidated financials include 100% of a controlled subsidiary's assets, liabilities, and profit, then separately carve out the minority's share — this matters for correctly calculating both Enterprise Value and per-share earnings attributable to the parent's own shareholders.",
        interpretation="Ignoring minority interest when computing Enterprise Value or Equity Value overstates the value actually attributable to the parent company's own shareholders.",
        related_concepts=("enterprise_value", "equity_value"),
    ),
    "preferred_equity": ConceptCard(
        "preferred_equity", M, "Preferred Equity (Preferred Stock)",
        "A hybrid capital instrument that ranks senior to common equity but junior to debt, typically paying a fixed dividend and without full voting rights.",
        business_meaning="Sits between debt and common equity in both risk and the priority-of-claims stack — treated as a component of both Enterprise Value (added, like debt) and excluded from common Equity Value.",
        related_concepts=("enterprise_value", "capital_structure", "seniority"),
    ),
    "goodwill_impairment": ConceptCard(
        "goodwill_impairment", M, "Goodwill Impairment",
        "A non-cash accounting write-down recognized when the carrying value of goodwill (from a past acquisition) on the balance sheet exceeds its estimated recoverable/fair value.",
        business_meaning="A large impairment is effectively a retrospective admission that a past acquisition was overpaid for or has underperformed expectations — it reduces book value and Net Income but does not affect current-period cash flow.",
        interpretation="Impairments should prompt scrutiny of a management team's M&A track record and capital-allocation discipline, even though the charge itself is non-cash and backward-looking.",
        related_concepts=("goodwill_and_intangibles", "acquisition_returns", "tangible_book"),
    ),
    "restructuring_charges": ConceptCard(
        "restructuring_charges", M, "Restructuring Charges",
        "One-off costs associated with reorganizing a business — severance, facility closures, contract terminations — typically excluded from 'adjusted' or 'non-GAAP' earnings measures.",
        business_meaning="Genuinely one-off restructuring can be reasonable to exclude when assessing ongoing earnings power, but companies with 'recurring one-off' restructuring charges every year are effectively understating their true normalized cost base.",
        common_mistakes="Accepting a company's non-GAAP adjustments at face value without checking whether the 'one-off' items actually recur period after period.",
        related_concepts=("non_gaap_adjustments",),
    ),
    "non_gaap_adjustments": ConceptCard(
        "non_gaap_adjustments", M, "Non-GAAP (Adjusted) Earnings",
        "Company-reported earnings measures that exclude certain items (stock-based compensation, restructuring, impairments, one-offs) that management deems non-representative of ongoing performance.",
        business_meaning="Can provide genuinely useful insight into underlying trends, but are not standardized or audited to the same degree as GAAP/IFRS figures, giving management discretion over what to exclude.",
        interpretation="An analyst should always reconcile non-GAAP figures back to GAAP and evaluate whether excluded items are truly non-recurring — persistent, recurring 'adjustments' are a red flag for earnings-quality analysis.",
        related_concepts=("restructuring_charges", "eps_dilution_mechanics"),
    ),
    "deferred_tax": ConceptCard(
        "deferred_tax", M, "Deferred Tax Assets & Liabilities",
        "Balance-sheet items arising from temporary timing differences between when income/expenses are recognized for accounting purposes versus tax purposes.",
        business_meaning="A Deferred Tax Asset represents taxes a company expects to save in the future (e.g. from carried-forward losses); a Deferred Tax Liability represents taxes it expects to owe later (e.g. from accelerated tax depreciation).",
        interpretation="A large Deferred Tax Asset is only valuable if the company expects sufficient future taxable profit to actually use it — auditors require a 'valuation allowance' write-down if that is in doubt.",
        related_concepts=("nopat",),
    ),
    "segment_reporting": ConceptCard(
        "segment_reporting", M, "Segment Reporting",
        "The disclosure of financial results broken down by a company's distinct operating/business segments, rather than only at the consolidated whole-company level.",
        business_meaning="Essential for Sum-of-the-Parts valuation and for identifying which parts of a diversified business are creating versus destroying value, since blended consolidated figures can hide this.",
        interpretation="A company can report healthy consolidated growth while segment data reveals that growth is entirely concentrated in one segment, with others actually declining.",
        related_concepts=("sotp", "diversification"),
    ),
}
