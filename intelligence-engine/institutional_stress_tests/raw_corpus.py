"""Raw evidence corpora for IST-02 — documents/facts only, never institutional answers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional


def _ev(
    evidence_id: str,
    *,
    source: str,
    date: str,
    evidence_type: str,
    ticker: str,
    text: str,
    confidence_contribution: float = 0.5,
    metrics: Optional[dict[str, Any]] = None,
    peer_ticker: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "evidence_id": evidence_id,
        "source": source,
        "date": date,
        "evidence_type": evidence_type,
        "ticker": ticker.upper(),
        "text": text.strip(),
        "confidence_contribution": float(confidence_contribution),
        "schema": "ist02.raw_evidence.v1",
    }
    if metrics:
        row["metrics"] = dict(metrics)
    if peer_ticker:
        row["peer_ticker"] = peer_ticker.upper()
    if extras:
        row["extras"] = dict(extras)
    return row


def kotak_rbi_april_2024_raw_corpus() -> dict[str, Any]:
    """
    Raw evidence pack for Kotak / RBI April 2024 case.

    Contains ONLY source-like disclosures, statement excerpts, call snippets,
    peer figures, and price points — NOT Q&A answers or investment conclusions.
    """
    t = "KOTAKBANK"
    docs = [
        _ev(
            "raw:kotak:rbi:2024-04-24",
            source="RBI / Exchange announcement",
            date="2024-04-24",
            evidence_type="regulatory_filing",
            ticker=t,
            text=(
                "Reserve Bank of India directed Kotak Mahindra Bank to cease onboarding "
                "new customers through its online and mobile banking channels and to stop "
                "issuing new credit cards, citing deficiencies in IT systems and digital "
                "service delivery, pending satisfactory remediation."
            ),
            confidence_contribution=0.9,
        ),
        _ev(
            "raw:kotak:bse:2024-04-24",
            source="BSE / NSE corporate announcement",
            date="2024-04-24",
            evidence_type="exchange_announcement",
            ticker=t,
            text=(
                "Kotak Mahindra Bank informed the exchanges of receipt of RBI directions "
                "restricting digital onboarding of new customers and issuance of new credit "
                "cards. The Bank stated it would engage with the regulator and strengthen IT controls."
            ),
            confidence_contribution=0.85,
        ),
        _ev(
            "raw:kotak:call:fy24q4",
            source="Kotak Mahindra Bank Q4 FY24 earnings call transcript",
            date="2024-05-04",
            evidence_type="earnings_call",
            ticker=t,
            text=(
                "Management stated that IT remediation and customer experience upgrades are "
                "priority programs; digital acquisition pause is expected to affect near-term "
                "customer adds while the liability franchise and credit costs remain the focus. "
                "Management characterised issues as operational/IT rather than capital adequacy."
            ),
            confidence_contribution=0.7,
        ),
        _ev(
            "raw:kotak:ar:fy24-excerpt",
            source="Kotak Mahindra Bank Annual Report FY24 (excerpt)",
            date="2024-06-30",
            evidence_type="annual_report",
            ticker=t,
            text=(
                "Board commentary noted investments in technology resilience, cybersecurity, "
                "and digital platforms. Risk disclosures referenced regulatory oversight of "
                "IT systems and operational risk frameworks."
            ),
            confidence_contribution=0.65,
        ),
        _ev(
            "raw:kotak:qtr:fy24q4-fs",
            source="Standalone financial results Q4 FY24",
            date="2024-05-04",
            evidence_type="financial_statement",
            ticker=t,
            text=(
                "Net interest income and operating profit disclosed for Q4 FY24; GNPA and NNPA "
                "ratios reported within management's stated band. Results do not separately "
                "quantify the full multi-quarter impact of digital onboarding restrictions."
            ),
            confidence_contribution=0.75,
            metrics={
                "period": "FY24Q4",
                "npa_commentary": "within_stated_band",
                "restriction_impact_quantified": False,
            },
        ),
        _ev(
            "raw:kotak:qtr:fy25q1-fs",
            source="Standalone financial results Q1 FY25",
            date="2024-07-20",
            evidence_type="quarterly_report",
            ticker=t,
            text=(
                "Post-restriction quarter: deposit growth and credit card additions commentary "
                "indicate slower digital-led acquisition versus prior run-rate. Asset quality "
                "ratios remained the primary disclosed credit metric."
            ),
            confidence_contribution=0.72,
            metrics={
                "period": "FY25Q1",
                "digital_acquisition": "slower_vs_prior",
                "restriction_still_active": True,
            },
        ),
        _ev(
            "raw:kotak:ppt:fy25q1",
            source="Investor presentation Q1 FY25",
            date="2024-07-20",
            evidence_type="investor_presentation",
            ticker=t,
            text=(
                "Presentation slides highlight liability franchise metrics, digital initiative "
                "roadmap, and remediation milestones under discussion with RBI. No slide states "
                "a definitive date for full restriction removal."
            ),
            confidence_contribution=0.6,
        ),
        _ev(
            "raw:kotak:corp:2024-05",
            source="Corporate actions / board updates",
            date="2024-05-15",
            evidence_type="corporate_action",
            ticker=t,
            text=(
                "Board/committee updates referenced technology governance enhancements and "
                "management accountability for IT remediation programs."
            ),
            confidence_contribution=0.55,
        ),
        _ev(
            "raw:kotak:px:2024-04-24",
            source="Exchange price series",
            date="2024-04-24",
            evidence_type="historical_price",
            ticker=t,
            text="Equity price declined on announcement day relative to prior close (market reaction).",
            confidence_contribution=0.4,
            metrics={"event_day_move": "negative", "vs_nifty_bank": "underperformed"},
        ),
        _ev(
            "raw:peer:hdfc:fy25q1",
            source="HDFC Bank quarterly results (peer)",
            date="2024-07-20",
            evidence_type="peer_financial",
            ticker=t,
            peer_ticker="HDFCBANK",
            text=(
                "HDFC Bank continued digital and liability franchise disclosure without an "
                "equivalent RBI digital-onboarding restriction in the same window."
            ),
            confidence_contribution=0.55,
        ),
        _ev(
            "raw:peer:icici:fy25q1",
            source="ICICI Bank quarterly results (peer)",
            date="2024-07-27",
            evidence_type="peer_financial",
            ticker=t,
            peer_ticker="ICICIBANK",
            text=(
                "ICICI Bank reported ongoing digital acquisition commentary; no matching RBI "
                "restriction event disclosed in the same period."
            ),
            confidence_contribution=0.55,
        ),
        _ev(
            "raw:peer:axis:fy25q1",
            source="Axis Bank quarterly results (peer)",
            date="2024-07-24",
            evidence_type="peer_financial",
            ticker=t,
            peer_ticker="AXISBANK",
            text=(
                "Axis Bank digital and retail growth disclosures provide a peer baseline without "
                "an equivalent regulatory digital freeze in April 2024."
            ),
            confidence_contribution=0.55,
        ),
        _ev(
            "raw:kotak:call:fy25q1",
            source="Kotak Mahindra Bank Q1 FY25 earnings call transcript",
            date="2024-07-20",
            evidence_type="earnings_call",
            ticker=t,
            text=(
                "Management reiterated remediation progress with RBI engagement; acknowledged "
                "near-term pressure on new digital customer acquisition and new credit card "
                "issuance until restrictions are lifted. No unconditional timeline guaranteed."
            ),
            confidence_contribution=0.7,
        ),
    ]
    return {
        "schema": "ist02.raw_corpus.v1",
        "case_id": "IST-02",
        "ticker": t,
        "event": {
            "name": "RBI business restrictions on Kotak Mahindra Bank",
            "anchor_period": "2024-04",
            "regulator": "RBI",
        },
        "peers": ["HDFCBANK", "ICICIBANK", "AXISBANK"],
        "documents": docs,
        "document_count": len(docs),
        "fixture_answers": False,
        "prewritten_conclusions": False,
        "note": "Raw disclosures/metrics only — institutional conclusions must be assembled by modules.",
    }


def corpus_to_documents(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    """Shape raw corpus rows into FIRE/FIL-friendly document dicts."""
    out = []
    for d in corpus.get("documents") or []:
        out.append(
            {
                "doc_id": d.get("evidence_id"),
                "evidence_id": d.get("evidence_id"),
                "ticker": d.get("ticker"),
                "doc_type": d.get("evidence_type"),
                "source": d.get("source"),
                "date": d.get("date"),
                "as_of": d.get("date"),
                "text": d.get("text"),
                "content": d.get("text"),
                "metrics": d.get("metrics") or {},
                "peer_ticker": d.get("peer_ticker"),
                "confidence_contribution": d.get("confidence_contribution"),
            }
        )
    return out


def corpus_to_series_map(corpus: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract simple period metrics into a series_map for FIRE soft input."""
    series: dict[str, list[dict[str, Any]]] = {}
    for d in corpus.get("documents") or []:
        metrics = d.get("metrics") or {}
        if not metrics:
            continue
        period = str(metrics.get("period") or d.get("date") or "unknown")
        for key, val in metrics.items():
            if key == "period":
                continue
            series.setdefault(key, []).append(
                {
                    "period": period,
                    "value": val,
                    "evidence_id": d.get("evidence_id"),
                    "date": d.get("date"),
                    "source": d.get("source"),
                }
            )
    return series


def load_corpus(case_id: str = "IST-02", corpus: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if corpus is not None:
        return deepcopy(corpus)
    if str(case_id).upper() in {"IST-02", "IST02", "KOTAK", "KOTAKBANK"}:
        return kotak_rbi_april_2024_raw_corpus()
    raise KeyError(f"no raw corpus for case: {case_id}")
