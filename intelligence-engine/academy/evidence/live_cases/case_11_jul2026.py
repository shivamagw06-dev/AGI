"""ACS Live Case #11 — July 2026 Market Stress — Evidence Intelligence Pack.

IMMUTABLE case pack for ACS/IRS. Sources are attributed. Priors are labelled priors.
"""

from __future__ import annotations

from typing import Any

from academy.evidence.schema import Claim, DecisionTrigger, MetricPoint, SourceRef

CASE_ID = "acs_live_11_jul2026"
CASE_TITLE = "July 2026 Market Stress — Oil + Private Bank Margins"


def sources() -> dict[str, SourceRef]:
    return {
        "hdfc_pr_q1fy27": SourceRef(
            "hdfc_pr_q1fy27",
            "HDFC Bank",
            "Press Release — Results for quarter ended 30 June 2026",
            "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/about-us/financial-results/2026-2027/quarter-1/press-release-june-2026.pdf",
            "2026-07-18",
            "filing",
            0.95,
        ),
        "hdfc_pres_q1fy27": SourceRef(
            "hdfc_pres_q1fy27",
            "HDFC Bank",
            "Q1FY27 Earnings Presentation",
            "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/about-us/financial-results/2026-2027/quarter-1/q1fy27-earnings-presentation.pdf",
            "2026-07-18",
            "filing",
            0.95,
        ),
        "fe_hdfc_q1": SourceRef(
            "fe_hdfc_q1",
            "Financial Express",
            "HDFC Bank reports steady Q1; net up 5%",
            "https://www.financialexpress.com/business/banking-finance/hdfc-bank-reports-steady-q1-net-up-5/4295872/",
            "2026-07",
            "wire",
            0.75,
        ),
        "outlook_banks_q1": SourceRef(
            "outlook_banks_q1",
            "Outlook Business",
            "Why HDFC Bank, Axis Bank And Kotak Shares Fell Despite Q1 Profit Growth",
            "https://www.outlookbusiness.com/markets/why-hdfc-bank-axis-bank-and-kotak-shares-fell-despite-q1-profit-growth",
            "2026-07",
            "wire",
            0.72,
        ),
        "hbl_banks_q1": SourceRef(
            "hbl_banks_q1",
            "Hindu Business Line",
            "Bank stocks underperform post Q1 — ICICI gains; HDFC/Axis/Kotak decline",
            "https://www.thehindubusinessline.com/markets/stock-markets/bank-stocks-underperform-icici-bank-gains-while-hdfc-bank-axis-bank-kotak-mahindra-yes-bank-decline/article71243829.ece",
            "2026-07",
            "wire",
            0.72,
        ),
        "upstox_week": SourceRef(
            "upstox_week",
            "Upstox",
            "Weekly Market Wrap — Nifty/Sensex decline; crude spike; HDFC leads losses",
            "https://upstox.com/news/market-news/stocks/weekly-market-wrap-nifty-50-sensex-decline-on-rising-crude-oil-prices-geopolitical-tensions-hdfc-bank-leads-losses/article-197552/",
            "2026-07-25",
            "wire",
            0.70,
        ),
        "nestle_bse_q1": SourceRef(
            "nestle_bse_q1",
            "Nestlé India / BSE",
            "Q1 FY 2026-27 results outcome",
            "https://www.bseindia.com/xml-data/corpfiling/AttachLive/7c705f10-1408-4d37-9a13-83f57e3f4f7a.pdf",
            "2026-07-22",
            "filing",
            0.95,
        ),
        "ms_comment_hbl": SourceRef(
            "ms_comment_hbl",
            "Morgan Stanley (via Hindu Business Line)",
            "Broker comment: HDFC/Axis NII miss on NIM compression",
            "https://www.thehindubusinessline.com/markets/stock-markets/bank-stocks-underperform-icici-bank-gains-while-hdfc-bank-axis-bank-kotak-mahindra-yes-bank-decline/article71243829.ece",
            "2026-07",
            "broker",
            0.70,
        ),
        "bbg_est_fe": SourceRef(
            "bbg_est_fe",
            "Bloomberg estimates (via Financial Express)",
            "HDFC PAT/NII vs Bloomberg consensus estimates",
            "https://www.financialexpress.com/business/banking-finance/hdfc-bank-reports-steady-q1-net-up-5/4295872/",
            "2026-07",
            "broker",
            0.70,
        ),
    }


