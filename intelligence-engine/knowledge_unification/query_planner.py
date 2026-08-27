"""Module 2 — Query Planner (deterministic question typing)."""

from __future__ import annotations

import re
from typing import Optional

from knowledge_unification.schema import QueryPlan

_CONCEPT_RE = re.compile(
    r"\b(explain|what is|what are|define|definition of|meaning of)\b",
    re.I,
)
_ACCOUNTING_RE = re.compile(
    r"\b(journal|debit|credit|balance sheet|income statement|retained earnings|"
    r"double entry|trial balance|ledger|accrual|depreciation|amortisation|amortization)\b",
    re.I,
)
_FSA_RE = re.compile(
    r"\b(financial statement|read the (p&l|pnl|balance sheet)|cash flow statement|"
    r"working capital|days sales|inventory days|dupont|"
    r"earnings quality|receivables|inventory doubles|ocf|operating cash|"
    r"reconstruct the cash flow|interpret\.?$)\b",
    re.I,
)
_FSA_SHAPE_RE = re.compile(
    r"(%|％).{0,40}(%|％)|"
    r"\b(revenue|pat|ebitda|fcf|ocf|capex|receivables|inventory)\b.{0,30}"
    r"(\+|−|-|up|down|flat|doubled|grew|falling)",
    re.I,
)
_VALUATION_RE = re.compile(
    r"\b(valuation|valued|enterprise value|equity value|dcf|ev/?ebitda|ev/?sales|"
    r"p/?b|price.to.book|p/e|pe ratio|wacc|terminal value|embedded value|\bnav\b)\b",
    re.I,
)
_BUSINESS_RE = re.compile(
    r"\b(business model|membership model|how does .+ make money|how .+ (?:make|makes) money|"
    r"products?|competitors?|moat|segments?|revenue stream|monetis\w*|monetiz\w*|"
    r"cost advantages?|growth drivers?|what drives growth)\b",
    re.I,
)
_MOAT_RE = re.compile(
    r"\b(moat|competitive advantage|pricing power|premium pricing|"
    r"sustain premium|switching costs?|network effects?|"
    r"scale advantages?|customer lock[- ]?in|brand moat|distribution moat|"
    r"licensing moat|why is .+ considered to have a strong moat|"
    r"able to sustain)\b",
    re.I,
)
_UNIT_ECON_RE = re.compile(
    r"\b(unit economics|contribution margin|cac|ltv|payback|cash conversion|"
    r"airline economics|saas unit|fmcg cash|industry economics|"
    r"low[- ]margin|strong cash flow|working capital|"
    r"capital intens\w*|operating leverage|scale differently|"
    r"why do .+ (earn|generate|use|carry|scale))\b",
    re.I,
)
_COMPARISON_RE = re.compile(
    r"\b(compare|vs\.?|versus|more profitable than|higher margins than|"
    r"better margins than|better than|differently from|\bvs\b)\b",
    re.I,
)
_INDUSTRY_NAME_RE = re.compile(
    r"\b(banks?|nbfcs?|saas|software|airlines?|railways?|fmcg|utilities|"
    r"hospitals?|telecoms?|cement|insurance|insurers?|retail|it services|"
    r"chemicals?|diagnostics?|metals?|mining|pharma|real estate|realty|"
    r"power utilities|renewables?|oil\s*&?\s*gas|qsr|logistics|shipping)\b",
    re.I,
)
_GROWTH_RE = re.compile(
    r"\b(what drives growth|growth drivers?|drives growth|growth modes?|"
    r"pricing-led|volume-led|capacity expansion)\b",
    re.I,
)
_VALUE_DRIVER_RE = re.compile(
    r"\b(value drivers?|key drivers?|what drives)\b",
    re.I,
)
_MANAGEMENT_RE = re.compile(
    r"\b(management quality|capital allocat\w*|governance|shareholder friendl)\b",
    re.I,
)
_INVESTMENT_RE = re.compile(
    r"\b(investment thesis|investment (quality|risks?|case|perspective|monitoring|lens)|"
    r"from an investment (perspective|lens)|for an investor|"
    r"how should investors monitor|investors? (should )?monitor|"
    r"monitoring (priorities|points)|key investment monitoring|"
    r"key catalysts?|biggest catalysts?|catalysts? for|"
    r"bull,? base,? and bear|bull and bear|bear cases?|base scenarios?|"
    r"scenario analysis|scenarios?\b|"
    r"investment committee|committee simulation|evidence strength|"
    r"why is (this|the) company attractive|downside( risks?)?|"
    r"major investment risks?|what could (improve|rerate)|"
    r"why might roic|roic improve|"
    r"quality scorecard|investment implications|"
    r"what drives valuation|valuation drivers?|"
    r"business quality|quality perspective|"
    r"unknowns? remain|so what does .+ mean for an investor)\b",
    re.I,
)
_INVESTMENT_VERB_RE = re.compile(r"\b(evaluate|assess|analy[sz]e)\b", re.I)
_BUSINESS_RISK_RE = re.compile(
    r"\b(biggest risks?|business risks?|key risks?|risks? matter|"
    r"why are .+ cyclical|cyclical|"
    r"concentration risk|commodity risk|regulatory risk|"
    r"investment risks?|downside risks?)\b",
    re.I,
)
_INDUSTRY_RE = re.compile(
    r"\b(industry|sector|peers?|competitive (?:landscape|structure)|"
    r"industry structure|porter|five forces|"
    r"entry barriers?|supplier power|customer power|buyer power|oligopol\w*|"
    r"duopol\w*|fragmented|spectrum|regulator|regulates?|"
    r"nim|casa|arpob|load factor|rask|cask|sssg|cet1|gnpa|"
    r"utilization|attrition|billing rate|offshore mix|nrr|cac|"
    r"cycle matters|credit cycle|commodity cycle|housing cycle|"
    r"industry dna|industry kpi)\b",
    re.I,
)
# Sell-side / broker consensus — Capital IQ market data, answered from the
# valuation_consensus store rather than AGI's own analytical engines.
_CONSENSUS_RE = re.compile(
    r"\b(consensus|analyst consensus|street (?:view|estimate|target)|sell[- ]side|"
    r"broker (?:estimate|consensus|recommendation|rating|coverage)|brokerages?|"
    r"target price|price target|consensus target|mean target|"
    r"analyst (?:target|rating|recommendation|coverage|estimate|opinion)|"
    r"how many (?:analysts?|brokers?)|analysts? cover|coverage count|"
    r"buy(?:/| |,| and )?(?:hold|sell)(?: |/|,|and )*(?:sell|ratings?|recommendations?)|"
    r"buy ratings?|sell ratings?|hold ratings?|outperform ratings?|"
    r"upside to target|potential upside|implied upside|consensus upside)\b",
    re.I,
)
# Market-wide consensus screens ("highest upside", "most covered") — no ticker.
_CONSENSUS_SCREEN_RE = re.compile(
    r"\b(highest|lowest|most|least|top|best|worst|widest|biggest)\b.{0,40}"
    r"\b(upside|target|coverage|covered|buy|sell|hold|consensus|conviction)\b|"
    r"\b(upside|coverage|covered|consensus)\b.{0,30}\b(across|in the|by sector|universe|market)\b",
    re.I,
)
_MACRO_RE = re.compile(
    r"\b(macro|gdp|inflation|interest rate|rbi|fed|risk premium|country premium|"
    r"rate cut|rate hike|basis point|repo rate|nbfc)\b",
    re.I,
)
# Pure definitions of macro-finance terms belong to concepts/academy, not MIE.
_MACRO_CONCEPT_TERM_RE = re.compile(
    r"\b(equity risk premium|country risk premium|risk premium|inflation|"
    r"cost of equity|gdp|interest rate)\b",
    re.I,
)
_MARKET_RE = re.compile(
    r"\b(price|return|returns|market cap|volume|earnings date|ytd|"
    r"market breadth|sector rotation|institutional flows|today'?s (?:indian )?market|"
    r"market summary|indian market)\b",
    re.I,
)
_FORECAST_RE = re.compile(
    r"\b(forecast|outlook|bull case|bear case|base case|bull,? base,? and bear|"
    r"next 3(?:\s*[–-]\s*5)? years|scenario probabilities|forecast confidence)\b",
    re.I,
)
_HISTORICAL_VAL_RE = re.compile(
    r"\b(historical valuation|own history|similar to today|when has|when was|"
    r"ever traded|what happened afterwards|percentile|versus history|vs\.? history)\b",
    re.I,
)
_ATTRIBUTION_RE = re.compile(
    r"\b(attribute|attribution|break down the premium|decompose|"
    r"trades? at a premium|trading at a premium|premium valuation|"
    r"what explains the|valuation drivers?)\b",
    re.I,
)
_SCREEN_RE = re.compile(
    r"\b(hedge fund|screen for|find (?:high-quality|companies)|compounders?|"
    r"which (?:stocks|companies)|strategy screen|factor screen|"
    r"rising institutional ownership|attractive valuation)\b",
    re.I,
)
_COMPANY_INTEL_RE = re.compile(
    r"\b(institutional equity analyst|complete company intelligence|"
    r"investment committee|ic report|committee report|research report|"
    r"as if you were|dossier|key monitoring points|"
    r"observed,? derived,? and inferred)\b",
    re.I,
)
_PORTFOLIO_RE = re.compile(
    r"\b(portfolio|position sizing|risk budget|factor exposure|concentration|"
    r"rebalanc\w*|portfolio construction|portfolio quality|portfolio scenario|"
    r"watchlist|agib core|concentrated growth)\b",
    re.I,
)
_RESEARCH_RE = re.compile(
    r"\b(annual report|earnings (call|transcript)|conference call|transcript|"
    r"management (commentary|intelligence|philosophy)|"
    r"guidance (history|evolved|vs|intelligence)|"
    r"research memory|deep research|cross-?document|investor day|"
    r"(research )?timeline intelligence|research timeline|"
    r"what changed since|last quarter|five years of|5 years of|"
    r"from the annual report|capital allocation evolution|"
    r"estimate (intelligence|changes)|event (intelligence|research)|"
    r"structured research|research workspace|from .+ event research)\b",
    re.I,
)
_NEWS_RE = re.compile(r"\b(news|latest|recent|announced|filing|transcript)\b", re.I)

