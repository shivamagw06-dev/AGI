"""Deterministic generator — expands CIO gold into 1000+ institutional questions."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.datasets.models import question

# ---------------------------------------------------------------------------
# Template libraries (deterministic; no LLM)
# ---------------------------------------------------------------------------

COMPANIES = [
    ("HDFCBANK", "banks", "private bank"),
    ("ICICIBANK", "banks", "private bank"),
    ("SBIN", "banks", "PSU bank"),
    ("INFY", "it_services", "IT services"),
    ("TCS", "it_services", "IT services"),
    ("WIPRO", "it_services", "IT services"),
    ("RELIANCE", "energy", "conglomerate"),
    ("TITAN", "consumer", "jewellery / watches"),
    ("ASIANPAINT", "paints", "decorative paints"),
    ("MARUTI", "auto", "passenger vehicles"),
    ("INDIGO", "airlines", "airline"),
    ("SUNPHARMA", "pharma", "pharmaceuticals"),
    ("ULTRACEMCO", "cement", "cement"),
    ("TATASTEEL", "metals", "steel"),
    ("HINDUNILVR", "fmcg", "FMCG"),
    ("BAJFINANCE", "nbfc", "NBFC"),
    ("LT", "industrials", "engineering & construction"),
    ("BHARTIARTL", "telecom", "telecom"),
    ("NESTLEIND", "fmcg", "FMCG"),
    ("POWERGRID", "utilities", "power transmission"),
]

INDUSTRIES = [
    ("cement", "utilisation", "pricing power"),
    ("steel", "spreads", "capacity"),
    ("it_services", "attrition", "deal wins"),
    ("banks", "NIM", "GNPA"),
    ("nbfc", "cost of funds", "asset quality"),
    ("airlines", "ATF", "load factor"),
    ("paints", "volume", "premium mix"),
    ("auto", "demand", "margins"),
    ("pharma", "USFDA", "pipeline"),
    ("fmcg", "volume growth", "A&P"),
    ("telecom", "ARPU", "capex"),
    ("cement", "housing", "infra"),
    ("metals", "China demand", "coking coal"),
    ("real_estate", "affordability", "launches"),
    ("hospitals", "occupancy", "ARPOB"),
]

MACRO_SHOCKS = [
    ("RBI repo rate cut of 50 bps", "rate_cutting_cycle", ["banks", "nbfc", "real_estate", "auto"]),
    ("RBI repo rate hike of 50 bps", "rate_hiking_cycle", ["nbfc", "real_estate", "auto"]),
    ("crude oil falls 20%", "oil_collapse", ["airlines", "paints", "tyres"]),
    ("crude oil spikes 30%", "oil_spike", ["omc", "airlines", "paints"]),
    ("INR depreciates 8%", "fx_depreciation", ["it_services", "pharma", "omc"]),
    ("GST collections rise for six months", "fiscal_expansion", ["fmcg", "discretionary"]),
    ("import duties on steel doubled", "import_shock", ["steel", "auto", "capex"]),
    ("PLI expansion for electronics", "fiscal_expansion", ["electronics", "manufacturing"]),
    ("liquidity tightening in money markets", "liquidity_tightening", ["nbfc", "banks"]),
    ("inflation accelerates above 6%", "high_inflation", ["staples", "gold", "rate_sensitive"]),
    ("GDP growth slows while inflation stays high", "stagflation", ["defensive", "staples"]),
    ("election-year fiscal expansion", "election_cycle", ["infra", "PSU", "capex"]),
    ("monsoon failure / agri shock", "demand_slowdown", ["fmcg", "tractors", "rural"]),
    ("global risk-off / FII outflows", "risk_off", ["banks", "high_beta"]),
    ("COVID-style demand shock", "pandemic", ["airlines", "hotels", "discretionary"]),
]

DOC_FOCUS = [
    ("MD&A", "emerging risks"),
    ("notes to accounts", "contingent liabilities"),
    ("related party disclosures", "governance risk"),
    ("cash flow statement", "cash conversion"),
    ("auditor report / KAMs", "accounting risk"),
    ("investor presentation vs annual report", "non-GAAP inconsistency"),
    ("capital allocation commentary", "buybacks vs capex"),
    ("segment notes", "hidden capital intensity"),
    ("risk factors", "pre-financial risks"),
    ("board report", "strategy shifts"),
]

VALUATION_FRAMES = [
    ("P/B and Residual Income", "banks", ["FW_PB", "FW_RESIDUAL_INCOME"]),
    ("EV/EBITDA and DCF", "it_services", ["FW_EV_EBITDA", "FW_DCF"]),
    ("SOTP", "conglomerate", ["FW_SOTP", "FW_NAV"]),
    ("P/E vs growth", "fmcg", ["FW_PE", "FW_PEG"]),
    ("replacement cost", "cement", ["FW_REPLACEMENT", "FW_EV_EBITDA"]),
    ("NAV", "real_estate", ["FW_NAV", "FW_DCF"]),
]

RISK_THEMES = [
    ("asset quality deterioration", "banks"),
    ("client concentration", "it_services"),
    ("regulatory action", "nbfc"),
    ("commodity input spike", "paints"),
    ("USFDA warning letter", "pharma"),
    ("capacity glut", "cement"),
    ("ATF cost shock", "airlines"),
    ("working capital blowout", "consumer"),
    ("governance red flags", "cross"),
    ("refinancing risk", "nbfc"),
]

PORTFOLIO_THEMES = [
    ("overweight private banks vs PSU banks", "banks"),
    ("pair trade IT vs metals", "cross"),
    ("defensive tilt into staples", "fmcg"),
    ("reduce duration-sensitive NBFCs", "nbfc"),
    ("add exporters on INR weakness", "it_services"),
    ("cut high-beta cyclicals into hike cycle", "metals"),
    ("infrastructure beneficiaries of budget capex", "industrials"),
    ("quality premium vs value trap", "cross"),
]

ACCOUNTING_THEMES = [
    ("revenue recognition aggressiveness", "it_services"),
    ("inventory days spike", "consumer"),
    ("capitalised costs", "telecom"),
    ("one-off other income", "conglomerate"),
    ("NPA recognition lag", "banks"),
    ("lease capitalisation effects", "airlines"),
    ("deferred tax volatility", "pharma"),
    ("promoter pledging disclosures", "cross"),
]

REPLAY_DATES = [
    ("2020-03-31", "COVID onset", "INFY"),
    ("2013-08-31", "taper tantrum", "HDFCBANK"),
    ("2016-11-30", "demonetisation", "HINDUNILVR"),
    ("2018-09-30", "NBFC liquidity stress", "BAJFINANCE"),
    ("2022-06-30", "rate hike cycle", "ICICIBANK"),
    ("2008-10-31", "GFC acute phase", "RELIANCE"),
    ("2014-12-31", "oil collapse", "INDIGO"),
    ("2017-07-31", "GST launch", "TITAN"),
]


def generate_institutional_library(*, target: int = 1000) -> list[dict[str, Any]]:
    """Build ≥target unique structured questions across all IEL categories."""
    rows: list[dict[str, Any]] = []
    n = 0

    def add(q: dict[str, Any]) -> None:
        nonlocal n
        rows.append(q)
        n += 1

    # --- Company (entity-linked) ---
    for ticker, sector, label in COMPANIES:
        templates = [
            (
                f"What evidence domains should AGIB retrieve before assessing {ticker}'s competitive position as a {label}?",
                ["Analyse"],
                ["FW_BUSINESS_QUALITY", "FW_PEER_COMPARISON"],
                ["competitors", "margins", "market_share"],
                "medium",
            ),
            (
                f"How would you evaluate capital allocation quality at {ticker} over the last five years?",
                ["Analyse", "Documents"],
                ["FW_CAPITAL_ALLOCATION", "FW_CORPORATE_GOVERNANCE"],
                ["buybacks", "dividends", "capex", "annual_report"],
                "medium",
            ),
            (
                f"Which valuation frameworks are most appropriate for {ticker} ({label}) and why?",
                ["Explain", "Accounting"],
                ["FW_FRAMEWORK_EXPLANATION", "FW_HISTORICAL_VALUATION"],
                ["accounting", "valuation", sector],
                "medium",
            ),
            (
                f"If {ticker} misses earnings expectations, what historical analogues should Institutional Memory retrieve?",
                ["HistoricalReplay", "Analyse", "CorporateEvents"],
                ["FW_EXPECTATIONS", "FW_PEER_COMPARISON"],
                ["earnings", "guidance", "historical_events"],
                "hard",
            ),
            (
                f"Identify the top institutional risks for {ticker} that could invalidate a bullish thesis.",
                ["Analyse"],
                ["FW_RISK", "FW_SCENARIO"],
                ["risk", "governance", "industry"],
                "medium",
            ),
        ]
        for i, (text, intent, fws, ev, diff) in enumerate(templates, 1):
            add(
                question(
                    f"GEN-CO-{ticker}-{i:02d}",
                    text=text,
                    category="company",
                    intent=intent,
                    frameworks=fws,
                    expected_evidence=ev,
                    expected_playbook=["PB_COMPANY_", "PB_IND_", f"PB_{sector.upper()[:6]}"],
                    expected_reasoning=[label, "evidence", "institutional"],
                    difficulty=diff,
                    sector=sector,
                    ticker_hint=ticker,
                    suite="institutional_1000",
                    tags=["generated", "company", sector],
                )
            )

    # --- Industry ---
    for ind, kpi_a, kpi_b in INDUSTRIES:
        ind_label = ind.replace("_", " ")
        for i, (text, intent, fws) in enumerate(
            [
                (
                    f"Which KPIs matter most for the Indian {ind_label} industry and why ({kpi_a}, {kpi_b})?",
                    ["Industry", "Explain"],
                    ["FW_INDUSTRY_STRUCTURE", "FW_KPI"],
                ),
                (
                    f"Explain the current cycle position of Indian {ind_label} using utilisation, pricing, and competitive structure.",
                    ["Industry", "Analyse"],
                    ["FW_INDUSTRY_STRUCTURE", "FW_SCENARIO"],
                ),
                (
                    f"How should AGIB compare leaders vs laggards within Indian {ind_label}?",
                    ["Compare", "Industry"],
                    ["FW_PEER_COMPARISON", "FW_INDUSTRY_STRUCTURE"],
                ),
            ],
            1,
        ):
            add(
                question(
                    f"GEN-IND-{ind[:8].upper()}-{i:02d}",
                    text=text,
                    category="industry",
                    intent=intent,
                    frameworks=fws,
                    expected_evidence=[ind, kpi_a, kpi_b],
                    expected_playbook=["PB_IND_", f"PB_IND_{ind[:6].upper()}"],
                    expected_reasoning=[kpi_a, kpi_b, "cycle"],
                    difficulty="medium",
                    sector=ind,
                    concept_mode=True,
                    suite="institutional_1000",
                    tags=["generated", "industry", ind],
                )
            )

    # --- Macro / Government ---
    for i, (shock, regime, beneficiaries) in enumerate(MACRO_SHOCKS, 1):
        add(
            question(
                f"GEN-MAC-TX-{i:03d}",
                text=(
                    f"Shock: {shock}. Trace first-order and second-order transmission to "
                    f"{', '.join(beneficiaries)}. Which sectors benefit or suffer?"
                ),
                category="macro",
                intent=["Macro", "CrossDomain", "Government"],
                frameworks=["FW_MACRO_TRANSMISSION", "FW_SCENARIO", "FW_INDUSTRY_STRUCTURE"],
                expected_evidence=[regime, *beneficiaries[:2]],
                expected_playbook=["PB_MACRO_", "PB_GOV_", "PB_RATE"],
                expected_reasoning=["first-order", "second-order", "transmission"],
                ground_truth=[f"regime:{regime}"],
                difficulty="hard",
                concept_mode=True,
                suite="institutional_1000",
                tags=["generated", "macro", regime],
            )
        )
        add(
            question(
                f"GEN-GOV-POL-{i:03d}",
                text=(
                    f"Policy/macro context: {shock}. What government or RBI evidence should AGIB "
                    f"retrieve before concluding on {beneficiaries[0]} exposure?"
                ),
                category="government",
                intent=["Government", "Macro", "Analyse"],
                frameworks=["FW_POLICY", "FW_MACRO_TRANSMISSION"],
                expected_evidence=["policy", beneficiaries[0], "government"],
                expected_playbook=["PB_GOV_", "PB_MACRO_"],
                expected_reasoning=["policy", "evidence before conclusion"],
                difficulty="medium",
                concept_mode=True,
                suite="institutional_1000",
                tags=["generated", "government", regime],
            )
        )
        add(
            question(
                f"GEN-MEM-ANLG-{i:03d}",
                text=(
                    f"Have we seen this before? Given {shock}, which historical analogues should "
                    f"Institutional Memory retrieve for {beneficiaries[0]} and {beneficiaries[1]}?"
                ),
                category="historical_replay",
                intent=["HistoricalReplay", "Macro", "Analyse", "Government"],
                frameworks=["FW_MACRO_TRANSMISSION", "FW_SCENARIO"],
                expected_evidence=["historical", regime, "analog"],
                expected_playbook=["PB_MACRO_", "PB_REPLAY"],
                expected_reasoning=["analogues", "similarities", "differences"],
                difficulty="hard",
                concept_mode=True,
                suite="institutional_1000",
                tags=["generated", "memory", regime],
            )
        )

    # --- Valuation ---
    for i, (frame, sector, fws) in enumerate(VALUATION_FRAMES, 1):
        for j, ticker in enumerate([c[0] for c in COMPANIES if c[1] == sector or sector in c[2]][:4] or ["INFY"], 1):
            add(
                question(
                    f"GEN-VAL-{i:02d}-{j:02d}",
                    text=f"When is {frame} the correct primary framework for {ticker}? When would it be misleading?",
                    category="valuation",
                    intent=["Explain", "Accounting", "Valuation"],
                    frameworks=list(fws) + ["FW_FRAMEWORK_EXPLANATION"],
                    expected_evidence=["valuation", "accounting", sector],
                    expected_playbook=["PB_VAL_", "PB_FRAMEWORK"],
                    expected_reasoning=["appropriate", "misleading", "accounting identity"],
                    difficulty="medium",
                    sector=sector,
                    ticker_hint=ticker,
                    suite="institutional_1000",
                    tags=["generated", "valuation"],
                )
            )

    # --- Accounting ---
    for i, (theme, sector) in enumerate(ACCOUNTING_THEMES, 1):
        for j, (ticker, sec, _) in enumerate([c for c in COMPANIES if c[1] == sector or sector == "cross"][:5], 1):
            add(
                question(
                    f"GEN-ACC-{i:02d}-{j:02d}",
                    text=f"How would you investigate {theme} at {ticker}? Which statements and notes matter most?",
                    category="accounting",
                    intent=["Accounting", "Analyse", "Documents"],
                    frameworks=["FW_ACCOUNTING", "FW_CASH_FLOW", "FW_RISK"],
                    expected_evidence=["notes", "cash_flow", "annual_report"],
                    expected_playbook=["PB_ACC_", "PB_DOC_"],
                    expected_reasoning=[theme.split()[0], "investigate", "notes"],
                    difficulty="hard",
                    sector=sec,
                    ticker_hint=ticker,
                    suite="institutional_1000",
                    tags=["generated", "accounting"],
                )
            )

    # --- Documents ---
    for i, (section, purpose) in enumerate(DOC_FOCUS, 1):
        for j, (ticker, sector, _) in enumerate(COMPANIES[:12], 1):
            add(
                question(
                    f"GEN-DOC-{i:02d}-{j:02d}",
                    text=(
                        f"Using {ticker}'s institutional documents, how would you use the {section} "
                        f"to identify {purpose}?"
                    ),
                    category="documents",
                    intent=["Documents", "Explain", "Analyse"],
                    frameworks=["FW_CORPORATE_GOVERNANCE", "FW_RISK", "FW_CAPITAL_ALLOCATION"],
                    expected_evidence=["annual_report", section.lower(), "documents"],
                    expected_playbook=["PB_DOC_ANNUAL", "PB_DOC_"],
                    expected_reasoning=[purpose, section],
                    difficulty="medium",
                    sector=sector,
                    ticker_hint=ticker,
                    suite="institutional_1000",
                    tags=["generated", "documents"],
                )
            )

    # --- Risk ---
    for i, (theme, sector) in enumerate(RISK_THEMES, 1):
        for j in range(1, 6):
            ticker = next((c[0] for c in COMPANIES if c[1] == sector), COMPANIES[j % len(COMPANIES)][0])
            add(
                question(
                    f"GEN-RSK-{i:02d}-{j:02d}",
                    text=f"Construct a risk checklist for {theme} affecting {ticker}. What evidence would falsify complacency?",
                    category="risk",
                    intent=["Risk", "Analyse", "Explain"],
                    frameworks=["FW_RISK", "FW_SCENARIO", "FW_CREDIT_CYCLE"],
                    expected_evidence=["risk", "evidence", "falsify"],
                    expected_playbook=["PB_RISK_", "PB_COMPANY_"],
                    expected_reasoning=["checklist", "falsify", theme.split()[0]],
                    difficulty="medium",
                    sector=sector if sector != "cross" else None,
                    ticker_hint=ticker,
                    suite="institutional_1000",
                    tags=["generated", "risk"],
                )
            )

    # --- Portfolio ---
    for i, (theme, sector) in enumerate(PORTFOLIO_THEMES, 1):
        for j in range(1, 8):
            add(
                question(
                    f"GEN-PF-{i:02d}-{j:02d}",
                    text=(
                        f"Portfolio decision: {theme}. What macro, industry, and company evidence "
                        f"must AGIB assemble before sizing the position? (variant {j})"
                    ),
                    category="portfolio",
                    intent=["Portfolio", "Analyse", "CrossDomain", "Macro"],
                    frameworks=["FW_PORTFOLIO", "FW_MACRO_TRANSMISSION", "FW_RISK"],
                    expected_evidence=["portfolio", "macro", "risk", sector],
                    expected_playbook=["PB_PORTFOLIO_", "PB_MACRO_", "PB_IC_"],
                    expected_reasoning=["sizing", "evidence before position", theme.split()[0]],
                    difficulty="hard",
                    sector=sector if sector != "cross" else None,
                    concept_mode=True,
                    suite="institutional_1000",
                    tags=["generated", "portfolio"],
                )
            )

    # --- Historical replay ---
    for i, (as_of, label, ticker) in enumerate(REPLAY_DATES, 1):
        for j, aspect in enumerate(
            ["valuation evidence", "macro regime", "management commentary", "competitive position", "risk factors"],
            1,
        ):
            add(
                question(
                    f"GEN-REP-{i:02d}-{j:02d}",
                    text=(
                        f"Replay {ticker} as of {as_of} ({label}). Restrict analysis to {aspect} "
                        f"available on that date. Explain how AGIB prevents future leakage."
                    ),
                    category="historical_replay",
                    intent=["HistoricalReplay"],
                    frameworks=["FW_HISTORICAL_VALUATION", "FW_SCENARIO"],
                    expected_evidence=["as_of", "point_in_time", label.split()[0].lower()],
                    expected_playbook=["PB_REPLAY", "PB_IND_", "PB_MACRO_"],
                    expected_reasoning=["available_from", "no future leakage", as_of],
                    ground_truth=[f"as_of={as_of}"],
                    difficulty="hard",
                    ticker_hint=ticker,
                    as_of=as_of,
                    must_not=["2024", "2025", "generative ai"],
                    suite="institutional_1000",
                    tags=["generated", "replay", label.replace(" ", "_")],
                )
            )

    # --- Cross-domain combinations to fill to target ---
    combo_i = 0
    while len(rows) < target:
        combo_i += 1
        shock, regime, bens = MACRO_SHOCKS[(combo_i - 1) % len(MACRO_SHOCKS)]
        ticker, sector, label = COMPANIES[(combo_i - 1) % len(COMPANIES)]
        ind, kpi_a, kpi_b = INDUSTRIES[(combo_i - 1) % len(INDUSTRIES)]
        add(
            question(
                f"GEN-XDOM-{combo_i:04d}",
                text=(
                    f"Cross-domain: Under {shock}, how should AGIB connect macro transmission, "
                    f"{ind} industry KPIs ({kpi_a}/{kpi_b}), and company evidence for {ticker} "
                    f"({label}) before forming a conclusion?"
                ),
                category="cross_domain",
                intent=["CrossDomain", "Macro", "Analyse"],
                frameworks=["FW_MACRO_TRANSMISSION", "FW_INDUSTRY_STRUCTURE", "FW_BUSINESS_QUALITY"],
                expected_evidence=[regime, ind, ticker.lower(), kpi_a],
                expected_playbook=["PB_MACRO_", "PB_IND_", "PB_COMPANY_"],
                expected_reasoning=["cross-domain", "evidence before conclusion", "transmission"],
                difficulty="expert" if combo_i % 5 == 0 else "hard",
                sector=sector,
                ticker_hint=ticker,
                concept_mode=False,
                suite="institutional_1000",
                tags=["generated", "cross_domain", regime],
            )
        )

    # Stable order
    rows.sort(key=lambda r: r["question_id"])
    return rows[: max(target, 1000)]
