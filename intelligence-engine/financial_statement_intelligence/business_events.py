"""Business Events — Institutional Accounting Exam Section H.

Structured three-statement impact explanations for advanced events that
sit beyond Phase 1's basic 28-transaction catalog (some require account
types — Right-of-Use Assets, Deferred Tax Assets — that a foundational
chart of accounts does not carry). Each event gets the same rigor as
Phase 1's linkage engine: today's impact across IS/BS/CF, the future
ripple, the governing accounting principle, and the most common
misconception — never a bare description.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BusinessEvent:
    key: str
    title: str
    income_statement_today: str
    balance_sheet_today: str
    cash_flow_today: str
    future_ripple: str
    governing_principle: str
    common_misconception: str


BUSINESS_EVENTS: dict[str, BusinessEvent] = {
    "inventory_writeoff": BusinessEvent(
        "inventory_writeoff", "Inventory Written Off",
        "An inventory write-off expense reduces EBIT (and PAT) immediately for the full write-off amount.",
        "Inventory (asset) decreases by the write-off amount; no liability or cash account is touched.",
        "No cash effect today — this is a non-cash charge, exactly like depreciation, and is added "
        "back when computing Operating Cash Flow via the same working-capital mechanism (Inventory decrease "
        "shows up as a source of cash in the indirect method, offsetting the PAT hit).",
        "None going forward — the loss is fully recognised today; there is no future depreciation-style "
        "drag, unlike a fixed-asset purchase.",
        "Matching principle in reverse: once inventory is judged unsellable at cost, its carrying value "
        "must be written down immediately (lower of cost or net realisable value) rather than carried "
        "at an overstated value until eventually sold at a loss.",
        "Believing a write-off reduces cash — it does not; the cash was already spent when the inventory "
        "was originally purchased.",
    ),
    "share_buyback": BusinessEvent(
        "share_buyback", "Share Buyback",
        "No Income Statement effect — a buyback is a capital transaction with owners, never an expense "
        "or a reduction of revenue.",
        "Cash decreases and Treasury Stock (a contra-equity account) increases by the purchase price — "
        "Total Equity decreases by the same amount, and the number of shares outstanding falls.",
        "A Financing outflow — cash returned to shareholders through the capital markets, not through operations.",
        "EPS rises mechanically going forward purely from the smaller share count (same PAT divided by "
        "fewer shares), and ROE rises from the smaller equity base — neither reflects an operating improvement.",
        "A buyback reduces Equity, not a liability — the company owes shareholders nothing; it has simply "
        "returned capital and cancelled/held the repurchased shares.",
        "Assuming a buyback is 'accretive' to fundamentals — it mechanically improves per-share metrics "
        "without changing the underlying business at all; always decompose EPS/ROE gains from a buyback "
        "period before crediting operating performance.",
    ),
    "convertible_debt_converts": BusinessEvent(
        "convertible_debt_converts", "Convertible Debt Converts to Equity",
        "No Income Statement effect from the conversion itself — going forward, Interest Expense on the "
        "converted portion disappears, which will raise EBIT-to-PAT flow-through in future periods.",
        "The Debt liability is extinguished and Share Capital increases by the same amount — Total "
        "Liabilities fall and Total Equity rises; Total Assets are unchanged (the accounting equation "
        "still holds because one side simply moved from liability to equity).",
        "No cash effect — this is a non-cash reclassification between the liability and equity sections "
        "of the Balance Sheet; the cash was already received when the convertible was originally issued.",
        "Share count rises (dilution), so EPS calculated going forward divides a similar PAT (now "
        "slightly higher from lower interest expense) by more shares — the net EPS effect depends on "
        "which force dominates.",
        "A convertible is debt until conversion and equity after — it should never be shown as both, and "
        "the conversion itself is a Balance-Sheet-only reclassification, not a financing cash inflow.",
        "Believing conversion brings in new cash — it does not; the cash was raised when the convertible "
        "bond was first issued, not when it later converts.",
    ),
    "asset_impairment": BusinessEvent(
        "asset_impairment", "Asset Impairment",
        "An impairment loss reduces EBIT (and PAT) immediately by the write-down amount — usually shown "
        "as a distinct non-operating or 'exceptional' line so analysts can strip it out for a normalised view.",
        "The impaired asset (PPE, Goodwill, or Intangibles) decreases by the write-down amount; Retained "
        "Earnings falls by the same amount through the PAT hit at year-end close.",
        "No cash effect today — like depreciation, an impairment is a non-cash charge and should be "
        "added back when computing Operating Cash Flow.",
        "Future Depreciation Expense on the impaired asset falls (a smaller carrying value depreciates "
        "less each period), partially offsetting future PAT versus what it would have been without the "
        "impairment.",
        "Assets are carried at the lower of cost (net of depreciation) and recoverable value — an "
        "impairment recognises economic reality that has already occurred, it does not create new economic loss.",
        "Treating an impairment as a 'one-off that doesn't matter' — while it is non-cash and often "
        "excluded from adjusted PAT, a LARGE or REPEATED impairment history is itself a red flag about "
        "the quality of prior capital-allocation decisions (the asset was overpaid for or over-invested in).",
    ),
    "deferred_tax_asset_recognized": BusinessEvent(
        "deferred_tax_asset_recognized", "Deferred Tax Asset Recognised",
        "Tax Expense falls (and PAT rises) in the period the DTA is recognised, reflecting an expected "
        "future tax benefit being pulled into the current period's Income Statement.",
        "A Deferred Tax Asset increases on the Balance Sheet (an asset representing future tax savings); "
        "Retained Earnings rises through the PAT effect.",
        "No cash effect today — no cash tax was actually saved yet; the benefit is only realised in "
        "future periods when the company actually uses the DTA to reduce a real cash tax payment.",
        "In the future period the DTA is utilised, Cash Tax Paid will be lower than the P&L Tax Expense "
        "would otherwise suggest — but this future cash benefit was already 'pulled forward' into PAT today.",
        "A DTA is only recognised when it is 'probable' the company will have sufficient future taxable "
        "profit to use it — recognising one implies management's forecast of future profitability.",
        "Believing a DTA is cash in the bank — it is a claim on FUTURE tax savings, contingent on the "
        "company actually being profitable enough later to use it; a DTA can be written down (reversing "
        "the PAT benefit) if that profitability doesn't materialise.",
    ),
    "lease_under_ifrs16": BusinessEvent(
        "lease_under_ifrs16", "Operating Lease Capitalised Under IFRS 16 / Ind AS 116",
        "Rent Expense (a single operating-expense line) disappears and is replaced by Depreciation "
        "(on the Right-of-Use asset) plus Interest Expense (on the lease liability) — EBITDA rises "
        "mechanically (rent moves below the EBITDA line) even though nothing about the business changed.",
        "A Right-of-Use Asset and a matching Lease Liability both appear on the Balance Sheet at the "
        "present value of future lease payments — both Total Assets and Total Liabilities rise.",
        "No day-one cash effect from capitalisation itself; the actual lease payments are now split "
        "between an Operating (interest portion) and a Financing (principal repayment portion) cash "
        "outflow, instead of one lump Operating outflow as before.",
        "Interest Expense declines over the lease term as the liability amortises (like any amortising "
        "loan), while Depreciation on the Right-of-Use asset is typically straight-line — so the total "
        "P&L charge front-loads higher in early years versus the old operating-lease treatment.",
        "IFRS 16 / Ind AS 116 exists because operating leases were previously a major source of "
        "off-balance-sheet leverage — the standard forces nearly all leases onto the Balance Sheet so "
        "leverage metrics reflect economic reality.",
        "Comparing EBITDA/EBITDA-margin before and after a company adopts IFRS 16 as if it reflects "
        "operating improvement — the mechanical reclassification of rent into D&A and interest inflates "
        "EBITDA with zero change in the underlying business.",
    ),
    "acquisition_at_premium": BusinessEvent(
        "acquisition_at_premium", "Acquisition at a Premium to Net Assets",
        "No immediate Income Statement effect from the premium itself; going forward, any incremental "
        "depreciation/amortisation on fair-valued acquired assets reduces future EBIT, though Goodwill "
        "itself is NOT amortised (only tested annually for impairment) under most modern accounting standards.",
        "Goodwill increases by the amount paid above the fair value of net identifiable assets acquired; "
        "Cash decreases (if funded in cash) and/or Debt/Share Capital increases (if funded by borrowing "
        "or issuing shares) by the total consideration.",
        "A large Investing outflow (or non-cash if funded entirely by issuing shares) equal to the "
        "purchase consideration, net of any cash acquired with the target.",
        "The Goodwill balance sits on the Balance Sheet indefinitely until either the acquisition proves "
        "its worth (through the acquired business's earnings) or an impairment test concludes it must be "
        "written down — concentrating future one-off PAT risk.",
        "Goodwill = Purchase Price − Fair Value of Net Identifiable Assets Acquired; it represents the "
        "value of synergies, brand, and workforce the acquirer is willing to pay above the target's "
        "identifiable net assets.",
        "Assuming a large Goodwill balance means the acquirer overpaid — it may simply reflect a "
        "genuinely valuable, asset-light target (e.g. a software or services business) where most of "
        "the value was never on the target's own balance sheet to begin with.",
    ),
    "foreign_currency_loss": BusinessEvent(
        "foreign_currency_loss", "Foreign Currency Translation/Transaction Loss",
        "A transaction FX loss (e.g. on a foreign-currency payable/receivable or foreign-currency debt) "
        "reduces PAT directly, typically below EBIT as a non-operating item — it should not be confused "
        "with operating performance.",
        "The FX loss reduces the value of the underlying foreign-currency asset/liability being "
        "remeasured, and Retained Earnings falls through the PAT effect (a pure translation loss on "
        "a foreign subsidiary instead flows through an Equity reserve, bypassing the Income Statement "
        "entirely, depending on the accounting treatment).",
        "No cash effect from the remeasurement itself — it is a non-cash revaluation; cash only moves "
        "when the underlying foreign-currency item is actually settled at the prevailing rate.",
        "If the underlying exposure (e.g. foreign-currency debt) remains outstanding, further currency "
        "moves will continue to generate translation gains/losses each period until it is settled or hedged.",
        "Monetary assets/liabilities denominated in a foreign currency are remeasured at each period-end "
        "using the closing exchange rate — the resulting gain/loss reflects currency movement, not "
        "operating performance.",
        "Treating an FX loss as evidence of operational weakness — it is a financing/translation effect "
        "driven by currency markets, and should be assessed (and typically excluded) separately from "
        "the underlying business's operating trend.",
    ),
}


def explain_event(key: str) -> dict:
    ev = BUSINESS_EVENTS.get(key)
    if not ev:
        return {"found": False, "key": key}
    return {
        "found": True,
        "key": ev.key,
        "title": ev.title,
        "income_statement_today": ev.income_statement_today,
        "balance_sheet_today": ev.balance_sheet_today,
        "cash_flow_today": ev.cash_flow_today,
        "future_ripple": ev.future_ripple,
        "governing_principle": ev.governing_principle,
        "common_misconception": ev.common_misconception,
    }


def list_events() -> list[str]:
    return sorted(BUSINESS_EVENTS.keys())


def all_events() -> list[dict]:
    return [explain_event(k) for k in list_events()]
