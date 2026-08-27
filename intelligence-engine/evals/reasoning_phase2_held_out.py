"""Phase-2 generalisation evaluation bank.

CRITICAL RULES
--------------
1. NEVER import this module into matchers, composers, or gold patterns.
2. NEVER train on these questions.
3. Use only for evaluation / scorecards.

A high score here means genuine family reasoning.
A mid score with T1–T15 memorisation only means pattern matching.
"""

from __future__ import annotations

from typing import Any

# Each item: id, family, question, must_include (rubric needles), must_not_include,
# forbids_decision (for dual-hyp), sector tag.
HELD_OUT: list[dict[str, Any]] = [
    # ---- Category 1 Banking (Contradiction / Accounting) ----
    {
        "id": "G01",
        "family": "contradiction",
        "sector": "banking",
        "question": "Deposits increased 18%, but CASA ratio declined. Which signal is more important?",
        "must_include": ["casa", "funding", "together"],
        "must_not_include": ["buy", "sell", "target price"],
    },
    {
        "id": "G02",
        "family": "accounting",
        "sector": "banking",
        "question": "Loan growth accelerated, but provisions doubled. What does this suggest?",
        "must_include": ["credit", "provision", "growth"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G03",
        "family": "contradiction",
        "sector": "banking",
        "question": "Advances grew 22%, but net interest margin compressed. Which deserves more attention?",
        "must_include": ["quality", "together"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G04",
        "family": "accounting",
        "sector": "banking",
        "question": "Fee income rose, but slippage ratios worsened. What questions should an analyst ask?",
        "must_include": ["slippage"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G05",
        "family": "contradiction",
        "sector": "banking",
        "question": "Retail loans jumped, but unsecured share of the book also rose. Is this positive?",
        "must_include": ["depends"],
        "must_not_include": ["definitely buy"],
    },
    # ---- Category 2 Manufacturing (Accounting) ----
    {
        "id": "G06",
        "family": "accounting",
        "sector": "manufacturing",
        "question": "Production increased 25%, but inventory increased 40%. What could explain this?",
        "must_include": ["inventory", "demand"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G07",
        "family": "accounting",
        "sector": "manufacturing",
        "question": "Sales increased, but receivables increased twice as fast. What questions should an analyst ask?",
        "must_include": ["receivables", "cash"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G08",
        "family": "accounting",
        "sector": "manufacturing",
        "question": "Gross margin improved, but operating cash flow fell. Can both be true?",
        "must_include": ["cash", "true"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G09",
        "family": "accounting",
        "sector": "manufacturing",
        "question": "Capacity utilisation rose, but finished-goods inventory days also rose. What does this suggest?",
        "must_include": ["inventory"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G10",
        "family": "accounting",
        "sector": "manufacturing",
        "question": "Order book grew, but raw-material inventory surged ahead of sales. Explain possible reasons.",
        "must_include": ["inventory"],
        "must_not_include": ["buy", "sell"],
    },
    # ---- Category 3 Technology ----
    {
        "id": "G11",
        "family": "contradiction",
        "sector": "technology",
        "question": "Revenue grew 30%, but customer growth slowed. Can both be true?",
        "must_include": ["yes", "monetisation"],
        "must_not_include": ["impossible"],
    },
    {
        "id": "G12",
        "family": "contradiction",
        "sector": "technology",
        "question": "Billings rose, but net retention declined. Which signal matters more?",
        "must_include": ["quality", "together"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G13",
        "family": "accounting",
        "sector": "technology",
        "question": "Deferred revenue increased, but free cash flow weakened. What could explain this?",
        "must_include": ["cash"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G14",
        "family": "contradiction",
        "sector": "technology",
        "question": "Cloud revenue accelerated, but deal sizes fell. Is this healthy growth?",
        "must_include": ["depends"],
        "must_not_include": ["definitely"],
    },
    {
        "id": "G15",
        "family": "comparison",
        "sector": "technology",
        "question": "Two SaaS companies grew revenue at the same rate. One burns cash; the other is free-cash-flow positive. Which is stronger?",
        "must_include": ["not enough", "cash"],
        "must_not_include": ["always buy"],
    },
    # ---- Category 4 Macro / Causality ----
    {
        "id": "G16",
        "family": "causality",
        "sector": "macro",
        "question": "Inflation falls but bond yields rise. Explain three possible reasons.",
        "must_include": ["yield"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G17",
        "family": "causality",
        "sector": "macro",
        "question": "The central bank cuts rates, but bank stocks fall. Give three possible explanations.",
        "must_include": ["possible"],
        "must_not_include": ["must buy"],
    },
    {
        "id": "G18",
        "family": "causality",
        "sector": "macro",
        "question": "Crude oil drops 25%. How might this affect airlines, paint makers and oil producers differently?",
        "must_include": ["differ"],
        "must_not_include": ["same for all"],
    },
    {
        "id": "G19",
        "family": "causality",
        "sector": "macro",
        "question": "The rupee weakens sharply. Explain possible effects on IT exporters versus oil importers.",
        "must_include": [],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "G20",
        "family": "causality",
        "sector": "macro",
        "question": "Food inflation rises while core inflation falls. What does this mean for policy interpretation?",
        "must_include": [],
        "must_not_include": ["buy", "sell"],
    },
    # ---- Category 5 Valuation ----
    {
        "id": "G21",
        "family": "valuation",
        "sector": "valuation",
        "question": "Earnings increased 20%, but the P/E ratio fell. Explain how both can happen.",
        "must_include": ["price", "p/e"],
        "must_not_include": ["impossible"],
    },
    {
        "id": "G22",
        "family": "valuation",
        "sector": "valuation",
        "question": "EV/EBITDA expanded while earnings were flat. What could that mean?",
        "must_include": [""],
        "must_not_include": ["buy now"],
    },
    {
        "id": "G23",
        "family": "valuation",
        "sector": "valuation",
        "question": "Two brokers publish DCF fair values that differ by 40%. How should AIG treat them?",
        "must_include": [""],
        "must_not_include": ["average them blindly"],
    },
    {
        "id": "G24",
        "family": "valuation",
        "sector": "valuation",
        "question": "Book value rose, but price-to-book fell. Can both be true?",
        "must_include": ["true"],
        "must_not_include": ["impossible"],
    },
    {
        "id": "G25",
        "family": "evidence",
        "sector": "valuation",
        "question": "One terminal shows forward P/E of 14 and another shows 19 for the same ticker today. What should AIG do?",
        "must_include": [""],
        "must_not_include": ["average them"],
    },
    # ---- Evidence / Uncertainty / Self-critique / Comparison fillers ----
    {
        "id": "G26",
        "family": "evidence",
        "sector": "evidence",
        "question": "A newspaper claims a major contract win, but the exchange has no filing. How should this be weighted?",
        "must_include": ["unverified", "filing"],
        "must_not_include": ["treat as confirmed"],
    },
    {
        "id": "G27",
        "family": "uncertainty",
        "sector": "uncertainty",
        "question": "Quarterly results are delayed by three weeks. What cannot be concluded about the latest quarter?",
        "must_include": ["cannot", "evidence"],
        "must_not_include": ["profit definitely"],
    },
    {
        "id": "G28",
        "family": "self_critique",
        "sector": "self_critique",
        "question": "Challenge the view that margins will keep expanding. What would prove that view wrong?",
        "must_include": ["wrong", "assumption"],
        "must_not_include": ["certainly correct"],
    },
    {
        "id": "G29",
        "family": "comparison",
        "sector": "comparison",
        "question": "Company A and Company B both grew sales 15%. A has higher ROE but much higher debt. Which looks stronger?",
        "must_include": ["not enough", "debt"],
        "must_not_include": ["always a"],
    },
    {
        "id": "G30",
        "family": "dual_hypothesis",
        "sector": "hard",
        "question": (
            "A company's revenue, profit, free cash flow, inventory, debt and share price all "
            "moved in different directions. Produce two equally plausible explanations, explain "
            "what evidence supports each, what evidence contradicts each, and what additional "
            "information would allow you to distinguish between them. Do not decide which "
            "explanation is correct."
        ),
        "must_include": [
            "explanation 1",
            "explanation 2",
            "supports",
            "distinguish",
            "do not decide",
        ],
        "must_not_include": ["the correct explanation is", "therefore buy"],
        "forbids_decision": True,
    },
]

# Expand to ~100 held-out prompts by generating sector/metric variants that stay
# evaluation-only. Templates intentionally differ from T1–T15 wording.
_VARIANT_SEEDS: list[tuple[str, str, str, list[str]]] = [
    ("contradiction", "banking", "Current-account balances rose, but savings-account balances fell. What does the mix shift imply?", ["mix", "quality"]),
    ("contradiction", "banking", "Wholesale deposits surged while retail deposits stagnated. Which funding signal matters more?", ["funding", "quality"]),
    ("accounting", "banking", "Interest income rose, but credit costs jumped. How should an analyst read this?", ["credit", "together"]),
    ("accounting", "banking", "Recoveries improved, but fresh slippages also rose. What could explain both?", [""]),
    ("contradiction", "banking", "Branch productivity rose, but cost-to-income worsened. Is that positive?", ["depends"]),
    ("accounting", "manufacturing", "Volumes rose 12%, but payables stretched significantly. What risks appear?", [""]),
    ("accounting", "manufacturing", "EBITDA grew, but inventory write-downs increased. What questions follow?", ["inventory"]),
    ("accounting", "manufacturing", "Plant utilisation hit a record, but cash conversion cycle lengthened. Explain.", ["cash"]),
    ("accounting", "manufacturing", "Exports rose, but freight costs absorbed most of the gain. What does this suggest?", [""]),
    ("accounting", "manufacturing", "Spare-parts sales rose while finished-goods inventory aged. What might be happening?", ["inventory"]),
    ("contradiction", "technology", "Paid users rose slowly, but average revenue per user jumped. Can both be healthy?", ["yes"]),
    ("contradiction", "technology", "Gross bookings grew, but take-rate declined. Which metric needs more weight?", ["quality"]),
    ("accounting", "technology", "Capitalised software costs rose while free cash flow fell. What should be checked?", ["cash"]),
    ("contradiction", "technology", "Enterprise deals grew, but SMB churn rose. How should this be interpreted?", [""]),
    ("comparison", "technology", "Two platforms show identical revenue growth; only one has rising net retention. Which looks higher quality?", ["not enough"]),
    ("causality", "macro", "Real rates rise while nominal GDP growth slows. Outline sector implications without picking winners.", [""]),
    ("causality", "macro", "Liquidity surplus rises but short-term market rates also firm. Give three reasons this can happen.", ["possible"]),
    ("causality", "macro", "A monsoon shock lifts food prices. How might that transmit to rate expectations?", [""]),
    ("causality", "macro", "Global shipping costs spike. Which domestic manufacturers are more exposed and why?", ["differ"]),
    ("causality", "macro", "Credit growth cools after a rate hike cycle. Explain the causal chain to housing and autos.", [""]),
    ("valuation", "valuation", "EPS guidance was raised, yet the forward multiple compressed. How is that possible?", ["price"]),
    ("valuation", "valuation", "A stock re-rates higher on unchanged near-term earnings. What must investors be pricing?", [""]),
    ("valuation", "valuation", "Price-to-sales fell while sales accelerated. Explain the mechanics.", ["price"]),
    ("evidence", "evidence", "Management slides cite a market-share number that filings do not show. How should AIG treat it?", [""]),
    ("evidence", "evidence", "Two research notes disagree on normalised earnings by 30%. What process should AIG follow?", [""]),
    ("uncertainty", "uncertainty", "Segment disclosures were withdrawn this quarter. What conclusions are blocked?", ["cannot"]),
    ("uncertainty", "uncertainty", "Only nine months of data exist for a newly listed company. What remains unknown?", [""]),
    ("self_critique", "self_critique", "List the assumptions behind a view that demand has bottomed, and how to falsify each.", ["assumption"]),
    ("self_critique", "self_critique", "Argue against the conclusion that cost cutting has permanently lifted margins.", ["wrong"]),
    ("comparison", "comparison", "Firm A grows slower than Firm B but converts more cash. How should quality be compared?", ["cash"]),
    ("comparison", "comparison", "One retailer has higher same-store growth; the other has higher ROIC. What else is needed?", ["not enough"]),
    ("contradiction", "retail", "Footfalls rose, but average ticket size fell. Can the revenue outcome still improve?", [""]),
    ("accounting", "retail", "Same-store sales grew, but inventory aged in seasonal categories. What should be checked?", ["inventory"]),
    ("contradiction", "energy", "Refining throughput rose, but crack spreads collapsed. Which signal dominates?", ["quality"]),
    ("accounting", "energy", "Upstream production rose while receivables from buyers ballooned. What questions follow?", ["receivables"]),
    ("causality", "macro", "A fiscal deficit surprise hits the bond market. Trace effects to banks and infrastructure lenders.", [""]),
    ("valuation", "valuation", "Earnings beat estimates, but enterprise value fell. Explain how EV and earnings can diverge.", [""]),
    ("evidence", "evidence", "A wire service reports promoter pledging changes before the exchange update. How to weight it?", ["unverified"]),
    ("uncertainty", "uncertainty", "Auditor commentary flags estimation uncertainty on receivables. What cannot be treated as settled?", [""]),
    ("self_critique", "self_critique", "What would invalidate the belief that a rate cut automatically helps NBFCs?", ["assumption"]),
    ("dual_hypothesis", "hard", "Revenue is up, profit is flat, FCF is down, inventory is up, debt is up and the share price is up. Give two coherent stories, support and challenge each, and say what would distinguish them. Do not pick a winner.", ["explanation", "distinguish"]),
    ("contradiction", "banking", "Priority-sector lending rose faster than overall advances, but yields fell. Interpret the trade-off.", [""]),
    ("accounting", "manufacturing", "Warranty provisions rose after a strong sales quarter. What does that combination suggest?", [""]),
    ("contradiction", "technology", "AI-related revenue rose quickly while traditional services slowed. Is the company healthier?", ["depends"]),
    ("causality", "macro", "US yields jump. Explain three channels to Indian financial markets without forecasting returns.", ["possible"]),
    ("valuation", "valuation", "Normalised EPS is up, reported EPS is down, and P/E looks cheap on reported numbers. What caution follows?", [""]),
    ("evidence", "evidence", "Company IR says 'record demand' on a call; channel checks are mixed. How should confidence be set?", [""]),
    ("uncertainty", "uncertainty", "Key customer concentration is undisclosed. What portfolio conclusions are unsafe?", ["cannot"]),
    ("comparison", "comparison", "Both chemicals companies show similar EBITDA margins; only one has rising sustaining capex needs. Compare quality.", [""]),
    ("accounting", "manufacturing", "Vendor advances increased alongside higher production. What working-capital questions arise?", [""]),
    ("contradiction", "banking", "Digital transaction volumes soared, but fee income per transaction fell. Which signal is richer?", ["quality"]),
    ("causality", "macro", "A carbon tax is proposed. Sketch differential effects on cement, IT services and renewables.", ["differ"]),
    ("valuation", "valuation", "The stock de-rated after a clean earnings beat. List non-earnings reasons this can happen.", [""]),
    ("self_critique", "self_critique", "Assume the house view is 'balance sheet is conservative'. How could that be wrong?", ["wrong"]),
    ("dual_hypothesis", "hard", "Profit rose, FCF fell, debt fell, inventory rose, and the share price fell. Offer two explanations with supporting and contradicting evidence; do not decide.", ["explanation"]),
    ("contradiction", "healthcare", "Hospital occupancy rose, but average revenue per occupied bed declined. Can earnings still improve?", [""]),
    ("accounting", "healthcare", "Procedure volumes rose while receivables days lengthened with insurers. What should be investigated?", ["receivables"]),
    ("comparison", "comparison", "Two auto OEMs report identical volume growth; one gains share in premium mix. What else is required to rank them?", ["not enough"]),
    ("evidence", "evidence", "An unverified social post claims a plant fire; no exchange disclosure yet. How should AIG respond?", ["unverified"]),
    ("uncertainty", "uncertainty", "Guidance was withdrawn. Which forward statements must now be withheld?", [""]),
    ("causality", "macro", "Employment data softens while wage growth stays firm. Explain why markets can read this two ways.", [""]),
    ("valuation", "valuation", "Cash on the balance sheet rose and EV fell even as equity price was flat. Explain the arithmetic.", [""]),
    ("accounting", "technology", "Stock-based compensation rose sharply while non-GAAP profit looked strong. What cash questions remain?", ["cash"]),
    ("contradiction", "banking", "Deposit rates were cut, but cost of funds still rose. How is that possible?", [""]),
    ("comparison", "comparison", "NBFC A grows AUM faster; NBFC B has lower credit costs. How do you avoid a shallow ranking?", ["not enough"]),
    ("self_critique", "self_critique", "List falsifiers for the claim that inventory build is only seasonal.", ["assumption"]),
    ("accounting", "manufacturing", "Sales rose after deep discounts; receivables quality is unclear. What should an analyst demand?", [""]),
    ("causality", "macro", "A surprise rate pause arrives after markets priced cuts. Give three plausible market reactions without recommending trades.", ["possible"]),
    ("evidence", "evidence", "Annual report footnotes and a press release disagree on contingent liabilities. Which prevails and why?", [""]),
    ("dual_hypothesis", "hard", "Revenue down, profit up, FCF up, inventory down, debt up, share price down. Produce two plausible readings and the evidence that would separate them. Do not conclude.", ["explanation", "do not"]),
]


def _build_bank() -> list[dict[str, Any]]:
    rows = list(HELD_OUT)
    start = len(rows) + 1
    for i, (family, sector, question, needles) in enumerate(_VARIANT_SEEDS):
        rows.append(
            {
                "id": f"G{start + i:02d}",
                "family": family,
                "sector": sector,
                "question": question,
                # Generated variants score family ownership + structure; avoid brittle phrase locks.
                "must_include": [],
                "must_not_include": ["buy now", "sell now", "target price"],
                "forbids_decision": family == "dual_hypothesis",
                "generated_variant": True,
                "family_hint_needles": [n for n in needles if n],
            }
        )
    return rows


EVAL_BANK: list[dict[str, Any]] = _build_bank()

assert len(EVAL_BANK) >= 100, f"expected >=100 held-out questions, got {len(EVAL_BANK)}"
assert all("question" in r and "family" in r for r in EVAL_BANK)

# Guard: this module must never be treated as training data.
NEVER_TRAIN = True
EVALUATION_ONLY = True


def list_held_out() -> list[dict[str, Any]]:
    return list(EVAL_BANK)


__all__ = ["EVAL_BANK", "EVALUATION_ONLY", "HELD_OUT", "NEVER_TRAIN", "list_held_out"]
