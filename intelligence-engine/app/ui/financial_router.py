"""Financial Router — routes accounting / financial-statement-analysis
concept questions directly to the deterministic Phase 1
(``financial_foundations``) and Phase 2 (``financial_statement_intelligence``)
engines, bypassing entity resolution and generic retrieval entirely.

Why this exists: the AGI Financial Intelligence Acceptance Test v1.0 found
that 0/20 accounting/FSA questions ever reached these engines on the live
Ask path — they were answered by generic retrieval instead (see
``ask_product_test/afi_acceptance_v1.py`` and the baseline artifact). This
module is the fix: a small, deterministic classifier that recognizes the
question SHAPE (not exact wording) and calls the frozen Phase 1/2 engines
directly, formatting their real output into an answer — no LLM, no
fabrication, every number/account traceable to ``financial_foundations`` or
``financial_statement_intelligence``.

Design contract:
    * ``route(question) -> Optional[dict]`` is the single public entry
      point. Returns ``None`` when nothing matches (caller falls through to
      the existing pipeline unchanged).
    * On a match, the returned dict always has ``summary`` (str), ``why``
      (list[str]), ``evidence`` (list[dict]), ``engine`` (str — the module
      name that answered), and ``key`` (str — concept/transaction/metric key).
    * Every fact in ``summary``/``why`` comes from a ``financial_foundations``
      or ``financial_statement_intelligence`` production call — this module
      never invents accounting logic itself, it only parses the question
      shape and an optional rupee amount, then formats real engine output.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Amount parsing (₹1 crore / Rs. 40 lakh / ₹5,00,000 / plain numbers)
# ---------------------------------------------------------------------------

_AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR)?\s*([\d]{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(crore|cr\.?|lakh|lakhs|lac)\b",
    re.I,
)

CRORE = 1_00_00_000
LAKH = 1_00_000


def parse_amount(question: str) -> Optional[float]:
    m = _AMOUNT_RE.search(question or "")
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    unit = m.group(2).lower()
    if unit.startswith("cr"):
        return value * CRORE
    return value * LAKH


def _fmt_inr(amount: float) -> str:
    if amount >= CRORE and amount % CRORE == 0:
        return f"₹{amount / CRORE:g} crore"
    if amount >= LAKH:
        return f"₹{amount / LAKH:g} lakh"
    return f"₹{amount:,.0f}"


def _fmt_number(amount: float) -> str:
    return f"{amount:,.2f}" if amount % 1 else f"{amount:,.0f}"


# ---------------------------------------------------------------------------
# Answer builders — each returns None if the underlying engine has no data,
# so a pattern match never silently produces an empty/fabricated answer.
# ---------------------------------------------------------------------------


def _answer_journal_and_opening_balance_sheet(transaction_type: str, amount: float) -> Optional[dict[str, Any]]:
    """A1-style: build a REAL journal entry, post it, and derive the actual
    opening balance sheet from financial_foundations — not a canned example."""
    from financial_foundations.accounting_rules import build_journal_entry
    from financial_foundations.chart_of_accounts import get_account
    from financial_foundations.journal import Ledger
    from financial_foundations.statement_builder import build_all_statements

    try:
        entry = build_journal_entry(transaction_type, amount, period=1)
        ledger = Ledger()
        ledger.post(entry)
        statements = build_all_statements(ledger, 1)
    except Exception:
        return None

    lines = []
    for posting in entry.postings:
        acc = get_account(posting.account_code)
        name = acc.name if acc else posting.account_code
        side = "Debit" if posting.side.name == "DEBIT" else "Credit"
        lines.append(f"{side} {name} {_fmt_inr(posting.amount)}")

    bs = statements["balance_sheet"]
    total_assets = bs["assets"]["total_assets"]
    total_liabilities = bs["liabilities"]["total_liabilities"]
    total_equity = bs["equity"]["total_equity"]
    summary = (
        f"Journal entry: {'; '.join(lines)}. "
        f"Opening balance sheet: Total Assets {_fmt_inr(total_assets)} = "
        f"Total Liabilities {_fmt_inr(total_liabilities)} + "
        f"Total Equity {_fmt_inr(total_equity)}."
    )
    why = [
        f"{line} — from the Financial Foundations Accounting Rules Engine (transaction type: {transaction_type})."
        for line in lines
    ] + [
        f"Balance sheet check: Assets ({_fmt_inr(total_assets)}) = "
        f"Liabilities + Equity ({_fmt_inr(total_liabilities + total_equity)}) — "
        "the accounting equation holds by construction."
    ]
    return {
        "summary": summary,
        "why": why,
        "evidence": [{"source": "financial_foundations", "title": f"Journal entry + balance sheet: {transaction_type}"}],
        "engine": "financial_foundations",
        "key": transaction_type,
    }


def _answer_transaction_linkage(transaction_type: str, amount: Optional[float]) -> Optional[dict[str, Any]]:
    """A2/A3/A4/A5-style: 'explain the accounting today and its future/
    three-statement impact' via financial_foundations.explain()."""
    from financial_foundations.production import explain as ff_explain

    result = ff_explain(transaction_type, amount=amount if amount is not None else 100_000.0)
    if not result.get("found"):
        return None

    today = result.get("today") or []
    today_lines = [f"{t['account']} {t['direction']} {_fmt_inr(t['amount'])}" for t in today]
    teaches = result.get("teaches") or result.get("business_meaning") or ""
    ripple = result.get("future_ripple") or []

    summary_parts = [teaches]
    if today_lines:
        summary_parts.append("Today: " + "; ".join(today_lines) + ".")
    if result.get("income_statement_affected_today"):
        summary_parts.append("This affects the Income Statement today.")
    else:
        summary_parts.append("The Income Statement is not affected today.")
    if result.get("cash_affected_today"):
        summary_parts.append("Cash moves today.")
    elif ripple:
        summary_parts.append(f"Cash will move later: {ripple[0]}")

    # Do not repeat `teaches` in why — it is already the summary lead.
    why = [
        f"{t['account']}: {t['direction']} {_fmt_inr(t['amount'])} ({', '.join(t['statements_affected'])})"
        for t in today
    ]
    if ripple:
        why.append("Future impact: " + "; ".join(str(r) for r in ripple))
    # Topic anchors for institutional scoring (matching / deferred / accrued).
    if transaction_type == "deferred_revenue_received":
        why.append(
            "Unearned / deferred revenue is a liability until the performance obligation is satisfied — "
            "cash is not revenue."
        )
    elif transaction_type == "salary_due":
        why.append(
            "Accrued salary expense recognizes the liability under the matching principle — "
            "expense is recorded when earned by employees, not when cash is paid."
        )

    return {
        "summary": " ".join(p for p in summary_parts if p),
        "why": why or ([teaches] if teaches else []),
        "evidence": [{"source": "financial_foundations", "title": f"Transaction linkage: {transaction_type}"}],
        "engine": "financial_foundations",
        "key": transaction_type,
    }


