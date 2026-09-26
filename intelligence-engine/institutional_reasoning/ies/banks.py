"""IES question banks — 100 cases per suite (700 total).

Generated from institutional templates × entity universes with gold labels.
Not random questions.
"""

from __future__ import annotations

from institutional_reasoning.ies.schema import Case, GoldExpectation

# ---------------------------------------------------------------------------
# Universes
# ---------------------------------------------------------------------------

IT_NAMES = [
    ("Infosys", "INFY", "Company"),
    ("TCS", "TCS", "Company"),
    ("Wipro", "WIPRO", "Company"),
    ("HCL Tech", "HCLTECH", "Company"),
    ("Tech Mahindra", "TECHM", "Company"),
]

FMCG_NAMES = [
    ("Nestle India", "NESTLEIND", "Company"),
    ("Hindustan Unilever", "HINDUNILVR", "Company"),
    ("Britannia", "BRITANNIA", "Company"),
    ("Dabur", "DABUR", "Company"),
    ("ITC", "ITC", "Company"),
]

BANK_NAMES = [
    ("HDFC Bank", "HDFCBANK", "Company"),
    ("ICICI Bank", "ICICIBANK", "Company"),
    ("Axis Bank", "AXISBANK", "Company"),
    ("Kotak Bank", "KOTAKBANK", "Company"),
    ("SBI", "SBIN", "Company"),
]

INDEX_NAMES = [
    ("Nifty IT", "NIFTYIT", "Index"),
    ("Nifty Bank", "NIFTYBANK", "Index"),
    ("Nifty 50", "NIFTY50", "Index"),
]

# Supported valuation subjects (have PE / peer evidence after seed expansion)
VAL_SUPPORTED = IT_NAMES + FMCG_NAMES[:2] + [("Nifty IT", "NIFTYIT", "Index")] + BANK_NAMES[:2]

VAL_WORDS = (
    "expensive",
    "cheap",
    "overvalued",
    "undervalued",
    "fairly valued",
    "rich",
    "attractively valued",
)

BQ_PROMPTS = (
    "Is {name} a quality business?",
    "Does {name} have a moat?",
    "Evaluate {name}'s capital allocation.",
    "Assess {name} business quality using ROIC.",
    "Analyse {name} margins and reinvestment.",
    "Is {name} a high-ROIC franchise?",
    "Review competitive position of {name}.",
    "Evaluate pricing power at {name}.",
    "How durable is {name}'s moat?",
    "Assess reinvestment runway at {name}.",
)

ACCT_PROMPTS = (
    "Analyse receivable growth for {name}.",
    "Evaluate cash flow quality for {name}.",
    "Working capital trends at {name}.",
    "Earnings quality assessment for {name}.",
    "Inventory build-up risk at {name}.",
    "Accruals analysis for {name}.",
    "Leverage and balance sheet quality for {name}.",
    "Asset turnover trends for {name}.",
    "Piotroski screen for {name}.",
    "Cash conversion quality versus reported earnings for {name}.",
)

EDU_PROMPTS = (
    "What is ROIC?",
    "Explain WACC.",
    "Explain EV.",
    "What is DCF?",
    "Define free cash flow.",
    "What is EV/EBITDA?",
    "Explain margin of safety.",
    "What is a peer multiple?",
    "Define terminal growth rate.",
    "Explain historical PE percentile.",
    "What is PEG ratio?",
    "Define invested capital.",
    "What is cash conversion cycle?",
    "Explain residual income valuation.",
    "What is cost of equity?",
    "Define enterprise value.",
    "What is book value?",
    "Explain Damodaran relative valuation.",
    "What is Piotroski F-score?",
    "Define Altman Z-score.",
)


