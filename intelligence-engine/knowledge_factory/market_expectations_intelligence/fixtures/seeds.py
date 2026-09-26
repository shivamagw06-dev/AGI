"""Phase-1 expectation seeds — company guidance, actuals, AGIB internal forecasts.

Public/auditable sources only. No broker consensus. No fabricated street estimates.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence.objects.expectation import (
    build_expectation,
)
from knowledge_factory.market_expectations_intelligence.schema import UNKNOWN


def _e(**kwargs: Any) -> dict[str, Any]:
    return build_expectation(**kwargs)


def curated_expectation_seeds() -> list[dict[str, Any]]:
    """Guidance → revisions → actuals for core names. Values are curated institutional seeds."""
    seeds: list[dict[str, Any]] = []

    # ----- INFY FY25 — guidance + AGIB forecast + actual -----
    seeds.append(
        _e(
            entity="INFY",
            metric="growth",
            period="FY25",
            forecast_value=3.5,
            forecast_range={"low": 1.0, "high": 3.5},
            unit="percent",
            kind="guidance",
            source="company_guidance",
            collector="imei.fixtures.guidance",
            available_from="2024-04-18",
            announcement_date="2024-04-18",
            confidence=0.92,
            evidence="INFY-Q4FY24-earnings-guidance",
            notes="Company-issued constant-currency revenue growth guidance band (seed).",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="INFY",
            metric="growth",
            period="FY25",
            forecast_value=3.0,
            forecast_range={"low": 1.0, "high": 3.0},
            unit="percent",
            kind="guidance",
            source="company_guidance",
            collector="imei.fixtures.guidance",
            available_from="2024-07-18",
            announcement_date="2024-07-18",
            confidence=0.92,
            evidence="INFY-Q1FY25-guidance-revision",
            notes="Company revised guidance (seed).",
            revision_sequence=1,
        )
    )
    seeds.append(
        _e(
            entity="INFY",
            metric="eps",
            period="FY25Q1",
            forecast_value=15.2,
            unit="inr",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-30",
            announcement_date="2024-06-30",
            confidence=0.75,
            evidence="AGIB-timestamped-forecast-INFY-FY25Q1-EPS",
            notes="AGIB timestamped internal forecast — not street consensus.",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="INFY",
            metric="eps",
            period="FY25Q1",
            forecast_value=15.8,
            unit="inr",
            kind="actual",
            source="company_earnings_release",
            collector="imei.fixtures.actuals",
            available_from="2024-07-18",
            announcement_date="2024-07-18",
            confidence=0.95,
            evidence="INFY-Q1FY25-reported-EPS",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="INFY",
            metric="revenue",
            period="FY25Q1",
            forecast_value=4715.0,
            unit="usd_mn",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-30",
            confidence=0.75,
            evidence="AGIB-timestamped-forecast-INFY-FY25Q1-REV",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="INFY",
            metric="revenue",
            period="FY25Q1",
            forecast_value=4740.0,
            unit="usd_mn",
            kind="actual",
            source="company_earnings_release",
            collector="imei.fixtures.actuals",
            available_from="2024-07-18",
            confidence=0.95,
            evidence="INFY-Q1FY25-reported-revenue",
            revision_sequence=0,
        )
    )

    # ----- TCS -----
    seeds.append(
        _e(
            entity="TCS",
            metric="growth",
            period="FY25",
            forecast_value=2.0,
            unit="percent",
            kind="guidance",
            source="company_guidance",
            collector="imei.fixtures.guidance",
            available_from="2024-04-12",
            confidence=0.88,
            evidence="TCS-FY25-outlook-commentary",
            notes="Directional company outlook seed (not a formal band).",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="TCS",
            metric="eps",
            period="FY25Q1",
            forecast_value=33.0,
            unit="inr",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-15",
            confidence=0.75,
            evidence="AGIB-forecast-TCS-FY25Q1-EPS",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="TCS",
            metric="eps",
            period="FY25Q1",
            forecast_value=34.1,
            unit="inr",
            kind="actual",
            source="company_earnings_release",
            collector="imei.fixtures.actuals",
            available_from="2024-07-11",
            confidence=0.95,
            evidence="TCS-Q1FY25-reported-EPS",
            revision_sequence=0,
        )
    )

    # ----- HDFCBANK -----
    seeds.append(
        _e(
            entity="HDFCBANK",
            metric="growth",
            period="FY25",
            forecast_value=15.0,
            unit="percent",
            kind="guidance",
            source="investor_presentation",
            collector="imei.fixtures.guidance",
            available_from="2024-04-20",
            confidence=0.85,
            evidence="HDFCBANK-investor-day-loan-growth-commentary",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="HDFCBANK",
            metric="growth",
            period="FY25",
            forecast_value=14.0,
            unit="percent",
            kind="guidance",
            source="company_guidance",
            collector="imei.fixtures.guidance",
            available_from="2024-07-20",
            confidence=0.85,
            evidence="HDFCBANK-Q1FY25-growth-commentary-revision",
            revision_sequence=1,
        )
    )
    seeds.append(
        _e(
            entity="HDFCBANK",
            metric="eps",
            period="FY25Q1",
            forecast_value=22.5,
            unit="inr",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-20",
            confidence=0.75,
            evidence="AGIB-forecast-HDFCBANK-FY25Q1-EPS",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="HDFCBANK",
            metric="eps",
            period="FY25Q1",
            forecast_value=21.8,
            unit="inr",
            kind="actual",
            source="company_earnings_release",
            collector="imei.fixtures.actuals",
            available_from="2024-07-20",
            confidence=0.95,
            evidence="HDFCBANK-Q1FY25-reported-EPS",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="HDFCBANK",
            metric="roe",
            period="FY25Q1",
            forecast_value=16.5,
            unit="percent",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-20",
            confidence=0.7,
            evidence="AGIB-forecast-HDFCBANK-FY25Q1-ROE",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="HDFCBANK",
            metric="roe",
            period="FY25Q1",
            forecast_value=16.0,
            unit="percent",
            kind="actual",
            source="company_earnings_release",
            collector="imei.fixtures.actuals",
            available_from="2024-07-20",
            confidence=0.9,
            evidence="HDFCBANK-Q1FY25-reported-ROE",
            revision_sequence=0,
        )
    )

    # ----- MARUTI -----
    seeds.append(
        _e(
            entity="MARUTI",
            metric="growth",
            period="FY25",
            forecast_value=10.0,
            unit="percent",
            kind="guidance",
            source="investor_presentation",
            collector="imei.fixtures.guidance",
            available_from="2024-05-10",
            confidence=0.8,
            evidence="MARUTI-volume-outlook-presentation",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="MARUTI",
            metric="revenue",
            period="FY25Q1",
            forecast_value=36000.0,
            unit="inr_cr",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-25",
            confidence=0.72,
            evidence="AGIB-forecast-MARUTI-FY25Q1-REV",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="MARUTI",
            metric="revenue",
            period="FY25Q1",
            forecast_value=37200.0,
            unit="inr_cr",
            kind="actual",
            source="company_earnings_release",
            collector="imei.fixtures.actuals",
            available_from="2024-07-31",
            confidence=0.95,
            evidence="MARUTI-Q1FY25-reported-revenue",
            revision_sequence=0,
        )
    )

    # ----- ULTRACEMCO (cement — alt-data link narrative) -----
    seeds.append(
        _e(
            entity="ULTRACEMCO",
            metric="growth",
            period="FY25",
            forecast_value=8.0,
            unit="percent",
            kind="guidance",
            source="investor_presentation",
            collector="imei.fixtures.guidance",
            available_from="2024-05-01",
            confidence=0.8,
            evidence="ULTRACEMCO-volume-growth-commentary",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="ULTRACEMCO",
            metric="growth",
            period="FY25",
            forecast_value=9.0,
            unit="percent",
            kind="guidance",
            source="company_guidance",
            collector="imei.fixtures.guidance",
            available_from="2024-08-01",
            confidence=0.8,
            evidence="ULTRACEMCO-guidance-upgrade-seed",
            revision_sequence=1,
        )
    )
    seeds.append(
        _e(
            entity="ULTRACEMCO",
            metric="ebitda",
            period="FY25Q1",
            forecast_value=2800.0,
            unit="inr_cr",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-20",
            confidence=0.7,
            evidence="AGIB-forecast-ULTRACEMCO-FY25Q1-EBITDA",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="ULTRACEMCO",
            metric="ebitda",
            period="FY25Q1",
            forecast_value=2950.0,
            unit="inr_cr",
            kind="actual",
            source="company_earnings_release",
            collector="imei.fixtures.actuals",
            available_from="2024-07-22",
            confidence=0.95,
            evidence="ULTRACEMCO-Q1FY25-reported-EBITDA",
            revision_sequence=0,
        )
    )

    # ----- NTPC (power / alt-data) -----
    seeds.append(
        _e(
            entity="NTPC",
            metric="growth",
            period="FY25",
            forecast_value=6.0,
            unit="percent",
            kind="guidance",
            source="investor_presentation",
            collector="imei.fixtures.guidance",
            available_from="2024-05-15",
            confidence=0.8,
            evidence="NTPC-generation-growth-commentary",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="NTPC",
            metric="eps",
            period="FY25Q1",
            forecast_value=4.5,
            unit="inr",
            kind="internal_forecast",
            source="agib_internal_forecast",
            collector="imei.fixtures.agib_forecast",
            available_from="2024-06-10",
            confidence=0.7,
            evidence="AGIB-forecast-NTPC-FY25Q1-EPS",
            revision_sequence=0,
        )
    )
    seeds.append(
        _e(
            entity="NTPC",
            metric="eps",
            period="FY25Q1",
            forecast_value=4.7,
            unit="inr",
            kind="actual",
            source="exchange_disclosure",
            collector="imei.fixtures.actuals",
            available_from="2024-07-27",
            confidence=0.95,
            evidence="NTPC-Q1FY25-exchange-filing-EPS",
            revision_sequence=0,
        )
    )

    # Explicit UNKNOWN licensed consensus placeholder (Phase 2 not configured)
    seeds.append(
        _e(
            entity="INFY",
            metric="eps",
            period="FY25",
            forecast_value=UNKNOWN,
            kind="licensed_consensus",
            source="licensed_consensus_feed",
            collector="imei.collectors.consensus_licensed",
            available_from="2024-01-01",
            confidence=0.0,
            evidence="phase_2_not_configured",
            notes="External consensus unavailable — marked UNKNOWN. Modular Phase-2 collector.",
            consensus={
                "median": UNKNOWN,
                "mean": UNKNOWN,
                "high": UNKNOWN,
                "low": UNKNOWN,
                "std_dev": UNKNOWN,
                "n_estimates": UNKNOWN,
                "basis": "licensed_feed_not_configured",
                "licensed_consensus": False,
            },
            revision_sequence=0,
        )
    )

    return seeds


def curated_narrative_seeds() -> list[dict[str, Any]]:
    """Structured market narratives — themes, not news summaries."""
    from knowledge_factory.market_expectations_intelligence.provenance import provenance
    from knowledge_factory.market_expectations_intelligence.schema import IMEI_VERSION

    themes = [
        {
            "narrative_id": "ai_spending",
            "name": "AI Spending",
            "description": "Enterprise AI / digital services demand cycle affecting IT services deal pipelines and margins.",
            "affected_industries": ["it_services"],
            "affected_companies": ["INFY", "TCS", "HCLTECH"],
            "macro_links": ["gdp", "fx"],
            "government_links": [],
            "alternative_data_links": [],
            "confidence": 0.8,
            "evolution": [
                {"date": "2023-01-01", "status": "emerging", "available_from": "2023-01-01"},
                {"date": "2024-01-01", "status": "strengthening", "available_from": "2024-01-01"},
            ],
            "evidence": "structured_theme_registry_ai",
        },
        {
            "narrative_id": "banking_credit_cycle",
            "name": "Banking Credit Cycle",
            "description": "Credit growth, deposit competition, and NIM trajectory for Indian banks/NBFCs.",
            "affected_industries": ["private_banks", "psu_banks", "nbfc"],
            "affected_companies": ["HDFCBANK", "ICICIBANK", "SBIN", "BAJFINANCE"],
            "macro_links": ["repo_rate", "credit", "liquidity"],
            "government_links": ["RBI"],
            "alternative_data_links": ["bank_credit_growth", "upi_transactions"],
            "confidence": 0.88,
            "evolution": [
                {"date": "2022-01-01", "status": "expanding", "available_from": "2022-01-01"},
                {"date": "2024-06-01", "status": "moderating", "available_from": "2024-06-01"},
            ],
            "evidence": "structured_theme_registry_credit",
        },
        {
            "narrative_id": "housing_recovery",
            "name": "Housing Recovery",
            "description": "Residential demand and housing finance transmission into construction materials.",
            "affected_industries": ["real_estate", "housing_finance", "cement"],
            "affected_companies": ["ULTRACEMCO", "DLF"],
            "macro_links": ["repo_rate", "credit"],
            "government_links": ["RBI"],
            "alternative_data_links": [],
            "confidence": 0.75,
            "evolution": [{"date": "2023-06-01", "status": "strengthening", "available_from": "2023-06-01"}],
            "evidence": "structured_theme_registry_housing",
        },
        {
            "narrative_id": "export_slowdown",
            "name": "Export Slowdown",
            "description": "Goods export softness and logistics volume implications.",
            "affected_industries": ["logistics", "textiles", "specialty_chem"],
            "affected_companies": ["ADANIPORTS", "CONCOR"],
            "macro_links": ["exports", "fx"],
            "government_links": ["Ministry of Commerce"],
            "alternative_data_links": ["port_cargo"],
            "confidence": 0.78,
            "evolution": [{"date": "2023-01-01", "status": "active", "available_from": "2023-01-01"}],
            "evidence": "structured_theme_registry_exports",
        },
        {
            "narrative_id": "manufacturing_boom",
            "name": "Manufacturing Boom",
            "description": "Domestic manufacturing / PLI-linked capacity and industrial activity theme.",
            "affected_industries": ["capital_goods", "electronics", "steel"],
            "affected_companies": ["LT", "SIEMENS", "DIXON", "TATASTEEL"],
            "macro_links": ["gdp", "industrial_activity"],
            "government_links": ["DPIIT", "PLI"],
            "alternative_data_links": ["iip_manufacturing", "electricity_demand"],
            "confidence": 0.82,
            "evolution": [{"date": "2022-01-01", "status": "strengthening", "available_from": "2022-01-01"}],
            "evidence": "structured_theme_registry_mfg",
        },
        {
            "narrative_id": "consumption_recovery",
            "name": "Consumption Recovery",
            "description": "Urban/rural consumption and discretionary demand recovery theme.",
            "affected_industries": ["fmcg", "retail", "passenger_vehicles"],
            "affected_companies": ["HINDUNILVR", "MARUTI", "DMART"],
            "macro_links": ["consumption"],
            "government_links": ["GST_COUNCIL"],
            "alternative_data_links": ["gst_collections", "vehicle_registrations", "upi_transactions"],
            "confidence": 0.8,
            "evolution": [
                {"date": "2023-01-01", "status": "uneven", "available_from": "2023-01-01"},
                {"date": "2024-01-01", "status": "improving", "available_from": "2024-01-01"},
            ],
            "evidence": "structured_theme_registry_consumption",
        },
        {
            "narrative_id": "electrification",
            "name": "Electrification",
            "description": "Power demand, renewables, and electrical equipment capex theme.",
            "affected_industries": ["power_generation", "renewables", "electrical_equipment"],
            "affected_companies": ["NTPC", "POWERGRID", "SIEMENS"],
            "macro_links": ["government_spending"],
            "government_links": ["Ministry of Power"],
            "alternative_data_links": ["electricity_demand"],
            "confidence": 0.85,
            "evolution": [{"date": "2022-01-01", "status": "strengthening", "available_from": "2022-01-01"}],
            "evidence": "structured_theme_registry_electrification",
        },
        {
            "narrative_id": "china_plus_one",
            "name": "China Plus One",
            "description": "Supply-chain diversification into India manufacturing and EMS.",
            "affected_industries": ["electronics", "specialty_chem", "autos"],
            "affected_companies": ["DIXON", "KAYNES"],
            "macro_links": ["trade"],
            "government_links": ["PLI", "DPIIT"],
            "alternative_data_links": ["iip_manufacturing"],
            "confidence": 0.8,
            "evolution": [{"date": "2021-01-01", "status": "active", "available_from": "2021-01-01"}],
            "evidence": "structured_theme_registry_cpo",
        },
        {
            "narrative_id": "capex_cycle",
            "name": "Capex Cycle",
            "description": "Public + private capex cycle through railways, infra, and capital goods.",
            "affected_industries": ["capital_goods", "engineering", "cement", "steel"],
            "affected_companies": ["LT", "ULTRACEMCO", "TATASTEEL", "SIEMENS"],
            "macro_links": ["government_spending", "gdp"],
            "government_links": ["MOF"],
            "alternative_data_links": ["railway_freight", "iip_manufacturing"],
            "confidence": 0.85,
            "evolution": [{"date": "2022-01-01", "status": "strengthening", "available_from": "2022-01-01"}],
            "evidence": "structured_theme_registry_capex",
        },
        {
            "narrative_id": "digitalisation",
            "name": "Digitalisation",
            "description": "UPI / digital payments deepening and fintech-bank distribution theme.",
            "affected_industries": ["private_banks", "nbfc", "consumer_internet"],
            "affected_companies": ["HDFCBANK", "PAYTM", "BAJFINANCE"],
            "macro_links": ["consumption", "liquidity"],
            "government_links": ["RBI", "NPCI"],
            "alternative_data_links": ["upi_transactions"],
            "confidence": 0.9,
            "evolution": [{"date": "2020-01-01", "status": "strengthening", "available_from": "2020-01-01"}],
            "evidence": "structured_theme_registry_digital",
        },
    ]
    out = []
    for t in themes:
        out.append(
            {
                **t,
                "provenance": provenance(
                    source="imei.narrative_registry",
                    collector="imei.fixtures.narratives",
                    confidence=float(t.get("confidence") or 0.8),
                    derived_from=[str(t.get("evidence"))],
                ),
                "version": IMEI_VERSION,
                "fabricated": False,
                "kind": "structured_theme",
                "not_news_summary": True,
            }
        )
    return out