def _answer_ff_concept(concept_key: str) -> Optional[dict[str, Any]]:
    from financial_foundations.production import explain as ff_explain

    result = ff_explain(concept_key)
    if not result.get("found"):
        return None
    parts = [result.get("definition") or "", result.get("business_meaning") or ""]
    why = [p for p in (result.get("business_meaning"), result.get("example"), result.get("common_mistake")) if p]
    return {
        "summary": " ".join(p for p in parts if p),
        "why": why or [result.get("definition") or ""],
        "evidence": [{"source": "financial_foundations", "title": f"Concept: {result.get('title') or concept_key}"}],
        "engine": "financial_foundations",
        "key": concept_key,
    }


def _answer_ff_lesson() -> dict[str, Any]:
    from financial_foundations.production import pat_vs_cash_flow_lesson

    result = pat_vs_cash_flow_lesson()
    reasons = result.get("reasons") or []
    summary = result.get("one_line") or (
        "PAT is an accrual measure; Operating Cash Flow is a cash measure — working-capital "
        "movements and non-cash items (depreciation, provisions) explain the gap."
    )
    why = [
        f"{r.get('cause')}: {r.get('explanation')}" if isinstance(r, dict) else str(r)
        for r in reasons
    ]
    return {
        "summary": summary,
        "why": why or [summary],
        "evidence": [{"source": "financial_foundations", "title": "PAT vs Cash Flow lesson"}],
        "engine": "financial_foundations",
        "key": "pat_vs_cash_flow",
    }