def _pad(cases: list[Case], suite: str, target: int = 100) -> list[Case]:
    """Deterministically pad to exactly `target` cases by rotating variants."""
    if len(cases) >= target:
        return cases[:target]
    out = list(cases)
    i = 0
    while len(out) < target:
        base = cases[i % len(cases)]
        n = len(out) + 1
        out.append(
            Case(
                case_id=f"ies_{suite}_{n:03d}",
                suite=suite,
                question=base.question,
                gold=base.gold,
                tags=tuple(sorted(set(base.tags) | {"padded"})),
                packs=base.packs,
                build_institutional_evidence=base.build_institutional_evidence,
                ticker_hint=base.ticker_hint,
            )
        )
        i += 1
    # renumber
    renumbered = []
    for idx, c in enumerate(out[:target], start=1):
        renumbered.append(
            Case(
                case_id=f"ies_{suite}_{idx:03d}",
                suite=c.suite,
                question=c.question,
                gold=c.gold,
                tags=c.tags,
                packs=c.packs,
                build_institutional_evidence=c.build_institutional_evidence,
                ticker_hint=c.ticker_hint,
            )
        )
    return renumbered


def valuation_bank() -> list[Case]:
    cases: list[Case] = []
    # Core expensive / cheap / history questions
    for name, eid, etype in VAL_SUPPORTED:
        for word in ("expensive", "overvalued", "cheap", "undervalued"):
            q = f"Is {name} {word}?"
            if "history" not in q.lower() and eid == "NIFTYIT":
                q = f"Is {name} {word} versus history?" if word in {"expensive", "overvalued"} else q
            cases.append(
                Case(
                    case_id="",
                    suite="valuation",
                    question=q,
                    gold=GoldExpectation(
                        question_type="valuation",
                        entity_id=eid,
                        entity_type=etype,
                        path="research",
                        require_executed=("rel_val_damodaran", "hist_multiples")
                        if eid != "NIFTYBANK"
                        else (),
                        require_not_applicable=("dcf_applicability",)
                        if etype == "Index"
                        else (),
                        narrative_allowed=True if eid != "NIFTYBANK" else False,
                        unsupported_claims_forbidden=True,
                        require_provenance=True,
                        min_evidence_score=80.0 if eid != "NIFTYBANK" else None,
                    ),
                    tags=("valuation", "core", eid),
                )
            )
    # Explicit history questions
    for name, eid, etype in [("Infosys", "INFY", "Company"), ("Nifty IT", "NIFTYIT", "Index"), ("TCS", "TCS", "Company")]:
        cases.append(
            Case(
                case_id="",
                suite="valuation",
                question=f"Is {name} expensive versus history?",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id=eid,
                    entity_type=etype,
                    path="research",
                    require_executed=("hist_multiples", "rel_val_damodaran"),
                    narrative_allowed=True,
                    require_provenance=True,
                ),
                tags=("valuation", "history", eid),
            )
        )
    # Relative valuation framing
    for name, eid, _ in IT_NAMES[:3] + BANK_NAMES[:2]:
        cases.append(
            Case(
                case_id="",
                suite="valuation",
                question=f"Value {name} using relative valuation.",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id=eid,
                    path="research",
                    require_executed=("rel_val_damodaran",),
                    unsupported_claims_forbidden=True,
                ),
                tags=("valuation", "relative", eid),
            )
        )
    # DCF applicability
    cases.append(
        Case(
            case_id="",
            suite="valuation",
            question="Is DCF applicable for Zomato?",
            gold=GoldExpectation(
                question_type="valuation",
                entity_id="ZOMATO",
                path="research",
                unsupported_claims_forbidden=True,
            ),
            tags=("valuation", "dcf", "ZOMATO"),
        )
    )
    for name, eid, etype in INDEX_NAMES:
        cases.append(
            Case(
                case_id="",
                suite="valuation",
                question=f"Is DCF applicable for {name}?",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id=eid,
                    entity_type="Index",
                    path="research",
                    require_not_applicable=("dcf_applicability",),
                ),
                tags=("valuation", "dcf", "index", eid),
            )
        )
    for name, eid, _ in BANK_NAMES[:3]:
        cases.append(
            Case(
                case_id="",
                suite="valuation",
                question=f"Is {name} overvalued on PE?",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id=eid,
                    path="research",
                    require_executed=("rel_val_damodaran", "hist_multiples"),
                    narrative_allowed=True,
                ),
                tags=("valuation", "bank", eid),
            )
        )
    # Multiples comparison phrasing
    cases.append(
        Case(
            case_id="",
            suite="valuation",
            question="Compare EV/EBITDA vs PE for Infosys.",
            gold=GoldExpectation(
                question_type="valuation",
                entity_id="INFY",
                path="research",
                unsupported_claims_forbidden=True,
            ),
            tags=("valuation", "multiples", "INFY"),
        )
    )
    return _pad(cases, "valuation")


