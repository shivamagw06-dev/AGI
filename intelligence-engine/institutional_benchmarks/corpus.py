"""Raw evidence corpora for IBS — disclosures/facts only, never answer packs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional, Sequence


def evidence(
    evidence_id: str,
    *,
    source: str,
    date: str,
    evidence_type: str,
    ticker: str,
    text: str,
    confidence_contribution: float = 0.55,
    peer_ticker: Optional[str] = None,
    metrics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "evidence_id": evidence_id,
        "source": source,
        "date": date,
        "evidence_type": evidence_type,
        "ticker": ticker.upper(),
        "text": text.strip(),
        "confidence_contribution": float(confidence_contribution),
        "schema": "ibs01.raw_evidence.v1",
    }
    if peer_ticker:
        row["peer_ticker"] = peer_ticker.upper()
    if metrics:
        row["metrics"] = dict(metrics)
    return row


def build_corpus(
    *,
    case_id: str,
    ticker: str,
    sector: str,
    title: str,
    time_window: str,
    peers: Sequence[str],
    documents: Sequence[dict[str, Any]],
    event: Optional[dict[str, Any]] = None,
    expected_coverage: Optional[Sequence[str]] = None,
    related_questions: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    docs = [deepcopy(d) for d in documents]
    return {
        "schema": "ibs01.raw_corpus.v1",
        "case_id": case_id,
        "ticker": ticker.upper(),
        "sector": sector.upper(),
        "title": title,
        "time_window": time_window,
        "peers": [p.upper() for p in peers],
        "event": dict(event or {}),
        "documents": docs,
        "document_count": len(docs),
        "expected_evidence_coverage": list(expected_coverage or []),
        "related_questions": list(related_questions or []),
        "fixture_answers": False,
        "prewritten_research": False,
        "note": "Raw disclosures only — AGI must assemble institutional research.",
    }


def filter_corpus_by_cutoff(corpus: dict[str, Any], cutoff: str) -> dict[str, Any]:
    """Historical blind mode — hide documents published after cutoff (YYYY-MM-DD)."""
    cut = str(cutoff or "").strip()[:10]
    if not cut:
        return deepcopy(corpus)
    kept = [d for d in (corpus.get("documents") or []) if str(d.get("date") or "")[:10] <= cut]
    out = deepcopy(corpus)
    out["documents"] = kept
    out["document_count"] = len(kept)
    out["historical_cutoff"] = cut
    out["hidden_after_cutoff"] = int((corpus.get("document_count") or 0) - len(kept))
    return out


# --- Sector case corpora (raw evidence excerpts) ---


def corpus_kotak_rbi() -> dict[str, Any]:
    """Reuse IST-02 Kotak raw corpus shape under IBS case id."""
    try:
        from institutional_stress_tests.raw_corpus import kotak_rbi_april_2024_raw_corpus

        base = kotak_rbi_april_2024_raw_corpus()
        return build_corpus(
            case_id="KOTAK_RBI",
            ticker="KOTAKBANK",
            sector="BANKING",
            title="Kotak Mahindra Bank — RBI Restrictions (April 2024)",
            time_window="2024-04 to 2024-07",
            peers=base.get("peers") or ["HDFCBANK", "ICICIBANK", "AXISBANK"],
            documents=base.get("documents") or [],
            event=base.get("event"),
            expected_coverage=[
                "regulatory_filing",
                "exchange_announcement",
                "earnings_call",
                "financial_statement",
                "peer_financial",
            ],
            related_questions=[
                "Explain Kotak after the RBI restrictions.",
                "Why not prefer HDFC Bank instead?",
                "Would you own ICICI Bank instead over the same window?",
            ],
        )
    except Exception:
        t = "KOTAKBANK"
        return build_corpus(
            case_id="KOTAK_RBI",
            ticker=t,
            sector="BANKING",
            title="Kotak Mahindra Bank — RBI Restrictions (April 2024)",
            time_window="2024-04 to 2024-07",
            peers=["HDFCBANK", "ICICIBANK", "AXISBANK"],
            documents=[
                evidence(
                    "raw:kotak:rbi:2024-04-24",
                    source="RBI announcement",
                    date="2024-04-24",
                    evidence_type="regulatory_filing",
                    ticker=t,
                    text="RBI restricted Kotak digital onboarding and new credit cards pending IT remediation.",
                    confidence_contribution=0.9,
                )
            ],
            event={"name": "RBI restrictions", "anchor_period": "2024-04"},
        )


def _standard_pack(
    case_id: str,
    ticker: str,
    sector: str,
    title: str,
    time_window: str,
    peers: Sequence[str],
    *,
    event_text: str,
    event_date: str,
    call_text: str,
    fs_text: str,
    peer_text: str,
    event_type: str = "exchange_announcement",
    related: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    t = ticker.upper()
    p0 = peers[0].upper() if peers else t
    docs = [
        evidence(
            f"raw:{t.lower()}:event:{event_date}",
            source="Exchange / IR announcement",
            date=event_date,
            evidence_type=event_type,
            ticker=t,
            text=event_text,
            confidence_contribution=0.85,
        ),
        evidence(
            f"raw:{t.lower()}:call:{event_date}",
            source=f"{t} conference call transcript",
            date=event_date,
            evidence_type="earnings_call",
            ticker=t,
            text=call_text,
            confidence_contribution=0.7,
        ),
        evidence(
            f"raw:{t.lower()}:fs:{event_date}",
            source=f"{t} financial results",
            date=event_date,
            evidence_type="financial_statement",
            ticker=t,
            text=fs_text,
            confidence_contribution=0.75,
            metrics={"period": event_date[:7]},
        ),
        evidence(
            f"raw:{t.lower()}:qtr:{event_date}",
            source=f"{t} quarterly report excerpt",
            date=event_date,
            evidence_type="quarterly_report",
            ticker=t,
            text=fs_text,
            confidence_contribution=0.7,
        ),
        evidence(
            f"raw:{t.lower()}:ar:{event_date}",
            source=f"{t} annual report excerpt",
            date=event_date,
            evidence_type="annual_report",
            ticker=t,
            text=f"Board/risk commentary for {t} in the case window.",
            confidence_contribution=0.6,
        ),
        evidence(
            f"raw:{t.lower()}:ppt:{event_date}",
            source=f"{t} investor presentation",
            date=event_date,
            evidence_type="investor_presentation",
            ticker=t,
            text=f"Management presentation slides for {title}.",
            confidence_contribution=0.55,
        ),
        evidence(
            f"raw:{t.lower()}:px:{event_date}",
            source="Exchange price series",
            date=event_date,
            evidence_type="historical_price",
            ticker=t,
            text=f"{t} equity price reaction around the case event window.",
            confidence_contribution=0.4,
            metrics={"event_window": time_window},
        ),
        evidence(
            f"raw:peer:{p0.lower()}:{event_date}",
            source=f"{p0} peer financials",
            date=event_date,
            evidence_type="peer_financial",
            ticker=t,
            peer_ticker=p0,
            text=peer_text,
            confidence_contribution=0.55,
        ),
    ]
    # Extra peers
    for p in list(peers)[1:3]:
        docs.append(
            evidence(
                f"raw:peer:{p.lower()}:{event_date}",
                source=f"{p} peer financials",
                date=event_date,
                evidence_type="peer_financial",
                ticker=t,
                peer_ticker=p,
                text=f"{p} peer disclosure in the same window for relative context.",
                confidence_contribution=0.5,
            )
        )
    return build_corpus(
        case_id=case_id,
        ticker=t,
        sector=sector,
        title=title,
        time_window=time_window,
        peers=peers,
        documents=docs,
        event={"name": title, "anchor_period": event_date[:7]},
        expected_coverage=[
            "exchange_announcement",
            "earnings_call",
            "financial_statement",
            "peer_financial",
            "historical_price",
        ],
        related_questions=related
        or [
            f"Explain {t} over {time_window}.",
            f"How does {t} compare with {p0}?",
            f"What would change the institutional view on {t}?",
        ],
    )


def all_corpora() -> dict[str, dict[str, Any]]:
    """Permanent benchmark corpus registry (raw evidence only)."""
    out: dict[str, dict[str, Any]] = {}
    out["KOTAK_RBI"] = corpus_kotak_rbi()

    banking = [
        (
            "YESBANK_TURNAROUND",
            "YESBANK",
            "Yes Bank Turnaround",
            "2020-03 to 2023-03",
            ["HDFCBANK", "ICICIBANK", "AXISBANK"],
            "2021-06-30",
            "Reconstruction and turnaround updates disclosed after the 2020 stress event.",
            "Management discussed franchise rebuild, liability mix, and asset quality trajectory.",
            "Financial results show evolving NPA and deposit metrics through the turnaround window.",
            "HDFC Bank continued as a large private-bank peer without an equivalent reconstruction event.",
        ),
        (
            "HDFC_MERGER",
            "HDFCBANK",
            "HDFC–HDFC Bank Merger",
            "2022-04 to 2024-03",
            ["ICICIBANK", "KOTAKBANK", "AXISBANK"],
            "2023-07-01",
            "Merger of HDFC Ltd with HDFC Bank completed; share swap and integration disclosures published.",
            "Management outlined integration priorities, float, and mortgage franchise combination.",
            "Combined entity financials and merger accounting disclosures for the integration window.",
            "ICICI Bank peer disclosures provide a non-merger private-bank baseline.",
        ),
        (
            "ICICI_RECOVERY",
            "ICICIBANK",
            "ICICI Bank Recovery",
            "2018-01 to 2021-12",
            ["HDFCBANK", "AXISBANK", "KOTAKBANK"],
            "2020-06-30",
            "Asset-quality recovery and retail mix shift disclosures through the cleanup window.",
            "Management emphasised credit costs, retail growth, and risk calibration.",
            "GNPA/NNPA and earnings trajectory disclosed across recovery periods.",
            "HDFC Bank peer metrics for relative franchise comparison.",
        ),
        (
            "AXIS_DIGITAL",
            "AXISBANK",
            "Axis Bank Digital Strategy",
            "2021-01 to 2024-06",
            ["HDFCBANK", "ICICIBANK", "KOTAKBANK"],
            "2023-03-31",
            "Digital acquisition and burgundy/retail strategy updates disclosed.",
            "Management highlighted digital throughput, liability franchise, and opex leverage.",
            "Digital KPIs and retail growth metrics in quarterly disclosures.",
            "Kotak Bank peer digital commentary for relative comparison.",
        ),
    ]
    for case_id, ticker, title, window, peers, date, ev, call, fs, peer in banking:
        out[case_id] = _standard_pack(
            case_id, ticker, "BANKING", title, window, peers,
            event_text=ev, event_date=date, call_text=call, fs_text=fs, peer_text=peer,
        )

    it_cases = [
        ("TCS", "TCS", "TCS Institutional Franchise", "2022-01 to 2024-06", ["INFY", "WIPRO", "TECHM"], "2024-04-12"),
        ("INFY", "INFY", "Infosys Demand Cycle", "2022-01 to 2024-06", ["TCS", "WIPRO", "TECHM"], "2024-04-18"),
        ("WIPRO", "WIPRO", "Wipro Transformation", "2022-01 to 2024-06", ["TCS", "INFY", "TECHM"], "2024-04-19"),
        ("TECHM", "TECHM", "Tech Mahindra Reset", "2022-01 to 2024-06", ["TCS", "INFY", "WIPRO"], "2024-04-25"),
    ]
    for case_id, ticker, title, window, peers, date in it_cases:
        out[case_id] = _standard_pack(
            case_id, ticker, "IT", title, window, peers,
            event_text=f"{ticker} disclosed demand, deal TCV, and margin commentary for the case window.",
            event_date=date,
            call_text=f"Management discussed vertical demand, pricing, and utilisation for {ticker}.",
            fs_text=f"{ticker} revenue growth, EBIT margin, and attrition metrics disclosed.",
            peer_text=f"{peers[0]} peer IT services metrics for relative demand comparison.",
        )

    pharma = [
        ("SUNPHARMA", "SUNPHARMA", "Sun Pharma Specialty Mix", ["DRREDDY", "CIPLA", "DIVISLAB"]),
        ("DRREDDY", "DRREDDY", "Dr Reddy US/Generics Mix", ["SUNPHARMA", "CIPLA", "DIVISLAB"]),
        ("CIPLA", "CIPLA", "Cipla Complex Generics", ["SUNPHARMA", "DRREDDY", "DIVISLAB"]),
        ("DIVISLAB", "DIVISLAB", "Divi's API Cycle", ["SUNPHARMA", "DRREDDY", "CIPLA"]),
    ]
    for case_id, ticker, title, peers in pharma:
        out[case_id] = _standard_pack(
            case_id, ticker, "PHARMA", title, "2022-01 to 2024-06", peers,
            event_text=f"{ticker} product mix / regulatory / capacity disclosures in the case window.",
            event_date="2024-05-15",
            call_text=f"Management discussed US/India mix, pricing, and capacity for {ticker}.",
            fs_text=f"{ticker} sales, gross margin, and R&D spend disclosed.",
            peer_text=f"{peers[0]} peer pharma metrics for relative positioning.",
        )

    industrials = [
        ("LT", "LT", "L&T Order Book Cycle", ["SIEMENS", "ABB", "CUMMINSIND"]),
        ("SIEMENS", "SIEMENS", "Siemens India Electrification", ["LT", "ABB", "CUMMINSIND"]),
        ("ABB", "ABB", "ABB India Automation", ["LT", "SIEMENS", "CUMMINSIND"]),
        ("CUMMINSIND", "CUMMINSIND", "Cummins India Power Cycle", ["LT", "SIEMENS", "ABB"]),
    ]
    for case_id, ticker, title, peers in industrials:
        out[case_id] = _standard_pack(
            case_id, ticker, "INDUSTRIALS", title, "2022-01 to 2024-06", peers,
            event_text=f"{ticker} order inflow / execution disclosures for the case window.",
            event_date="2024-05-10",
            call_text=f"Management discussed orders, margins, and working capital for {ticker}.",
            fs_text=f"{ticker} revenue, EBIT, and order book metrics disclosed.",
            peer_text=f"{peers[0]} peer industrial metrics for relative comparison.",
        )

    energy = [
        ("RELIANCE", "RELIANCE", "Reliance O2C–Digital Mix", ["ONGC", "NTPC", "COALINDIA"]),
        ("ONGC", "ONGC", "ONGC Upstream Cycle", ["RELIANCE", "NTPC", "COALINDIA"]),
        ("COALINDIA", "COALINDIA", "Coal India Volume Cycle", ["NTPC", "ONGC", "RELIANCE"]),
        ("NTPC", "NTPC", "NTPC Generation Mix", ["POWERGRID", "ONGC", "COALINDIA"]),
    ]
    for case_id, ticker, title, peers in energy:
        out[case_id] = _standard_pack(
            case_id, ticker, "ENERGY", title, "2022-01 to 2024-06", peers,
            event_text=f"{ticker} segment / commodity / capacity disclosures in the case window.",
            event_date="2024-05-20",
            call_text=f"Management discussed realisations, volumes, and capex for {ticker}.",
            fs_text=f"{ticker} EBITDA, volumes, and segment profits disclosed.",
            peer_text=f"{peers[0]} peer energy metrics for relative comparison.",
        )

    consumer = [
        ("ITC", "ITC", "ITC FMCG Transition", ["NESTLEIND", "TITAN", "ASIANPAINT"]),
        ("NESTLEIND", "NESTLEIND", "Nestle India Premiumisation", ["ITC", "TITAN", "ASIANPAINT"]),
        ("TITAN", "TITAN", "Titan Jewellery Cycle", ["ITC", "NESTLEIND", "ASIANPAINT"]),
        ("ASIANPAINT", "ASIANPAINT", "Asian Paints Demand Cycle", ["ITC", "NESTLEIND", "TITAN"]),
    ]
    for case_id, ticker, title, peers in consumer:
        out[case_id] = _standard_pack(
            case_id, ticker, "CONSUMER", title, "2022-01 to 2024-06", peers,
            event_text=f"{ticker} demand / mix / margin disclosures in the case window.",
            event_date="2024-05-08",
            call_text=f"Management discussed volume, premiumisation, and competitive intensity for {ticker}.",
            fs_text=f"{ticker} revenue growth, gross margin, and A&P spend disclosed.",
            peer_text=f"{peers[0]} peer consumer metrics for relative comparison.",
        )

    events = [
        ("DEMERGER", "RELIANCE", "FINANCIAL_EVENTS", "Demerger Event Pattern", "2023-01 to 2024-06"),
        ("MERGER", "HDFCBANK", "FINANCIAL_EVENTS", "Merger Event Pattern", "2022-04 to 2024-03"),
        ("RIGHTS_ISSUE", "YESBANK", "FINANCIAL_EVENTS", "Rights Issue Event Pattern", "2020-01 to 2021-12"),
        ("BUYBACK", "TCS", "FINANCIAL_EVENTS", "Buyback Event Pattern", "2022-01 to 2024-06"),
        ("CAPITAL_RAISE", "YESBANK", "FINANCIAL_EVENTS", "Capital Raise Event Pattern", "2020-01 to 2021-12"),
        ("LARGE_ACQUISITION", "SUNPHARMA", "FINANCIAL_EVENTS", "Large Acquisition Pattern", "2022-01 to 2024-06"),
        ("RESTRUCTURING", "YESBANK", "FINANCIAL_EVENTS", "Corporate Restructuring Pattern", "2020-01 to 2022-12"),
    ]
    for case_id, ticker, sector, title, window in events:
        out[case_id] = _standard_pack(
            case_id, ticker, sector, title, window, ["HDFCBANK", "ICICIBANK", "TCS"],
            event_text=f"Corporate event disclosures for {title} involving {ticker}.",
            event_date="2023-06-30",
            call_text=f"Management explained strategic rationale and financial impact of {title}.",
            fs_text=f"Financial statement effects and capital structure disclosures for {title}.",
            peer_text="Peer capital-structure / event baseline for comparison.",
            event_type="corporate_action",
        )

    macro = [
        ("COVID_2020", "NIFTY50", "COVID 2020 Shock", "2020-02 to 2020-12", "2020-03-24"),
        ("INFLATION_CYCLE", "NIFTY50", "Inflation Cycle", "2021-01 to 2023-06", "2022-06-30"),
        ("RATE_HIKES", "NIFTYBANK", "Rate Hike Cycle", "2022-04 to 2023-12", "2022-05-04"),
        ("RATE_CUTS", "NIFTYBANK", "Rate Cut Cycle", "2019-01 to 2020-06", "2019-08-07"),
        ("BANKING_STRESS", "NIFTYBANK", "Banking Stress Episode", "2020-03 to 2021-06", "2020-03-20"),
        ("COMMODITY_SHOCK", "NIFTY50", "Commodity Shock", "2021-01 to 2022-12", "2022-03-08"),
        ("ELECTION_CYCLE", "NIFTY50", "Election Cycle", "2023-01 to 2024-06", "2024-04-19"),
    ]
    for case_id, ticker, title, window, date in macro:
        out[case_id] = _standard_pack(
            case_id, ticker, "MACRO", title, window, ["HDFCBANK", "RELIANCE", "TCS"],
            event_text=f"Macro / market event context for {title} around {date}.",
            event_date=date,
            call_text=f"Institutional desk notes on transmission of {title} to earnings and multiples.",
            fs_text=f"Aggregate market / sector financial context during {title}.",
            peer_text="Sector leaders' disclosures used as transmission proxies.",
            event_type="macro",
        )

    return out


def get_corpus(case_id: str, *, cutoff: Optional[str] = None) -> dict[str, Any]:
    key = str(case_id or "").strip().upper()
    # aliases
    aliases = {"IST-02": "KOTAK_RBI", "IST02": "KOTAK_RBI", "KOTAK": "KOTAK_RBI"}
    key = aliases.get(key, key)
    corpora = all_corpora()
    if key not in corpora:
        raise KeyError(f"unknown benchmark case: {case_id}")
    corpus = deepcopy(corpora[key])
    if cutoff:
        corpus = filter_corpus_by_cutoff(corpus, cutoff)
    return corpus