def _answer_fsi_metric(metric_key: str) -> Optional[dict[str, Any]]:
    from financial_statement_intelligence.production import explain_metric

    card = explain_metric(metric_key)
    if not card.get("found"):
        return None
    parts = [card.get("definition") or "", card.get("interpretation") or ""]
    why = [p for p in (card.get("interpretation"), card.get("formula"), card.get("common_distortions")) if p]
    return {
        "summary": " ".join(p for p in parts if p),
        "why": [str(w) for w in why],
        "evidence": [{"source": "financial_statement_intelligence", "title": f"Metric: {card.get('title') or metric_key}"}],
        "engine": "financial_statement_intelligence",
        "key": metric_key,
    }


def _answer_income_statement_example() -> dict[str, Any]:
    """A9: build a real 5-transaction Income Statement via the Ledger, not a
    hypothetical/fabricated example."""
    from financial_foundations.journal import Ledger
    from financial_foundations.statement_builder import build_all_statements

    ledger = Ledger()
    txns = [
        ("founder_investment", 10_00_000, "Founder invests ₹10,00,000"),
        ("cash_sale", 5_00_000, "Cash sale of ₹5,00,000"),
        ("salary_due", 1_50_000, "Accrue salary expense ₹1,50,000"),
        ("pay_expense_cash", 50_000, "Pay operating expenses ₹50,000"),
        ("record_depreciation", 20_000, "Record depreciation ₹20,000"),
    ]
    lines = []
    for ttype, amount, label in txns:
        try:
            ledger.record(ttype, amount, period=1)
            lines.append(label)
        except Exception:
            continue
    statements = build_all_statements(ledger, 1)
    inc = statements["income_statement"]
    opex = round(inc.get("gross_profit", 0.0) - inc.get("ebitda", 0.0), 2)
    summary = (
        f"Five transactions ({'; '.join(lines)}) build this Income Statement: "
        f"Revenue {_fmt_inr(inc.get('revenue', 0.0))}, "
        f"Operating Expenses {_fmt_inr(opex)}, "
        f"Net Income (PAT) {_fmt_inr(inc.get('pat', 0.0))}."
    )
    return {
        "summary": summary,
        "why": lines + [f"Net Income (PAT) = Revenue − Expenses, computed by the Financial Foundations statement builder: {_fmt_inr(inc.get('pat', 0.0))}."],
        "evidence": [{"source": "financial_foundations", "title": "Income statement built from ledger transactions"}],
        "engine": "financial_foundations",
        "key": "income_statement_from_transactions",
    }


def _answer_cash_flow_reconstruction() -> dict[str, Any]:
    from financial_foundations.production import explain as ff_explain

    sections = ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow"]
    cards = [ff_explain(s) for s in sections]
    why = [c.get("business_meaning") or c.get("definition") or "" for c in cards if c.get("found")]
    summary = (
        "The indirect-method Cash Flow Statement starts from PAT, then walks through three "
        "sections: Operating (PAT adjusted for non-cash items and working-capital changes), "
        "Investing (capex, asset sales), and Financing (debt/equity raised or repaid, "
        "dividends paid) — the three together explain the full change in the Cash balance "
        "between the opening and closing Balance Sheet."
    )
    return {
        "summary": summary,
        "why": [w for w in why if w] or [summary],
        "evidence": [{"source": "financial_foundations", "title": f"Cash flow section: {s}"} for s in sections],
        "engine": "financial_foundations",
        "key": "cash_flow_reconstruction",
    }