def metrics() -> dict[str, MetricPoint]:
    return {
        "hdfc_pat_q1fy27": MetricPoint("PAT", 190.6, "₹ bn", "Q1FY27", "HDFC Bank", "hdfc_pres_q1fy27"),
        "hdfc_nii_q1fy27": MetricPoint("NII", 335.3, "₹ bn", "Q1FY27", "HDFC Bank", "hdfc_pres_q1fy27"),
        "hdfc_nim_q1fy27": MetricPoint(
            "NIM_total_assets",
            3.26,
            "%",
            "Q1FY27",
            "HDFC Bank",
            "hdfc_pr_q1fy27",
            peer_context={
                "axis_nim_q1fy27": 3.46,
                "axis_nim_q1fy26": 3.80,
                "axis_nim_q4fy26": 3.73,
                "axis_source": "outlook_banks_q1",
                "note": "Peer NIMs from earnings coverage — not a full 5y panel",
            },
        ),
        "hdfc_nim_prior_q": MetricPoint("NIM_total_assets", 3.40, "%", "Q4FY26", "HDFC Bank", "fe_hdfc_q1"),
        "hdfc_roe_q1fy27": MetricPoint("RoE", 13.8, "%", "Q1FY27", "HDFC Bank", "hdfc_pres_q1fy27"),
        "hdfc_roa_q1fy27": MetricPoint("RoA", 1.85, "%", "Q1FY27", "HDFC Bank", "hdfc_pres_q1fy27"),
        "hdfc_casa_pct": MetricPoint("CASA_ratio", 32.3, "%", "30-Jun-2026", "HDFC Bank", "hdfc_pr_q1fy27"),
        "hdfc_deposits_yoy": MetricPoint("Deposits_YoY", 14.7, "%", "30-Jun-2026", "HDFC Bank", "hdfc_pr_q1fy27"),
        "hdfc_td_yoy": MetricPoint("Time_deposits_YoY", 17.4, "%", "30-Jun-2026", "HDFC Bank", "hdfc_pr_q1fy27"),
        "hdfc_casa_yoy": MetricPoint("CASA_deposits_YoY", 9.4, "%", "30-Jun-2026", "HDFC Bank", "hdfc_pr_q1fy27"),
        "hdfc_adv_yoy": MetricPoint("Gross_advances_YoY", 15.4, "%", "30-Jun-2026", "HDFC Bank", "fe_hdfc_q1"),
        "hdfc_gnpa": MetricPoint("GNPA", 1.17, "%", "30-Jun-2026", "HDFC Bank", "hdfc_pres_q1fy27"),
        "hdfc_cet1": MetricPoint("CET1", 17.4, "%", "30-Jun-2026", "HDFC Bank", "hdfc_pres_q1fy27"),
        "hdfc_car": MetricPoint("CAR", 19.6, "%", "30-Jun-2026", "HDFC Bank", "hdfc_pres_q1fy27"),
        "hdfc_credit_cost": MetricPoint("Credit_cost", 40, "bps", "Q1FY27", "HDFC Bank", "fe_hdfc_q1"),
        "bbg_pat_est": MetricPoint("Bloomberg_PAT_est", 197.20, "₹ bn", "Q1FY27", "HDFC Bank", "bbg_est_fe"),
        "bbg_nii_est": MetricPoint("Bloomberg_NII_est", 342.57, "₹ bn", "Q1FY27", "HDFC Bank", "bbg_est_fe"),
        "nifty_week": MetricPoint("Nifty_weekly_return", -2.3, "%", "week_ended_2026-07-25", "NIFTY50", "upstox_week"),
        "sensex_week": MetricPoint("Sensex_weekly_return", -2.7, "%", "week_ended_2026-07-25", "SENSEX", "upstox_week"),
        "pvt_bank_week": MetricPoint("Nifty_Private_Bank_weekly", -4.6, "%", "week_ended_2026-07-25", "NIFTY_PRIVATE_BANK", "upstox_week"),
        "brent_spike": MetricPoint(
            "Brent",
            ">100 briefly; ~96.78 Fri close (wrap)",
            "USD/bbl",
            "week_ended_2026-07-25",
            "BRENT",
            "upstox_week",
        ),
        "nestle_pat": MetricPoint("PAT", 975.1, "₹ cr", "Q1FY27", "Nestlé India", "nestle_bse_q1"),
        "nestle_sales_growth": MetricPoint("Sales_growth", 25.4, "%", "Q1FY27", "Nestlé India", "nestle_bse_q1"),
        "axis_nim": MetricPoint("NIM", 3.46, "%", "Q1FY27", "Axis Bank", "outlook_banks_q1"),
    }


