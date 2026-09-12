"""Living management profiles — evidence-backed institutional memory (V1 seed).

Profiles are soft memory objects; FIL/FDI refresh qualitative inputs.
No subjective opinion without an evidence hook.
"""

from __future__ import annotations

from typing import Any

from management_intelligence.schema import DecisionRecord, ExecutiveProfile, GuidanceEvent

PROFILES: dict[str, dict[str, Any]] = {
    "HDFCBANK": {
        "ticker": "HDFCBANK",
        "company": "HDFC Bank",
        "executives": [
            ExecutiveProfile("CEO", "Sashidhar Jagdishan", "2020", notes="Professional bank leadership post HDFC Ltd merger integration").to_dict(),
            ExecutiveProfile("CFO", "Srinivasan Vaidyanathan", notes="Finance leadership").to_dict(),
            ExecutiveProfile("Chairman", "Atanu Chakraborty", notes="Non-executive chair").to_dict(),
        ],
        "board": {
            "independence": "majority_independent_disclosed",
            "audit_committee": "active",
            "compensation_committee": "active",
            "notes": "Large-cap private bank governance; promoter legacy via HDFC group history",
        },
        "dna_prior": ["Professional Steward", "Operator", "Capital Allocator"],
        "guidance_events": [
            GuidanceEvent(
                "hdfc_g_nim_q4fy26",
                "HDFCBANK",
                "NIM",
                "Q4FY26",
                "NIM near prior-quarter levels; deposit costs elevated but manageable",
                "maintained",
                "partially_delivered",
                "2026-04-20",
                "fdi_prior_hdfc_q4fy26",
                2,
            ).to_dict(),
            GuidanceEvent(
                "hdfc_g_growth_q1fy27",
                "HDFCBANK",
                "Loan_Growth",
                "Q1FY27",
                "Maintain medium-term loan growth; NIM near-term pressure acknowledged",
                "maintained",
                "pending",
                "2026-07-18",
                "hdfc_pres_q1fy27",
                2,
            ).to_dict(),
            GuidanceEvent(
                "hdfc_g_nim_q1fy27",
                "HDFCBANK",
                "NIM",
                "Q1FY27",
                "Expect gradual NIM stabilization",
                "maintained",
                "pending",
                "2026-07-18",
                "hdfc_pres_q1fy27",
                2,
            ).to_dict(),
            GuidanceEvent(
                "hdfc_g_hist_casa",
                "HDFCBANK",
                "CASA",
                "FY24-FY26",
                "Liability franchise rebuild / granular deposits priority",
                "maintained",
                "missed",
                "2026-03-31",
                "hdfc_hist_cet1_panel",
                1,
            ).to_dict(),
        ],
        "credibility_claims": [
            {
                "claim_id": "hdfc_c_margins_improve",
                "statement": "Margins / NIM should stabilize then improve",
                "as_of": "2026-04-20",
                "outcome": "incorrect",  # NIM 3.40 → 3.26
                "period_checked": "Q1FY27",
                "source_doc": "fdi_prior_hdfc_q4fy26",
            },
            {
                "claim_id": "hdfc_c_cet1_resilience",
                "statement": "Prioritise balance-sheet resilience / CET1 buffer",
                "as_of": "2026-07-18",
                "outcome": "correct",  # CET1 remains >16%
                "period_checked": "Q1FY27",
                "source_doc": "hdfc_pres_q1fy27",
            },
            {
                "claim_id": "hdfc_c_deposit_rebuild",
                "statement": "Rebuild liability franchise / granular deposits",
                "as_of": "2025-01-01",
                "outcome": "partially_correct",  # deposits grow but CASA mix still soft
                "period_checked": "Q1FY27",
                "source_doc": "hdfc_pres_q1fy27",
            },
        ],
        "execution": [
            {"initiative": "HDFC Ltd merger integration", "status": "completed", "as_of": "FY25", "notes": "Legal merger complete; liability mix still normalizing"},
            {"initiative": "Liability franchise rebuild", "status": "delayed", "as_of": "Q1FY27", "notes": "CASA still below multi-year average"},
            {"initiative": "Granular deposit expansion", "status": "in_progress", "as_of": "Q1FY27", "notes": "Deposit growth positive; mix skewed to term deposits"},
        ],
        "capital_allocation": [
            DecisionRecord(
                "hdfc_d_organic",
                "HDFCBANK",
                "Prefer organic growth; no extraordinary capital raise",
                "Preserve CET1 buffer while growing loans",
                "Maintain CET1 >16% with loan growth",
                "CET1 17.4% with advances growth continuing",
                "value_creating",
                "2026-07-18",
                "Capital buffer preserved through integration",
                "hdfc_pres_q1fy27",
            ).to_dict(),
            DecisionRecord(
                "hdfc_d_no_buyback",
                "HDFCBANK",
                "No buyback announced",
                "Prioritise balance-sheet resilience",
                "Retain capital for franchise rebuild",
                "No buyback; CET1 intact",
                "neutral",
                "2026-07-18",
                "Distribution deferred in favour of capital strength",
                "hdfc_pres_q1fy27",
            ).to_dict(),
        ],
        "acquisitions": [
            {
                "name": "HDFC Ltd merger",
                "purchase_price": "share-swap merger",
                "strategic_rationale": "Combine mortgage franchise with bank liability engine",
                "integration_progress": "legal complete; liability economics still normalizing",
                "synergies_promised": "Cross-sell and funding synergies",
                "synergies_realised": "partial",
                "roic_impact": "mixed_near_term",
                "shareholder_value_impact": "needs_monitoring",
                "as_of": "Q1FY27",
            }
        ],
        "governance_events": [
            {"event": "Dividend policy unchanged", "as_of": "Q1FY27", "severity": "low", "source_doc": "hdfc_pr_q1fy27"},
            {"event": "Related-party / contingent items unchanged vs prior quarter", "as_of": "Q1FY27", "severity": "low", "source_doc": "hdfc_pr_q1fy27"},
        ],
        "communication": {
            "transparency": 78,
            "consistency": 72,
            "clarity": 80,
            "tone": "cautious",
            "risk_acknowledgement": 85,
            "overconfidence": 25,
            "guidance_stability": 70,
            "notes": "Acknowledges deposit-cost / NIM pressure; maintains medium-term growth language",
        },
        "incentives": {
            "alignment": "partially_aligned",
            "long_term_incentives": "present",
            "stock_ownership": "executive_ownership_disclosed_historically",
            "notes": "Large-cap bank incentive structures; detailed comp tables pending denser FIL ingest",
            "score": 70,
        },
        "succession": {
            "ceo_stability": "stable",
            "cfo_stability": "stable",
            "key_person_risk": "moderate",
            "succession_planning": "board_disclosed_process",
            "score": 72,
        },
        "timeline": [
            {"as_of": "2020", "event": "CEO appointment — Sashidhar Jagdishan", "type": "leadership"},
            {"as_of": "2023-07", "event": "HDFC Ltd merger effective", "type": "acquisition"},
            {"as_of": "2026-04", "event": "Q4FY26: constructive tone; NIM manageable language", "type": "communication"},
            {"as_of": "2026-07", "event": "Q1FY27: NIM pressure acknowledged; guidance maintained; CASA soft", "type": "guidance"},
        ],
    },
    "NESTLEIND": {
        "ticker": "NESTLEIND",
        "company": "Nestlé India",
        "executives": [
            ExecutiveProfile("CEO", "Suresh Narayanan", notes="Long-tenure FMCG operator").to_dict(),
            ExecutiveProfile("CFO", "Deepika Ramesh Warrier", notes="Finance leadership").to_dict(),
        ],
        "board": {"independence": "board_with_independents", "audit_committee": "active", "compensation_committee": "active"},
        "dna_prior": ["Operator", "Professional Steward", "Growth Builder"],
        "guidance_events": [
            GuidanceEvent(
                "nestle_g_premium",
                "NESTLEIND",
                "Revenue_Growth",
                "Q1FY27",
                "Continue premiumisation; no formal numeric cut",
                "maintained",
                "delivered",
                "2026-07-22",
                "nestle_bse_q1fy27",
                1,
            ).to_dict(),
        ],
        "credibility_claims": [
            {
                "claim_id": "nestle_c_premium",
                "statement": "Premiumisation / distribution strength supports growth",
                "as_of": "2026-04-01",
                "outcome": "correct",
                "period_checked": "Q1FY27",
                "source_doc": "nestle_bse_q1fy27",
            }
        ],
        "execution": [
            {"initiative": "Distribution expansion", "status": "completed", "as_of": "Q1FY27"},
            {"initiative": "Premiumisation", "status": "exceeded", "as_of": "Q1FY27", "notes": "Sales +25.4% Q1FY27"},
        ],
        "capital_allocation": [
            DecisionRecord(
                "nestle_d_brand",
                "NESTLEIND",
                "Brand and distribution investment",
                "Sustain pricing power and reach",
                "Support volume/value growth",
                "Strong Q1 sales growth with dividend capacity intact",
                "value_creating",
                "2026-07-22",
                "Organic brand investment remains primary allocation",
                "nestle_bse_q1fy27",
            ).to_dict(),
        ],
        "acquisitions": [],
        "governance_events": [],
        "communication": {
            "transparency": 80,
            "consistency": 82,
            "clarity": 84,
            "tone": "constructive",
            "risk_acknowledgement": 70,
            "overconfidence": 30,
            "guidance_stability": 80,
        },
        "incentives": {"alignment": "aligned", "score": 75, "notes": "MNC subsidiary incentive norms"},
        "succession": {"ceo_stability": "stable", "key_person_risk": "moderate", "score": 74},
        "timeline": [
            {"as_of": "2026-07-22", "event": "Q1FY27 results: sales +25.4%, PAT ₹975.1 cr", "type": "execution"},
        ],
    },
    "TCS": {
        "ticker": "TCS",
        "company": "Tata Consultancy Services",
        "executives": [
            ExecutiveProfile("CEO", "K. Krithivasan", "2023", notes="Internal succession").to_dict(),
            ExecutiveProfile("CFO", "Samir Seksaria", notes="Finance leadership").to_dict(),
        ],
        "board": {"independence": "tata_group_governance", "audit_committee": "active"},
        "dna_prior": ["Operator", "Professional Steward", "Capital Allocator"],
        "guidance_events": [
            GuidanceEvent(
                "tcs_g_margin",
                "TCS",
                "EBIT_Margin",
                "FY26",
                "Industry-leading margins through utilization and pricing discipline",
                "maintained",
                "delivered",
                "2026-03-31",
                "seed_panel",
                2,
            ).to_dict(),
        ],
        "credibility_claims": [
            {
                "claim_id": "tcs_c_margins",
                "statement": "Sustain superior EBIT margins vs Indian IT peers",
                "as_of": "FY24",
                "outcome": "correct",
                "period_checked": "FY26",
                "source_doc": "it_services_peer_pack",
            }
        ],
        "execution": [
            {"initiative": "Margin discipline", "status": "exceeded", "as_of": "FY26"},
            {"initiative": "Large-deal pipeline", "status": "in_progress", "as_of": "FY26"},
        ],
        "capital_allocation": [
            DecisionRecord(
                "tcs_d_dividends",
                "TCS",
                "Consistent dividends / shareholder returns",
                "High cash conversion supports distributions",
                "Sustain payout with growth investment",
                "Cash conversion leadership vs peers (PIL seed)",
                "value_creating",
                "FY26",
                "Return of capital alongside organic investment",
                "seed_panel",
            ).to_dict(),
        ],
        "acquisitions": [],
        "governance_events": [],
        "communication": {
            "transparency": 82,
            "consistency": 85,
            "clarity": 84,
            "tone": "measured",
            "risk_acknowledgement": 75,
            "overconfidence": 20,
            "guidance_stability": 80,
        },
        "incentives": {"alignment": "aligned", "score": 78},
        "succession": {"ceo_stability": "stable_post_transition", "key_person_risk": "low_moderate", "score": 80},
        "timeline": [
            {"as_of": "2023", "event": "CEO succession — K. Krithivasan", "type": "leadership"},
        ],
    },
}


def profile_for(ticker: str) -> dict[str, Any] | None:
    t = ticker.upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND"}
    t = aliases.get(t, t)
    p = PROFILES.get(t)
    return dict(p) if p else None


def list_profiles() -> list[str]:
    return sorted(PROFILES.keys())