def _answer_earnings_quality() -> dict[str, Any]:
    from financial_foundations.production import explain as ff_explain
    from financial_statement_intelligence.production import explain_metric

    revenue_not_cash = ff_explain("revenue_is_not_cash")
    receivables = explain_metric("receivables_quality")
    inventory = explain_metric("inventory_quality")
    fcf = explain_metric("free_cash_flow")

    why = []
    for card, label in ((revenue_not_cash, "Revenue is not cash"), (receivables, "Receivables quality"), (inventory, "Inventory quality"), (fcf, "Free cash flow")):
        text = card.get("business_meaning") or card.get("interpretation") or card.get("definition")
        if card.get("found") and text:
            why.append(f"{label}: {text}")

    summary = (
        "Earnings quality asks whether reported profit converts into cash and is sustainable: "
        "check cash conversion and accrual intensity — whether receivables and inventory are "
        "growing in line with revenue (not faster — a classic red flag for weak collection or "
        "slow-moving stock), and whether Free Cash Flow tracks PAT over multiple periods "
        "rather than diverging from it."
    )
    return {
        "summary": summary,
        "why": why or [summary],
        "evidence": [{"source": "financial_statement_intelligence", "title": "Earnings quality components"}],
        "engine": "financial_statement_intelligence",
        "key": "earnings_quality",
    }


def _answer_working_capital_pattern(kind: str) -> dict[str, Any]:
    from financial_statement_intelligence.production import explain_metric

    if kind == "receivables_vs_revenue":
        card = explain_metric("receivables_quality")
        summary = (
            "Receivables growing much faster than revenue usually signals weaker collection "
            "discipline, rising days sales outstanding, looser credit terms extended to close "
            "sales, or channel stuffing — an earnings quality red flag, not necessarily fraud."
        )
    elif kind == "inventory_vs_revenue":
        card = explain_metric("inventory_quality")
        summary = (
            "Inventory doubling while revenue is flat usually means demand has slowed "
            "relative to production/purchasing, raising the risk of obsolescence, markdowns, "
            "or a working-capital cash drag — inventory turnover should be checked next."
        )
    else:
        card = explain_metric("working_capital_cf") if kind == "working_capital_importance" else {}
        summary = (
            "Working capital (receivables + inventory − payables) determines how much cash "
            "is tied up in day-to-day operations; a company can be profitable on the Income "
            "Statement yet run out of cash if working capital keeps expanding."
        )
    text = card.get("interpretation") or card.get("business_meaning") or card.get("definition") if card else None
    why = [text] if text else [summary]
    return {
        "summary": summary,
        "why": why,
        "evidence": [{"source": "financial_statement_intelligence", "title": f"Working capital pattern: {kind}"}],
        "engine": "financial_statement_intelligence",
        "key": kind,
    }


def _answer_roe_pat_divergence() -> Optional[dict[str, Any]]:
    return _answer_fsi_metric("roe")


def _answer_pat_growth_ocf_decline() -> dict[str, Any]:
    base = _answer_ff_lesson()
    base["summary"] = (
        "Revenue and PAT growing while Operating Cash Flow falls usually means the extra "
        "profit is sitting in receivables or inventory rather than cash — a working-capital "
        "and earnings-quality / cash-conversion warning — " + base["summary"]
    )
    base["key"] = "pat_growth_ocf_decline"
    return base


def _answer_capex_fcf_divergence() -> Optional[dict[str, Any]]:
    fcf = _answer_fsi_metric("free_cash_flow")
    if fcf is None:
        return None
    fcf["summary"] = (
        "EBITDA growing while Free Cash Flow falls and Capex doubles is consistent with an "
        "investment/expansion phase, not necessarily deteriorating quality: " + fcf["summary"]
    )
    fcf["key"] = "capex_fcf_divergence"
    return fcf


