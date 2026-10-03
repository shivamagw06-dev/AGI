"""Structured Tier-1/2 filing corpus for FIL V1.

Documents are institutional memory objects derived from official company sources
(same URLs as EIL Live Case #11). Raw PDF bytes are not required — FIL ingests
structured filing payloads with full provenance.
"""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import FilingDocument


def seed_documents() -> list[FilingDocument]:
    return [
        FilingDocument(
            doc_id="hdfc_pr_q1fy27",
            ticker="HDFCBANK",
            company="HDFC Bank",
            doc_type="press_release",
            title="Press Release — Results for quarter ended 30 June 2026",
            period="Q1FY27",
            as_of="2026-07-18",
            url="https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/about-us/financial-results/2026-2027/quarter-1/press-release-june-2026.pdf",
            evidence_tier=4,
            source_publisher="HDFC Bank",
            text=(
                "HDFC Bank Q1FY27 results. Net Interest Margin on total assets 3.26%. "
                "CASA ratio 32.3%. Deposits grew 14.7% YoY. Time deposits grew 17.4% YoY. "
                "CASA deposits grew 9.4% YoY. Gross advances grew. "
                "Management notes deposit mix shift toward term deposits and funding-cost pressure. "
                "Capital remains strong. Dividend policy unchanged. "
                "Risks: competitive deposit pricing, interest-rate cycle, credit costs. "
                "Guidance: maintain medium-term loan growth; NIM near-term pressure acknowledged. "
                "Related party and contingent items unchanged vs prior quarter notes."
            ),
            tables=[
                {
                    "name": "key_metrics",
                    "rows": [
                        {"metric": "NIM", "value": 3.26, "unit": "%"},
                        {"metric": "CASA", "value": 32.3, "unit": "%"},
                        {"metric": "Deposits_YoY", "value": 14.7, "unit": "%"},
                        {"metric": "Time_deposits_YoY", "value": 17.4, "unit": "%"},
                        {"metric": "CASA_deposits_YoY", "value": 9.4, "unit": "%"},
                    ],
                }
            ],
            metadata={"exchange": "NSE/BSE", "fiscal": "FY27"},
        ),
        FilingDocument(
            doc_id="hdfc_pres_q1fy27",
            ticker="HDFCBANK",
            company="HDFC Bank",
            doc_type="investor_presentation",
            title="Q1FY27 Earnings Presentation",
            period="Q1FY27",
            as_of="2026-07-18",
            url="https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/about-us/financial-results/2026-2027/quarter-1/q1fy27-earnings-presentation.pdf",
            evidence_tier=2,
            source_publisher="HDFC Bank",
            text=(
                "Investor presentation Q1FY27. PAT 190.6 billion rupees. NII 335.3 billion. "
                "RoE 13.8%. RoA 1.85%. GNPA 1.17%. CET1 17.4%. CAR 19.6%. "
                "Credit cost contained. Segment: retail, wholesale, treasury. "
                "Management priorities: liability franchise rebuild, granular deposits, "
                "balance-sheet resilience, calibrated loan growth. "
                "Capital allocation: organic growth preferred; CET1 buffer preserved; "
                "no extraordinary capital raise. Buybacks not announced. "
                "Outlook: deposit costs elevated; expect gradual NIM stabilization. "
                "Guidance maintained on medium-term growth despite NIM compression. "
                "Accounting notes: no material revenue recognition change; "
                "exceptional items nil; goodwill monitoring ongoing post-merger."
            ),
            tables=[
                {
                    "name": "income_and_capital",
                    "rows": [
                        {"metric": "PAT", "value": 190.6, "unit": "₹ bn"},
                        {"metric": "NII", "value": 335.3, "unit": "₹ bn"},
                        {"metric": "ROE", "value": 13.8, "unit": "%"},
                        {"metric": "ROA", "value": 1.85, "unit": "%"},
                        {"metric": "GNPA", "value": 1.17, "unit": "%"},
                        {"metric": "CET1", "value": 17.4, "unit": "%"},
                        {"metric": "CAR", "value": 19.6, "unit": "%"},
                        {"metric": "Credit_Cost", "value": 40, "unit": "bps"},
                    ],
                }
            ],
        ),
        FilingDocument(
            doc_id="hdfc_hist_cet1_panel",
            ticker="HDFCBANK",
            company="HDFC Bank",
            doc_type="annual_report",
            title="Capital adequacy history panel (compiled from annual/quarterly filings)",
            period="FY22-FY26",
            as_of="2026-03-31",
            url="",
            evidence_tier=1,
            source_publisher="HDFC Bank",
            text=(
                "Historical CET1 from annual/quarterly filings: "
                "FY22 17.0%, FY23 16.5%, FY24 16.8%, FY25 17.0%, FY26 17.5%. "
                "CET1 remained above 16% for five consecutive years despite merger integration. "
                "Management prioritised balance-sheet resilience while maintaining loan growth."
            ),
            tables=[
                {
                    "name": "cet1_history",
                    "rows": [
                        {"metric": "CET1", "period": "FY22", "value": 17.0, "unit": "%"},
                        {"metric": "CET1", "period": "FY23", "value": 16.5, "unit": "%"},
                        {"metric": "CET1", "period": "FY24", "value": 16.8, "unit": "%"},
                        {"metric": "CET1", "period": "FY25", "value": 17.0, "unit": "%"},
                        {"metric": "CET1", "period": "FY26", "value": 17.5, "unit": "%"},
                    ],
                },
                {
                    "name": "casa_history",
                    "rows": [
                        {"metric": "CASA", "period": "FY22", "value": 48.0, "unit": "%"},
                        {"metric": "CASA", "period": "FY23", "value": 44.0, "unit": "%"},
                        {"metric": "CASA", "period": "FY24", "value": 38.0, "unit": "%"},
                        {"metric": "CASA", "period": "FY25", "value": 35.0, "unit": "%"},
                        {"metric": "CASA", "period": "FY26", "value": 33.5, "unit": "%"},
                    ],
                },
                {
                    "name": "nim_history",
                    "rows": [
                        {"metric": "NIM", "period": "FY22", "value": 4.00, "unit": "%"},
                        {"metric": "NIM", "period": "FY23", "value": 4.10, "unit": "%"},
                        {"metric": "NIM", "period": "FY24", "value": 3.60, "unit": "%"},
                        {"metric": "NIM", "period": "FY25", "value": 3.50, "unit": "%"},
                        {"metric": "NIM", "period": "FY26", "value": 3.40, "unit": "%"},
                    ],
                },
            ],
            metadata={"compiled_from": "annual_and_quarterly_filings", "validation": "partially_verified"},
        ),
        FilingDocument(
            doc_id="axis_q1fy27_results",
            ticker="AXISBANK",
            company="Axis Bank",
            doc_type="quarterly_results",
            title="Axis Bank Q1FY27 results coverage pack",
            period="Q1FY27",
            as_of="2026-07-20",
            url="https://www.outlookbusiness.com/markets/why-hdfc-bank-axis-bank-and-kotak-shares-fell-despite-q1-profit-growth",
            evidence_tier=1,
            source_publisher="Axis Bank / exchange disclosures",
            text=(
                "Axis Bank NIM 3.46% in Q1FY27 versus 3.80% Q1FY26 and 3.73% Q4FY26. "
                "Profit growth reported; market reaction negative on margin compression. "
                "Management commentary: funding costs and NIM pressure. "
                "Guidance: cautious near-term NIM; loan growth maintained."
            ),
            tables=[
                {
                    "name": "key_metrics",
                    "rows": [
                        {"metric": "NIM", "value": 3.46, "unit": "%"},
                        {"metric": "NIM", "period": "Q1FY26", "value": 3.80, "unit": "%"},
                        {"metric": "NIM", "period": "Q4FY26", "value": 3.73, "unit": "%"},
                    ],
                }
            ],
        ),
        FilingDocument(
            doc_id="nestle_bse_q1fy27",
            ticker="NESTLEIND",
            company="Nestlé India",
            doc_type="quarterly_results",
            title="Nestlé India Q1 FY 2026-27 results outcome",
            period="Q1FY27",
            as_of="2026-07-22",
            url="https://www.bseindia.com/xml-data/corpfiling/AttachLive/7c705f10-1408-4d37-9a13-83f57e3f4f7a.pdf",
            evidence_tier=1,
            source_publisher="Nestlé India / BSE",
            text=(
                "Nestlé India Q1FY27: Sales growth 25.4%. PAT 975.1 crore. "
                "Management highlights pricing and volume contribution; distribution strength. "
                "Segment: prepared dishes, milk products, confectionery, beverages. "
                "Risks: commodity inflation, competitive intensity. "
                "Capital allocation: brand investment and distribution; dividend capacity intact. "
                "Guidance: continue premiumisation; no formal numeric revenue guidance withdrawn or cut."
            ),
            tables=[
                {
                    "name": "key_metrics",
                    "rows": [
                        {"metric": "PAT", "value": 975.1, "unit": "₹ cr"},
                        {"metric": "Revenue_Growth", "value": 25.4, "unit": "%"},
                    ],
                }
            ],
        ),
        FilingDocument(
            doc_id="icici_seed_filing_stub",
            ticker="ICICIBANK",
            company="ICICI Bank",
            doc_type="quarterly_results",
            title="ICICI Bank CASA/NIM history stub pending full ingest",
            period="FY22-Q1FY27",
            as_of="2026-07-01",
            url="",
            evidence_tier=1,
            source_publisher="ICICI Bank",
            text=(
                "ICICI Bank funding trajectory comparatively stable. "
                "CASA FY22 45.0%, FY23 45.5%, FY24 45.0%, FY25 44.5%, FY26 44.0%, Q1FY27 43.8%. "
                "NIM FY22 3.90% through Q1FY27 4.05%. CET1 near 16.7% Q1FY27. "
                "Guidance maintained on growth; deposit franchise commentary constructive."
            ),
            tables=[
                {
                    "name": "casa_history",
                    "rows": [
                        {"metric": "CASA", "period": "FY22", "value": 45.0, "unit": "%"},
                        {"metric": "CASA", "period": "FY23", "value": 45.5, "unit": "%"},
                        {"metric": "CASA", "period": "FY24", "value": 45.0, "unit": "%"},
                        {"metric": "CASA", "period": "FY25", "value": 44.5, "unit": "%"},
                        {"metric": "CASA", "period": "FY26", "value": 44.0, "unit": "%"},
                        {"metric": "CASA", "period": "Q1FY27", "value": 43.8, "unit": "%"},
                    ],
                },
                {
                    "name": "nim_history",
                    "rows": [
                        {"metric": "NIM", "period": "FY22", "value": 3.90, "unit": "%"},
                        {"metric": "NIM", "period": "FY26", "value": 4.10, "unit": "%"},
                        {"metric": "NIM", "period": "Q1FY27", "value": 4.05, "unit": "%"},
                    ],
                },
                {
                    "name": "capital",
                    "rows": [{"metric": "CET1", "period": "Q1FY27", "value": 16.7, "unit": "%"}],
                },
            ],
            metadata={"validation": "partially_verified", "note": "stub until full annual OCR ingest"},
        ),
    ]


def corpus_index() -> list[dict[str, Any]]:
    return [
        {
            "doc_id": d.doc_id,
            "ticker": d.ticker,
            "doc_type": d.doc_type,
            "period": d.period,
            "evidence_tier": d.evidence_tier,
            "title": d.title,
        }
        for d in seed_documents()
    ]