_FINANCE_TERMS = re.compile(
    r"\b(ebitda|ebit|roic|roe|roa|fcf|free cash flow|enterprise value|wacc|capex|"
    r"working capital|gross margin|operating margin|nim|npa|casa|book value)\b",
    re.I,
)


def _detect_company_hint(question: str) -> tuple[Optional[str], Optional[str]]:
    """Return (company_hint, ticker_hint) using Entity Intelligence then CapIQ.

    Entity Intelligence is authoritative: private / insufficient / forbidden
    binds must never surface a CapIQ substitute (e.g. Air India → BHARTIARTL).
    """
    try:
        from entity_intelligence.production import analyse as ei_analyse
        from entity_intelligence.production import validate_bound_ticker

        contract = ei_analyse(question) or {}
        if contract.get("state") == "verified_entity" and contract.get("allow_planner"):
            tk = contract.get("ticker")
            name = contract.get("canonical_name")
            if tk:
                return name, str(tk).upper()
        if contract.get("state") in {
            "clarification_required",
            "unsupported_entity",
        } or (
            contract.get("state") == "verified_entity" and not contract.get("allow_planner")
        ):
            # Explicitly no ticker — block CapIQ substitution.
            return None, None
        # If EI verified a public entity without ticker somehow, still block CapIQ forbid list.
        tentative = None
        try:
            from app.ui.company_router import detect_ikt_company

            tentative = detect_ikt_company(question)
        except Exception:
            tentative = None
        if tentative and not validate_bound_ticker(contract, tentative):
            return None, None
    except Exception:
        pass

    ticker = None
    company = None
    try:
        from app.ui.company_router import detect_ikt_company

        ticker = detect_ikt_company(question)
    except Exception:
        ticker = None
    if ticker:
        try:
            from institutional_knowledge_tables.store import get_table

            row = (get_table(ticker, "company_master").get("row") or {}).get("company_name") or {}
            company = row.get("value") if isinstance(row, dict) else None
        except Exception:
            company = None
        return company, ticker

    # Alias seed / common names (longest match first)
    aliases = {
        "state bank of india": "SBIN",
        "avenue supermarts": "DMART",
        "asian paints": "ASIANPAINT",
        "reliance retail": "RELIANCE",
        "hdfc bank": "HDFCBANK",
        "icici bank": "ICICIBANK",
        "axis bank": "AXISBANK",
        "jsw steel": "JSWSTEEL",
        "interglobe": "INDIGO",
        "adani enterprises": "ADANIENT",
        "larsen & toubro": "LT",
        "larsen and toubro": "LT",
        "tata motors": "TATAMOTORS",
        "reliance": "RELIANCE",
        "infosys": "INFY",
        "wipro": "WIPRO",
        "dmart": "DMART",
        "indigo": "INDIGO",
        "adani": "ADANIENT",
        "tcs": "TCS",
        "sbi": "SBIN",
        "ongc": "ONGC",
        "l&t": "LT",
    }
    low = question.lower()
    for name, tk in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
        if name in low:
            return name.title(), tk
    return None, None