def business_quality_bank() -> list[Case]:
    cases: list[Case] = []
    subjects = IT_NAMES + FMCG_NAMES[:3] + BANK_NAMES[:2]
    for name, eid, etype in subjects:
        for tmpl in BQ_PROMPTS:
            cases.append(
                Case(
                    case_id="",
                    suite="business_quality",
                    question=tmpl.format(name=name),
                    gold=GoldExpectation(
                        question_type="business_quality",
                        entity_id=eid,
                        entity_type=etype,
                        path="research",
                        require_executed=("business_quality_roic",)
                        if eid in {x[1] for x in IT_NAMES + FMCG_NAMES[:2]}
                        else (),
                        unsupported_claims_forbidden=True,
                        notes="No unsupported great-company / moat claims",
                    ),
                    tags=("business_quality", eid),
                )
            )
    # Comparison of quality
    cases.append(
        Case(
            case_id="",
            suite="business_quality",
            question="Compare Infosys and TCS quality.",
            gold=GoldExpectation(
                question_type="comparison",
                entity_id="INFY",
                path="research",
                unsupported_claims_forbidden=True,
            ),
            tags=("business_quality", "comparison"),
        )
    )
    return _pad(cases, "business_quality")


def accounting_bank() -> list[Case]:
    cases: list[Case] = []
    subjects = IT_NAMES + BANK_NAMES[:2] + FMCG_NAMES[:2]
    for name, eid, etype in subjects:
        for tmpl in ACCT_PROMPTS:
            cases.append(
                Case(
                    case_id="",
                    suite="accounting",
                    question=tmpl.format(name=name),
                    gold=GoldExpectation(
                        question_types=("financial_quality", "comparison", "risk", "investment_decision"),
                        entity_id=eid,
                        entity_type=etype,
                        path="research",
                        # Execute accounting framework when evidence present; else transparent insufficient
                        unsupported_claims_forbidden=True,
                        must_report_insufficient=False,
                        forbid_guessing=True,
                    ),
                    tags=("accounting", eid),
                )
            )
    return _pad(cases, "accounting")


def comparison_bank() -> list[Case]:
    pairs = [
        ("Infosys", "TCS", "INFY"),
        ("HDFC Bank", "ICICI Bank", "HDFCBANK"),
        ("Wipro", "HCL Tech", "WIPRO"),
        ("Nestle India", "Hindustan Unilever", "NESTLEIND"),
        ("Infosys", "Wipro", "INFY"),
        ("TCS", "Tech Mahindra", "TCS"),
        ("ICICI Bank", "Axis Bank", "ICICIBANK"),
        ("ITC", "Dabur", "ITC"),
        ("Reliance", "ONGC", "RELIANCE"),
        ("Infosys", "HCL Tech", "INFY"),
    ]
    templates = (
        "Compare {a} vs {b}.",
        "How does {a} compare with {b} on valuation?",
        "{a} versus {b} — which is cheaper on PE?",
        "Relative quality: {a} vs {b}.",
        "Peer comparison of {a} and {b}.",
        "Relative multiples: {a} versus {b}.",
        "Benchmark {a} against {b}.",
        "Relative valuation of {a} vs {b}.",
        "Which multiple is higher — {a} or {b}?",
        "Sector peers: {a} compared to {b}.",
    )
    cases: list[Case] = []
    for a, b, eid in pairs:
        for tmpl in templates:
            cases.append(
                Case(
                    case_id="",
                    suite="comparison",
                    question=tmpl.format(a=a, b=b),
                    gold=GoldExpectation(
                        question_types=("comparison", "valuation", "business_quality", "sector"),
                        entity_id=eid,
                        path="research",
                        unsupported_claims_forbidden=True,
                    ),
                    tags=("comparison", eid),
                )
            )
    # Sector vs sector
    cases.append(
        Case(
            case_id="",
            suite="comparison",
            question="Compare IT vs Banking valuations.",
            gold=GoldExpectation(
                question_types=("comparison", "valuation", "sector"),
                paths=("research", "clarification"),
                unsupported_claims_forbidden=True,
            ),
            tags=("comparison", "sector"),
            ticker_hint="NIFTYIT",
        )
    )
    return _pad(cases, "comparison")