def claims() -> list[Claim]:
    return [
        Claim(
            "c11_hdfc_nim_fact",
            "HDFC Bank NIM was 3.26% on total assets in Q1FY27, below 3.40% in Q4FY26.",
            "fact",
            analyst="financial",
            company="HDFC Bank",
            ticker="HDFCBANK",
            metric_ids=["hdfc_nim_q1fy27", "hdfc_nim_prior_q"],
            source_ids=["hdfc_pr_q1fy27", "fe_hdfc_q1"],
            peers_required=["ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
            history_required=["NIM_8q"],
            notes="Peer significance still incomplete without full history panel",
        ),
        Claim(
            "c11_hdfc_nii_vs_bbg",
            "HDFC NII ₹335.3 bn missed Bloomberg estimate ₹342.57 bn; PAT ₹190.6 bn missed Bloomberg ₹197.2 bn.",
            "street",
            analyst="financial",
            company="HDFC Bank",
            ticker="HDFCBANK",
            metric_ids=["hdfc_nii_q1fy27", "hdfc_pat_q1fy27", "bbg_nii_est", "bbg_pat_est"],
            source_ids=["hdfc_pres_q1fy27", "bbg_est_fe"],
            notes="Consensus named: Bloomberg estimates via Financial Express — not unspecified 'Street'",
        ),
        Claim(
            "c11_hdfc_casa_mix",
            "CASA was 32.3% of deposits; time deposits grew 17.4% YoY vs CASA deposits 9.4% YoY.",
            "fact",
            analyst="financial",
            company="HDFC Bank",
            ticker="HDFCBANK",
            metric_ids=["hdfc_casa_pct", "hdfc_td_yoy", "hdfc_casa_yoy"],
            source_ids=["hdfc_pr_q1fy27"],
            history_required=["CASA_8q", "CoF_8q"],
            peers_required=["ICICIBANK", "SBIN"],
        ),
        Claim(
            "c11_ms_nim_comment",
            "Morgan Stanley (via HBL) attributed HDFC/Axis NII misses to higher NIM compression.",
            "street",
            analyst="sector",
            company="HDFC Bank",
            ticker="HDFCBANK",
            source_ids=["ms_comment_hbl", "hbl_banks_q1"],
            notes="Broker named explicitly",
        ),
        Claim(
            "c11_macro_oil_week",
            "In the week ended 25 Jul 2026, Nifty fell ~2.3% and Brent spiked (briefly >$100 per market wrap).",
            "market",
            analyst="macro",
            metric_ids=["nifty_week", "brent_spike", "pvt_bank_week"],
            source_ids=["upstox_week"],
        ),
        Claim(
            "c11_nestle_defensive",
            "Nestlé India Q1FY27 sales +25.4%, PAT ₹975.1 cr; defensive/FMCG bid on results.",
            "fact",
            analyst="sector",
            company="Nestlé India",
            ticker="NESTLEIND",
            metric_ids=["nestle_pat", "nestle_sales_growth"],
            source_ids=["nestle_bse_q1"],
        ),
        Claim(
            "c11_franchise_judgement",
            "Judgement: expectations/NIM path challenged more than franchise identity — pending peer CoF/CASA panel.",
            "judgement",
            analyst="business",
            company="HDFC Bank",
            ticker="HDFCBANK",
            supports=["c11_hdfc_casa_mix", "c11_hdfc_nim_fact"],
            contradicts=[],
            peers_required=["ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
            history_required=["deposit_share_5y", "CASA_5y"],
            notes="Not a fact — judgement with incomplete peer/history pillars",
        ),
        Claim(
            "c11_prior_moat_softening",
            "Prior (not evidence): multi-year narrative that liability uniqueness may be softening post-merger.",
            "prior",
            analyst="business",
            company="HDFC Bank",
            ticker="HDFCBANK",
            notes="Institutional prior only — must not be cited as observed evidence",
        ),
    ]


def triggers() -> list[DecisionTrigger]:
    return [
        DecisionTrigger(
            "t11_casa",
            "c11_franchise_judgement",
            "CASA ratio and cost-of-funds gap vs ICICI & SBI for next 2 quarters",
            "Q2–Q3 FY27 prints",
            "CASA > 35% AND CoF gap vs ICICI stable/improving",
            "Committee reconvenes — funding-improving file",
            "Keep trajectory challenge open; do not upgrade uniqueness claim",
        ),
        DecisionTrigger(
            "t11_nim",
            "c11_hdfc_nim_fact",
            "NIM vs Axis/ICICI/Kotak and vs HDFC 8-quarter history",
            "Next 2 quarterly prints",
            "NIM stabilizes ≥ prior-year run-rate on IEA basis without adverse mix",
            "Reduce weight on structural-margin bear case",
            "Maintain margin-thesis challenge",
        ),
        DecisionTrigger(
            "t11_oil",
            "c11_macro_oil_week",
            "Brent + CPI + INR + FII flows over 4–6 weeks",
            "Through Aug–Sep 2026",
            "Brent < $85 and INR/FII stabilize while bank breadth recovers",
            "Raise weight on earnings-idiosyncratic explanation",
            "Keep macro amplification thesis",
        ),
    ]


def pack() -> dict[str, Any]:
    return {
        "case_id": CASE_ID,
        "title": CASE_TITLE,
        "eil_role": "Populate Fact rows; forbid priors-as-facts; name street sources",
        "sources": {k: v.to_dict() for k, v in sources().items()},
        "metrics": {k: v.to_dict() for k, v in metrics().items()},
        "claims": [c.to_dict() for c in claims()],
        "decision_triggers": [t.to_dict() for t in triggers()],
        "peer_panel_status": {
            "required": ["ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
            "partially_populated": ["AXISBANK_NIM_Q1FY27"],
            "missing": ["ICICI_NIM_CASA_CoF_panel", "SBI_panel", "Kotak_panel", "5y_history"],
        },
        "transmission_macro": [
            "Oil",
            "Current Account",
            "INR",
            "Imported Inflation",
            "Bond Yields",
            "Cost of Capital",
            "Valuation risk premium",
            "Market",
        ],
    }