_EXPLICIT_COMPANY_ALIASES = (
    "reliance", "hdfc bank", "infosys", "tcs", "wipro", "icici bank", "sbi",
    "state bank of india", "axis bank", "kotak", "tata steel", "tata motors",
    "tata power", "larsen & toubro", "larsen and toubro", "adani", "hmt limited",
    "goodricke", "utique", "aakaar", "spright agro", "titan company", "dmart",
    "avenue supermarts", "asian paints", "reliance retail", "ongc", "jsw steel",
    "indigo", "interglobe", "berger", "berger paints",
)


_CORPORATE_FORM_RE = re.compile(
    r"\b(limited|ltd\.?|pvt\.?|private limited|corporation|corp\.?|inc\.?|plc)\b",
    re.I,
)
# Tokens too generic to prove a CapIQ name was intentional in a pedagogy Q.
_GENERIC_NAME_TOKENS = frozenset(
    {
        "capital", "finance", "financial", "india", "indian", "limited", "group",
        "industries", "enterprise", "enterprises", "company", "global", "national",
        "international", "investment", "investments", "services", "power", "energy",
        "steel", "motors", "bank", "banking", "tech", "technology", "technologies",
        "holdings", "corporation", "private", "public", "agro", "labs", "lab",
        "allocation", "value", "equity", "growth", "income", "credit", "money",
        "market", "markets", "securities", "asset", "assets", "fund", "funds",
    }
)