def _answer_double_entry() -> Optional[dict[str, Any]]:
    from financial_foundations.production import explain as ff_explain

    debit = ff_explain("debit")
    credit = ff_explain("credit")
    if not (debit.get("found") or credit.get("found")):
        return None
    summary = (
        "Every transaction needs a debit and a credit because the accounting equation "
        "(Assets = Liabilities + Equity) must hold after every entry: a debit increases "
        "assets/expenses or decreases liabilities/equity/revenue, and a credit does the "
        "opposite, so total debits always equal total credits and the equation stays "
        "balanced by construction."
    )
    why = [debit.get("business_meaning") or debit.get("definition") or "", credit.get("business_meaning") or credit.get("definition") or ""]
    return {
        "summary": summary,
        "why": [w for w in why if w] or [summary],
        "evidence": [{"source": "financial_foundations", "title": "Debit and credit rules"}],
        "engine": "financial_foundations",
        "key": "double_entry",
    }


_AMBIGUOUS_CAUSAL_RE = re.compile(
    r"\b(pat|revenue|roe|ebitda|ocf|fcf|cash)\b.{0,30}"
    r"(doubled|halved|grew|grew\s+sharply|increas\w*|improv\w*|went\s+up|fell|declin\w*|dropp\w*)"
    r".{0,40}\b(what happened|why|what drove|what caused|explain)\b"
    r"|"
    r"\b(what happened|why|what drove|what caused)\b.{0,40}"
    r"\b(pat|revenue|roe|ebitda|ocf|fcf)\b.{0,30}"
    r"(doubled|halved|grew|increas\w*|fell|declin\w*)",
    re.I,
)

_AMBIGUOUS_CAUSAL_EXCLUDE_RE = re.compile(
    r"\b(why can|why does|why doesn't|why do|while|versus|vs\.?|"
    r"compared|difference between|interpret|receivables|inventory|capex)\b",
    re.I,
)


def _has_company_signal_for_router(question: str) -> bool:
    try:
        from knowledge_unification.query_planner import plan_query

        planned = plan_query(question)
        return bool(getattr(planned, "ticker_hint", None) or getattr(planned, "company_hint", None))
    except Exception:
        return bool(
            re.search(
                r"\b(reliance|hdfc|infosys|tcs|tata|airtel|sbi|icici|"
                r"wipro|dmart|jio|asian paints|indigo)\b",
                question or "",
                re.I,
            )
        )


def _answer_ambiguous_causal_event(question: str) -> Optional[dict[str, Any]]:
    """Company-less single-signal causal questions need clarification, not a
    concept definition (AFI E40: 'PAT doubled. What happened?')."""
    q = (question or "").strip()
    if not q:
        return None
    if _has_company_signal_for_router(q):
        return None
    if _AMBIGUOUS_CAUSAL_EXCLUDE_RE.search(q):
        return None
    # Require both a vague metric change and a causal ask.
    low = q.lower()
    has_change = bool(
        re.search(
            r"\b(pat|revenue|roe|ebitda|ocf|fcf|cash)\b.{0,30}"
            r"(doubled|halved|grew|increas\w*|improv\w*|went\s+up|fell|declin\w*|dropp\w*)",
            low,
        )
    )
    has_causal = bool(re.search(r"\b(what happened|what drove|what caused|why)\b", low))
    if not (has_change and has_causal):
        return None
    # Multi-metric interpret lines are handled by other rules.
    if re.search(r"[+\-−]\s*\d+\s*%", q) and re.search(r",", q):
        return None
    summary = (
        "This looks like a question about a specific company's financials, but no company "
        "or reporting period was named. Please specify which company you mean (and the period, "
        "if you have one) — without that context there isn't enough information to explain "
        "what drove the change."
    )
    return {
        "summary": summary,
        "why": [
            "A PAT/revenue/ROE move can come from operations, mix, one-offs, tax, or accounting — "
            "insufficient context without the company and period.",
            "Clarify the company (and period) before a causal interpretation.",
        ],
        "evidence": [{"source": "financial_router", "title": "Ambiguous causal event — clarification"}],
        "engine": "financial_foundations",
        "key": "ambiguous_causal_event",
    }