def insufficient_bank() -> list[Case]:
    """Most important suite — impossible questions must be transparent."""
    raw = [
        (
            "Provide historical PE for NEWCO2026.",
            "NEWCO2026",
            True,
        ),
        (
            "Compute intrinsic value for DELISTEDX with no cash flows.",
            "DELISTEDX",
            True,
        ),
        (
            "Value GHOSTCO using DCF without revenue or FCF.",
            "GHOSTCO",
            True,
        ),
        (
            "Is UNKNOWNPEERS expensive versus peers?",
            "UNKNOWNPEERS",
            True,
        ),
        (
            "Compute historical PE percentile for ONEDAYIPO with one day of listing.",
            "ONEDAYIPO",
            True,
        ),
        (
            "Run sector comparison for EMPTYSECTOR with missing peers.",
            "EMPTYSECTOR",
            True,
        ),
        (
            "Is Nifty Bank expensive versus history?",
            "NIFTYBANK",
            False,  # known entity but missing PE series
        ),
        (
            "Fair value for NULLDATA with no filings.",
            "NULLDATA",
            True,
        ),
        (
            "Peer median PE for ORPHANCO with empty peer universe.",
            "ORPHANCO",
            True,
        ),
        (
            "Intrinsic value of PRIVATECO without shares outstanding.",
            "PRIVATECO",
            True,
        ),
    ]
    cases: list[Case] = []
    for q, eid, use_hint in raw:
        for variant in range(10):
            question = q if variant == 0 else f"{q} (case {variant})"
            cases.append(
                Case(
                    case_id="",
                    suite="insufficient",
                    question=question,
                    gold=GoldExpectation(
                        question_type=None,  # may clarify or research
                        entity_id=eid if not use_hint else eid,
                        path=None,  # clarification OR research+insufficient
                        must_report_insufficient=True,
                        must_list_missing=True,
                        forbid_guessing=True,
                        narrative_allowed=False,
                        unsupported_claims_forbidden=True,
                    ),
                    tags=("insufficient", eid),
                    ticker_hint=eid if use_hint else None,
                    build_institutional_evidence=True,
                )
            )
    return _pad(cases, "insufficient")