def _has_explicit_company_signal(question: str, *, company_hint: Optional[str] = None, ticker_hint: Optional[str] = None) -> bool:
    """True only when the question clearly names a firm — not a fuzzy CapIQ hit.

    Pedagogy questions like "Customer pays ₹20 lakh in advance" must NOT keep
    a CapIQ bind to "Advance Agrolife Limited" just because one token overlaps.
    """
    low = (question or "").lower()
    if any(a in low for a in _EXPLICIT_COMPANY_ALIASES):
        return True
    # Corporate-form questions ("Explain Margo Finance Limited").
    if _CORPORATE_FORM_RE.search(low):
        return True
    # Only treat ticker_hint as explicit when it appears as a ticker token
    # (not as an English word — ADVANCE must not bind on "in advance").
    if ticker_hint:
        tk = str(ticker_hint).strip()
        if re.search(rf"(?<![a-z0-9]){re.escape(tk)}(?![a-z0-9])", question or "", re.I):
            # Reject pure common-English tickers unless corporate form present.
            if tk.lower() not in _GENERIC_NAME_TOKENS or _CORPORATE_FORM_RE.search(low):
                if tk.isupper() or _CORPORATE_FORM_RE.search(low) or any(
                    a in low for a in _EXPLICIT_COMPANY_ALIASES
                ):
                    # Bare uppercase ticker in the original question.
                    if re.search(rf"\b{re.escape(tk)}\b", question or ""):
                        return True
    if company_hint:
        name_low = str(company_hint).lower().strip()
        # Full/near-full company name present (strong signal).
        if len(name_low) >= 8 and name_low in low:
            return True
        # Or ≥2 distinctive name tokens (avoids "advance" → Advance Agrolife).
        tokens = [t for t in re.split(r"[^a-z0-9]+", name_low) if len(t) >= 4]
        distinctive = [t for t in tokens if t not in _GENERIC_NAME_TOKENS]
        matches = [t for t in distinctive if t in low]
        if len(matches) >= 2:
            return True
    finance_acronyms = {
        "EBITDA", "EBIT", "ROIC", "ROE", "ROA", "FCF", "WACC", "CAPEX", "EV",
        "GDP", "NPA", "NIM", "CASA", "PE", "EPS", "CAGR", "LTM", "YOY",
    }
    for tok in re.findall(r"\b([A-Z]{2,12}\d{0,4})\b", question or ""):
        if tok not in finance_acronyms:
            return True
    return False