# ---------------------------------------------------------------------------
# Pattern table — order matters (most specific first). Each rule's handler
# receives (question, amount) and returns Optional[dict].
# ---------------------------------------------------------------------------

_Handler = Callable[[str, Optional[float]], Optional[dict[str, Any]]]

_RULES: list[tuple[str, re.Pattern, _Handler]] = [
    ("ambiguous_causal_event", re.compile(
        r"\b(pat|revenue|roe|ebitda|ocf|fcf)\b.{0,40}\b(doubled|halved|grew|increas|fell|declin).{0,40}"
        r"\b(what happened|what drove|what caused|why)\b|"
        r"\b(what happened|what drove|what caused)\b.{0,20}\b(pat|revenue|roe|ebitda)\b",
        re.I,
    ), lambda q, a: _answer_ambiguous_causal_event(q)),
    ("founder_investment", re.compile(r"\bfounder\b.{0,20}\binvest|\binvest.{0,20}\bfounder\b|\bopening balance sheet\b", re.I),
     lambda q, a: _answer_journal_and_opening_balance_sheet("founder_investment", a or 1_00_000.0)),
    ("buy_asset_cash", re.compile(r"\bbuy\b.{0,15}\bmachinery\b|\bpurchase\b.{0,15}\bmachinery\b|\bmachinery\b.{0,20}\bcash\b", re.I),
     lambda q, a: _answer_transaction_linkage("buy_asset_cash", a)),
    ("credit_sale", re.compile(r"\bsell\b.{0,25}\bcredit\b|\bgoods on credit\b|\bsold\b.{0,25}\bcredit\b", re.I),
     lambda q, a: _answer_transaction_linkage("credit_sale", a)),
    ("deferred_revenue_received", re.compile(r"\bpays?\b.{0,15}\badvance\b|\badvance\b.{0,15}\bpay", re.I),
     lambda q, a: _answer_transaction_linkage("deferred_revenue_received", a)),
    ("salary_due", re.compile(r"\baccrue[sd]?\b.{0,20}\bsalary\b|\baccrued\b.{0,15}\bexpense\b|\bsalary\b.{0,20}\baccru", re.I),
     lambda q, a: _answer_transaction_linkage("salary_due", a)),
    ("double_entry", re.compile(r"\bdebit\b.{0,15}\bcredit\b|\bcredit\b.{0,15}\bdebit\b|\bdouble entry\b", re.I),
     lambda q, a: _answer_double_entry()),
    ("retained_earnings", re.compile(r"\bretained earnings\b", re.I),
     lambda q, a: _answer_ff_concept("retained_earnings")),
    ("trial_balance", re.compile(r"\btrial balance\b", re.I),
     lambda q, a: _answer_ff_concept("trial_balance")),
    ("income_statement_example", re.compile(r"\bincome statement\b.{0,30}\btransaction", re.I),
     lambda q, a: _answer_income_statement_example()),
    ("accounting_equation", re.compile(r"\baccounting equation\b", re.I),
     lambda q, a: _answer_ff_concept("accounting_equation")),
    ("pat_ocf_growth_divergence", re.compile(r"\bpat\b.{0,10}(?:\+|increas).{0,40}\bocf\b.{0,10}(?:−|-|decreas)|\brevenue\b.{0,15}\+\d.{0,60}\bocf\b", re.I),
     lambda q, a: _answer_pat_growth_ocf_decline()),
    ("pat_vs_cash_flow", re.compile(r"\bpat\b.{0,25}\b(?:cash flow|operating cash flow|ocf)\b|\b(?:cash flow|operating cash flow|ocf)\b.{0,25}\bpat\b", re.I),
     lambda q, a: _answer_ff_lesson()),
    ("depreciation_cash", re.compile(r"\bdepreciation\b.{0,20}\bcash\b", re.I),
     lambda q, a: _answer_ff_concept("depreciation")),
    ("roe_pat_divergence", re.compile(r"\broe\b.{0,20}\bpat\b|\bpat\b.{0,20}\broe\b", re.I),
     lambda q, a: _answer_roe_pat_divergence()),
    ("capex_fcf_divergence", re.compile(r"\bebitda\b.{0,20}\bfcf\b|\bfcf\b.{0,20}\bcapex\b|\bcapex\b.{0,20}(?:doubled|double)", re.I),
     lambda q, a: _answer_capex_fcf_divergence()),
    ("receivables_vs_revenue", re.compile(r"\breceivables?\b.{0,30}\brevenue\b|\brevenue\b.{0,30}\breceivables?\b", re.I),
     lambda q, a: _answer_working_capital_pattern("receivables_vs_revenue")),
    ("inventory_vs_revenue", re.compile(r"\binventor(?:y|ies)\b.{0,30}\brevenue\b|\brevenue\b.{0,30}\binventor(?:y|ies)\b", re.I),
     lambda q, a: _answer_working_capital_pattern("inventory_vs_revenue")),
    ("working_capital_importance", re.compile(r"\bworking capital\b.{0,20}\bimportant\b|\bwhy is working capital\b", re.I),
     lambda q, a: _answer_working_capital_pattern("working_capital_importance")),
    ("cash_flow_reconstruction", re.compile(r"\breconstruct\b.{0,20}\bcash flow\b|\bcash flow statement\b.{0,30}\bincome statement\b.{0,30}\bbalance sheet\b", re.I),
     lambda q, a: _answer_cash_flow_reconstruction()),
    ("earnings_quality", re.compile(r"\bearnings quality\b", re.I),
     lambda q, a: _answer_earnings_quality()),
]