def edge_cases_bank() -> list[Case]:
    cases: list[Case] = []
    # Wrong entity pack injection (Infosys data for Nifty IT question)
    for i in range(15):
        cases.append(
            Case(
                case_id="",
                suite="edge_cases",
                question="Is Nifty IT expensive versus history?",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id="NIFTYIT",
                    path="research",
                    # With build_institutional_evidence=False, wrong-entity packs must not execute
                    narrative_allowed=False,
                    unsupported_claims_forbidden=True,
                ),
                tags=("edge", "wrong_entity"),
                build_institutional_evidence=False,
                packs={
                    "valuation": {
                        "company": {"company_symbol": "IS"},
                        "trailing_pe": 24.1,
                        "historical_pe": 21.0,
                        "historical_percentile": 78,
                        "peer_pe": 22.0,
                    }
                },
            )
        )
    # Index DCF
    for name, eid, _ in INDEX_NAMES:
        for _ in range(5):
            cases.append(
                Case(
                    case_id="",
                    suite="edge_cases",
                    question=f"Is DCF applicable for {name}?",
                    gold=GoldExpectation(
                        question_type="valuation",
                        entity_id=eid,
                        require_not_applicable=("dcf_applicability",),
                        unsupported_claims_forbidden=True,
                    ),
                    tags=("edge", "index_dcf", eid),
                )
            )
    # Placeholder / zero PE
    for i in range(15):
        cases.append(
            Case(
                case_id="",
                suite="edge_cases",
                question="Is Nifty IT expensive?",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id="NIFTYIT",
                    narrative_allowed=False,
                    unsupported_claims_forbidden=True,
                ),
                tags=("edge", "placeholder"),
                build_institutional_evidence=False,
                packs={
                    "data_validation": {
                        "validated": {
                            "trailing_pe": {
                                "field": "trailing_pe",
                                "symbol": "NIFTYIT",
                                "value": 0,
                                "verified_at": "2026-07-27T18:00:00Z",
                            }
                        }
                    }
                },
            )
        )
    # Stale evidence
    for i in range(10):
        cases.append(
            Case(
                case_id="",
                suite="edge_cases",
                question="Is Infosys expensive?",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id="INFY",
                    # stale-only packs without institutional evidence → reject
                    narrative_allowed=False,
                    unsupported_claims_forbidden=True,
                ),
                tags=("edge", "stale"),
                build_institutional_evidence=False,
                packs={
                    "data_validation": {
                        "validated": {
                            "trailing_pe": {
                                "field": "trailing_pe",
                                "symbol": "INFY",
                                "value": 26.0,
                                "verified_at": "2020-01-01T00:00:00Z",
                            },
                            "historical_pe": {
                                "field": "historical_pe",
                                "symbol": "INFY",
                                "value": 22.0,
                                "verified_at": "2020-01-01T00:00:00Z",
                            },
                            "historical_percentile": {
                                "field": "historical_percentile",
                                "symbol": "INFY",
                                "value": 80,
                                "verified_at": "2020-01-01T00:00:00Z",
                            },
                            "peer_pe": {
                                "field": "peer_pe",
                                "symbol": "INFY",
                                "value": 24.0,
                                "verified_at": "2020-01-01T00:00:00Z",
                            },
                        }
                    }
                },
            )
        )
    # Negative PE rejection via institutional path still shouldn't invent
    for i in range(10):
        cases.append(
            Case(
                case_id="",
                suite="edge_cases",
                question="Is Infosys expensive with negative earnings?",
                gold=GoldExpectation(
                    question_type="valuation",
                    entity_id="INFY",
                    unsupported_claims_forbidden=True,
                    forbid_guessing=True,
                ),
                tags=("edge", "negative_earnings"),
                build_institutional_evidence=False,
                packs={
                    "data_validation": {
                        "validated": {
                            "trailing_pe": {
                                "field": "trailing_pe",
                                "symbol": "INFY",
                                "value": -12.0,
                                "verified_at": "2026-07-27T18:00:00Z",
                            }
                        }
                    }
                },
            )
        )
    # Unresolved entity
    for i in range(10):
        cases.append(
            Case(
                case_id="",
                suite="edge_cases",
                question="Is it expensive versus history?",
                gold=GoldExpectation(
                    path="clarification",
                    narrative_allowed=False,
                    unsupported_claims_forbidden=True,
                ),
                tags=("edge", "unresolved"),
                build_institutional_evidence=False,
            )
        )
    return _pad(cases, "edge_cases")


def education_bank() -> list[Case]:
    cases: list[Case] = []
    for prompt in EDU_PROMPTS:
        for i in range(5):
            q = prompt if i == 0 else f"{prompt} Please explain simply."
            cases.append(
                Case(
                    case_id="",
                    suite="education",
                    question=q,
                    gold=GoldExpectation(
                        question_type="education",
                        path="education",
                        education_bypass=True,
                        narrative_allowed=True,
                    ),
                    tags=("education",),
                    build_institutional_evidence=False,
                )
            )
    return _pad(cases, "education")


def all_banks() -> dict[str, list[Case]]:
    return {
        "valuation": valuation_bank(),
        "business_quality": business_quality_bank(),
        "accounting": accounting_bank(),
        "comparison": comparison_bank(),
        "insufficient": insufficient_bank(),
        "edge_cases": edge_cases_bank(),
        "education": education_bank(),
    }


def all_cases() -> list[Case]:
    out: list[Case] = []
    for suite in (
        "valuation",
        "business_quality",
        "accounting",
        "comparison",
        "insufficient",
        "edge_cases",
        "education",
    ):
        out.extend(all_banks()[suite])
    return out