def plan_query(question: str) -> QueryPlan:
    q = (question or "").strip()
    types: list[str] = []

    if _ACCOUNTING_RE.search(q):
        types.append("accounting")
    if _FSA_RE.search(q) or _FSA_SHAPE_RE.search(q):
        types.append("financial_statement")
    if _VALUATION_RE.search(q) or _FINANCE_TERMS.search(q):
        types.append("valuation" if _VALUATION_RE.search(q) else "concept")
    if _BUSINESS_RE.search(q):
        types.append("business_model")
    if _MOAT_RE.search(q):
        types.append("moat")
        if "business_model" not in types:
            types.append("business_model")
    if _UNIT_ECON_RE.search(q):
        types.append("unit_economics")
        if "business_model" not in types:
            types.append("business_model")
    if _COMPARISON_RE.search(q) and (
        _BUSINESS_RE.search(q)
        or _MOAT_RE.search(q)
        or _UNIT_ECON_RE.search(q)
        or _INDUSTRY_RE.search(q)
        or _INDUSTRY_NAME_RE.search(q)
        or _GROWTH_RE.search(q)
        or _MANAGEMENT_RE.search(q)
        or _VALUATION_RE.search(q)
        or _FORECAST_RE.search(q)
        or _HISTORICAL_VAL_RE.search(q)
        or re.search(
            r"\b(infosys|tcs|visa|mastercard|dmart|reliance|hdfc|icici|"
            r"ferrari|toyota|apple|costco|asian paints|indigo|air india|"
            r"adani|jsw|tata motors|larsen)\b",
            q,
            re.I,
        )
    ):
        types.append("comparison")
        if _INDUSTRY_NAME_RE.search(q) and not re.search(
            r"\b(infosys|tcs|visa|mastercard|dmart|reliance|hdfc|icici|"
            r"ferrari|toyota|apple|costco)\b",
            q,
            re.I,
        ):
            types.append("industry")
        elif _VALUATION_RE.search(q) or _FORECAST_RE.search(q) or _HISTORICAL_VAL_RE.search(q):
            if "valuation" not in types:
                types.append("valuation")
        elif "business_model" not in types:
            types.append("business_model")
    if _GROWTH_RE.search(q) or _VALUE_DRIVER_RE.search(q):
        if "business_model" not in types:
            types.append("business_model")
    if _MANAGEMENT_RE.search(q):
        if "business_model" not in types:
            types.append("business_model")
    if _INVESTMENT_RE.search(q):
        types.append("investment")
    if _BUSINESS_RISK_RE.search(q):
        types.append("business_risk")
        if "industry" not in types and "investment" not in types:
            types.append("industry")
    if _INDUSTRY_RE.search(q) or _INDUSTRY_NAME_RE.search(q):
        types.append("industry")
    if _CONSENSUS_RE.search(q) or _CONSENSUS_SCREEN_RE.search(q):
        types.insert(0, "consensus")
    if _FORECAST_RE.search(q):
        types.append("forecast")
    if _HISTORICAL_VAL_RE.search(q):
        types.append("historical")
    if _ATTRIBUTION_RE.search(q):
        types.append("attribution")
    if _SCREEN_RE.search(q):
        types.append("screen")
    if _COMPANY_INTEL_RE.search(q):
        types.append("research")
        types.append("investment")
    if _MACRO_RE.search(q):
        # "What is equity risk premium?" / "Explain inflation" are concept
        # pedagogy — not live macro-regime questions for MIE.
        if (
            _CONCEPT_RE.search(q)
            and _MACRO_CONCEPT_TERM_RE.search(q)
            and not re.search(
                r"\b(outlook|regime|affect|impact|transmission|cycle|"
                r"for (?:banks?|nbfcs?|india)|current macro)\b",
                q,
                re.I,
            )
        ):
            if "concept" not in types:
                types.append("concept")
        else:
            types.append("macro")
    if _MARKET_RE.search(q):
        types.append("market")
        if re.search(r"today'?s|market summary|market breadth|sector rotation", q, re.I):
            types.append("market_summary")
    if _PORTFOLIO_RE.search(q):
        types.append("portfolio")
    if _RESEARCH_RE.search(q):
        types.append("research")
    if _NEWS_RE.search(q):
        types.append("news")
    # Pedagogy concept detection — skip when already classified as business/investment.
    business_typed = bool(
        set(types).intersection(
            {
                "business_model",
                "moat",
                "unit_economics",
                "comparison",
                "business_risk",
                "industry",
                "investment",
                "research",
                "portfolio",
                "consensus",
                "forecast",
                "historical",
                "attribution",
                "screen",
                "macro",
                "market_summary",
            }
        )
    )
    if (_CONCEPT_RE.search(q) or _FINANCE_TERMS.search(q)) and not business_typed:
        if "concept" not in types:
            types.append("concept")

    company, ticker = _detect_company_hint(q)
    # CapIQ name matching is aggressive ("advance" → Advance Agrolife).
    # Keep a bind only when the question explicitly names a firm/ticker, or
    # is clearly company-shaped (business model / industry / market / news).
    explicit = _has_explicit_company_signal(q, company_hint=company, ticker_hint=ticker)
    company_shaped = bool(
        _BUSINESS_RE.search(q)
        or _MOAT_RE.search(q)
        or _COMPARISON_RE.search(q)
        or _INDUSTRY_RE.search(q)
        or _MARKET_RE.search(q)
        or _NEWS_RE.search(q)
        or _CONSENSUS_RE.search(q)
    )
    # Reject ticker collisions from finance vocabulary (premium pricing → PREMIUM).
    if ticker and str(ticker).upper() in {
        "PREMIUM", "VALUE", "GROWTH", "INCOME", "CREDIT", "ADVANCE", "CAPITAL",
    } and not explicit:
        company, ticker = None, None
    if (company or ticker) and not explicit and not company_shaped:
        company, ticker = None, None
    # Unsupported globals named in the question must not keep an Indian CapIQ bind.
    if ticker and re.search(
        r"\b(apple|costco|ferrari|toyota|visa|mastercard|netflix|tesla)\b", q, re.I
    ) and not explicit:
        # Only drop when the bind is not itself one of those names (never in IKT).
        company, ticker = None, None
    # Industry pedagogy phrases must not CapIQ-bind a random "Real Estate" company.
    # Keep the bind when the question explicitly names a firm (Titan Company sector,
    # Infosys competitors, …) — only strip fuzzy/pedagogy false binds.
    if (
        ticker
        and re.search(
            r"\b(real estate|industry|sector|oligopoly|porter|five forces|"
            r"typically valued|industry economics)\b",
            q,
            re.I,
        )
        and not explicit
        and not re.search(
            r"\b(infosys|tcs|hdfc|reliance|dmart|wipro|icici|sbi|titan|"
            r"axis|kotak|adani|ongc|asian paints)\b",
            q,
            re.I,
        )
    ):
        company, ticker = None, None
        if "company" in types:
            types = [t for t in types if t != "company"]
    if company or ticker:
        types.insert(0, "company")

    # Evaluate/Assess/Analyze + company bind → investment reasoning layer.
    explicit_now = _has_explicit_company_signal(q, company_hint=company, ticker_hint=ticker)
    if (
        "investment" not in types
        and _INVESTMENT_VERB_RE.search(q)
        and (company or ticker or explicit_now)
    ):
        types.append("investment")

    # Dedup preserving order
    seen = set()
    ordered = []
    for t in types:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    if not ordered:
        ordered = ["unknown"]

    requires_company = bool(ticker or company) or (
        "company" in ordered and "concept" not in ordered and "accounting" not in ordered
    )
    requires_det = bool(
        set(ordered).intersection({"concept", "accounting", "financial_statement", "valuation"})
        and not ticker
    )

    concept_hint = None
    if "concept" in ordered or "valuation" in ordered:
        concept_hint = q

    return QueryPlan(
        question=q,
        question_types=ordered,
        company_hint=company,
        ticker_hint=ticker,
        concept_hint=concept_hint,
        requires_company=requires_company,
        requires_deterministic_finance=requires_det,
    )