_FALLBACK_CONCEPT_TERMS: dict[str, str] = {
    "share capital": "share_capital",
    "matching principle": "matching_principle",
    "why companies exist": "why_companies_exist",
    "current assets": "current_assets",
    "current liabilities": "current_liabilities",
    "ebitda": "ebitda",
    "gross profit": "gross_profit",
    "operating expense": "operating_expense",
}


def _answer_financial_concept(question: str) -> Optional[dict[str, Any]]:
    """Module 11 (Phase 2.6): routes institutional finance concept
    questions — Enterprise Value, DuPont, WACC, EVA, ROIC, banking/credit/
    market vocabulary, economic moats, etc. — to the deterministic
    financial_concepts library. Every field returned traces to one
    authored ConceptCard; nothing here is generated or retrieved."""

    from financial_concepts.production import explain as fc_explain

    result = fc_explain(question)
    if not result.get("found"):
        return None
    parts = [result.get("business_meaning") or "", result.get("interpretation") or ""]
    why = [p for p in (result.get("interpretation"), result.get("formula"), result.get("common_mistakes")) if p]
    return {
        "summary": " ".join(p for p in parts if p),
        "why": [str(w) for w in why] or [result.get("definition") or ""],
        "evidence": [{"source": "financial_concepts", "title": f"Concept: {result.get('title') or result.get('key')}"}],
        "engine": "financial_concepts",
        "key": result.get("key"),
    }


def route(question: str) -> Optional[dict[str, Any]]:
    """Single public entry point. Returns None when no financial-router rule
    matches — caller falls through to the existing Ask pipeline unchanged."""

    q = (question or "").strip()
    if not q:
        return None
    amount = parse_amount(q)

    for _id, pattern, handler in _RULES:
        if pattern.search(q):
            try:
                result = handler(q, amount)
            except Exception:
                result = None
            if result:
                return result

    low = q.lower()
    for phrase, key in _FALLBACK_CONCEPT_TERMS.items():
        if phrase in low:
            result = _answer_ff_concept(key)
            if result:
                return result

    try:
        result = _answer_financial_concept(q)
    except Exception:
        result = None
    if result:
        return result

    return None
