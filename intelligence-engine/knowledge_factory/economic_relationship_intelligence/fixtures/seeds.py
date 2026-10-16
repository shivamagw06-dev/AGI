"""Curated evidence-backed economic relationship seeds.

Never invent. Only high-confidence public / soft-prior relationships.
Unknown relationships are omitted (not fabricated).
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence.relationship_objects.builder import (
    build_relationship,
)


def _r(**kwargs: Any) -> dict[str, Any]:
    return build_relationship(**kwargs)


def curated_relationship_seeds() -> list[dict[str, Any]]:
    """Return immutable relationship objects (not yet validated)."""
    seeds: list[dict[str, Any]] = []

    # ----- Commodity exposures / sensitivities (oil) -----
    for industry, strength, conf, shock in (
        ("airlines", "high", 0.9, "cost_up_when_oil_up"),
        ("paint", "high", 0.85, "cost_up_when_oil_up"),
        ("tyres", "high", 0.85, "cost_up_when_oil_up"),
        ("petrochemicals", "high", 0.88, "mixed_integrated"),
        ("logistics", "moderate", 0.8, "cost_up_when_oil_up"),
        ("packaging", "moderate", 0.75, "cost_up_when_oil_up"),
        ("fmcg", "moderate", 0.7, "cost_up_when_oil_up"),
        ("retail", "low", 0.65, "demand_second_order"),
    ):
        seeds.append(
            _r(
                source_kind="commodity",
                source_id="crude_oil",
                target_kind="industry",
                target_id=industry,
                relationship_type="oil_sensitivity",
                direction="affects",
                strength=strength,
                confidence=conf,
                evidence="sector_dna_oil_sensitivity_public",
                source="official_commodity_data",
                collector="ieri.fixtures.oil",
                available_from="2015-01-01",
                semantics="market",
                shock_direction=shock,
                time_horizon="short_to_medium",
                transmission_order=1,
            )
        )

    # Oil ↑ beneficiaries (producers / integrated)
    for co, conf in (("ONGC", 0.9), ("OIL", 0.85), ("RELIANCE", 0.8)):
        seeds.append(
            _r(
                source_kind="commodity",
                source_id="crude_oil",
                target_kind="company",
                target_id=co,
                relationship_type="commodity_exposure",
                direction="affects",
                strength="high",
                confidence=conf,
                evidence="producer_or_integrated_refiner_disclosures",
                source="annual_reports",
                collector="ieri.fixtures.oil_producers",
                available_from="2015-01-01",
                semantics="market",
                shock_direction="benefit_when_oil_up",
                notes="Upstream / integrated crude exposure — structured knowledge not a forecast.",
            )
        )

    # Oil ↑ losers (cost)
    for co, conf in (("INDIGO", 0.9), ("ASIANPAINT", 0.85), ("APOLLOTYRE", 0.85)):
        seeds.append(
            _r(
                source_kind="commodity",
                source_id="crude_oil",
                target_kind="company",
                target_id=co,
                relationship_type="oil_sensitivity",
                direction="affects",
                strength="high",
                confidence=conf,
                evidence="fuel_or_feedstock_cost_disclosures",
                source="annual_reports",
                collector="ieri.fixtures.oil_users",
                available_from="2016-01-01",
                semantics="market",
                shock_direction="hurt_when_oil_up",
            )
        )

    # Oil transmission chain (1→2→3)
    oil_chain = [
        ("crude_oil", "commodity", "paint", "industry", 1),
        ("paint", "industry", "consumer_goods", "industry", 2),
        ("crude_oil", "commodity", "tyres", "industry", 1),
        ("tyres", "industry", "passenger_vehicles", "industry", 2),
        ("crude_oil", "commodity", "airlines", "industry", 1),
        ("airlines", "industry", "logistics", "industry", 2),
        ("logistics", "industry", "retail", "industry", 3),
        ("crude_oil", "commodity", "petrochemicals", "industry", 1),
        ("petrochemicals", "industry", "packaging", "industry", 2),
        ("packaging", "industry", "fmcg", "industry", 3),
        ("fmcg", "industry", "retail", "industry", 3),
    ]
    for src, sk, tgt, tk, order in oil_chain:
        seeds.append(
            _r(
                source_kind=sk,
                source_id=src,
                target_kind=tk,
                target_id=tgt,
                relationship_type="transmission",
                direction="affects",
                strength="moderate" if order > 1 else "high",
                confidence=max(0.65, 0.9 - 0.1 * (order - 1)),
                evidence="economic_transmission_seed_oil",
                source="industry_associations",
                collector="ieri.fixtures.transmission_oil",
                available_from="2015-01-01",
                semantics="market",
                transmission_order=order,
                time_horizon="medium",
                shock_direction="oil_up_cost_pressure",
            )
        )

    # ----- Steel -----
    for industry, order in (
        ("passenger_vehicles", 1),
        ("construction", 1),
        ("capital_goods", 1),
        ("engineering", 2),
        ("infra", 1),
    ):
        seeds.append(
            _r(
                source_kind="commodity",
                source_id="steel",
                target_kind="industry",
                target_id=industry,
                relationship_type="steel_sensitivity",
                direction="affects",
                strength="high" if order == 1 else "moderate",
                confidence=0.85 if order == 1 else 0.75,
                evidence="steel_iivi_downstream_demand",
                source="industry_associations",
                collector="ieri.fixtures.steel",
                available_from="2015-01-01",
                semantics="market",
                transmission_order=order,
                shock_direction="benefit_when_steel_price_down",
            )
        )
    seeds.append(
        _r(
            source_kind="company",
            source_id="TATASTEEL",
            target_kind="industry",
            target_id="passenger_vehicles",
            relationship_type="supplier",
            direction="outbound",
            strength="high",
            confidence=0.85,
            evidence="steel_auto_supply_chain_public",
            source="industry_associations",
            collector="ieri.fixtures.tatasteel",
            available_from="2015-01-01",
            semantics="structural",
        )
    )
    seeds.append(
        _r(
            source_kind="company",
            source_id="TATASTEEL",
            target_kind="industry",
            target_id="construction",
            relationship_type="supplier",
            direction="outbound",
            strength="high",
            confidence=0.85,
            evidence="steel_construction_demand_public",
            source="industry_associations",
            collector="ieri.fixtures.tatasteel",
            available_from="2015-01-01",
            semantics="structural",
        )
    )
    seeds.append(
        _r(
            source_kind="commodity",
            source_id="iron_ore",
            target_kind="industry",
            target_id="steel",
            relationship_type="commodity_exposure",
            direction="affects",
            strength="high",
            confidence=0.9,
            evidence="steel_iivi_supply_chain",
            source="industry_associations",
            collector="ieri.fixtures.iron_ore",
            available_from="2015-01-01",
            semantics="market",
        )
    )

    # ----- Copper / semiconductors import dependency -----
    seeds.append(
        _r(
            source_kind="commodity",
            source_id="copper",
            target_kind="industry",
            target_id="electrical_equipment",
            relationship_type="import_dependency",
            direction="affects",
            strength="high",
            confidence=0.85,
            evidence="india_copper_import_dependence",
            source="public_trade_statistics",
            collector="ieri.fixtures.copper",
            available_from="2016-01-01",
            semantics="market",
        )
    )
    for co in ("DIXON", "KAYNES", "SYRMA"):
        seeds.append(
            _r(
                source_kind="company",
                source_id=co,
                target_kind="commodity",
                target_id="semiconductors",
                relationship_type="import_dependency",
                direction="outbound",
                strength="high",
                confidence=0.88,
                evidence="semiconductor_import_dependence_electronics_ems",
                source="ministry_reports",
                collector="ieri.fixtures.semiconductors",
                available_from="2020-01-01",
                semantics="market",
            )
        )

    # ----- Dixon Technologies company network -----
    for supplier, conf in (("KAYNES", 0.7), ("SYRMA", 0.7)):
        seeds.append(
            _r(
                source_kind="company",
                source_id=supplier,
                target_kind="company",
                target_id="DIXON",
                relationship_type="competitor",
                direction="bidirectional",
                strength="moderate",
                confidence=conf,
                evidence="ems_peer_set_public",
                source="investor_presentations",
                collector="ieri.fixtures.dixon_peers",
                available_from="2021-01-01",
                semantics="structural",
            )
        )
    seeds.append(
        _r(
            source_kind="industry",
            source_id="electronics",
            target_kind="company",
            target_id="DIXON",
            relationship_type="supporting_industry",
            direction="affects",
            strength="high",
            confidence=0.9,
            evidence="company_industry_map_iivi",
            source="industry_associations",
            collector="ieri.fixtures.dixon_industry",
            available_from="2020-01-01",
            semantics="structural",
        )
    )
    # PLI → DIXON is seeded once in the PLI company beneficiary loop below.

    # ----- Macro: Repo rate chain -----
    repo_chain = [
        ("repo_rate", "macro", "private_banks", "industry", 1, "interest_rate_sensitivity"),
        ("repo_rate", "macro", "psu_banks", "industry", 1, "interest_rate_sensitivity"),
        ("repo_rate", "macro", "nbfc", "industry", 1, "interest_rate_sensitivity"),
        ("private_banks", "industry", "housing_finance", "industry", 2, "credit_dependency"),
        ("nbfc", "industry", "housing_finance", "industry", 2, "credit_dependency"),
        ("housing_finance", "industry", "real_estate", "industry", 2, "credit_dependency"),
        ("real_estate", "industry", "construction", "industry", 3, "downstream_industry"),
        ("construction", "industry", "cement", "industry", 3, "downstream_industry"),
        ("cement", "industry", "building_materials", "industry", 3, "downstream_industry"),
        ("housing_finance", "industry", "consumer_durables", "industry", 3, "complementary_industry"),
    ]
    for src, sk, tgt, tk, order, rtype in repo_chain:
        seeds.append(
            _r(
                source_kind=sk,
                source_id=src,
                target_kind=tk,
                target_id=tgt,
                relationship_type=rtype,
                direction="affects",
                strength="high" if order == 1 else "moderate",
                confidence=max(0.7, 0.9 - 0.08 * (order - 1)),
                evidence="rbi_monetary_transmission_public",
                source="rbi",
                collector="ieri.fixtures.repo_chain",
                available_from="2016-01-01",
                semantics="market" if "sensitivity" in rtype or rtype == "credit_dependency" else "structural",
                transmission_order=order,
                time_horizon="medium",
                shock_direction="repo_cut_eases_credit",
            )
        )
    for co in ("HDFCBANK", "ICICIBANK", "SBIN", "BAJFINANCE"):
        seeds.append(
            _r(
                source_kind="macro",
                source_id="repo_rate",
                target_kind="company",
                target_id=co,
                relationship_type="interest_rate_sensitivity",
                direction="affects",
                strength="high",
                confidence=0.88,
                evidence="rbi_banking_nbfc_rate_sensitivity",
                source="rbi",
                collector="ieri.fixtures.repo_companies",
                available_from="2016-01-01",
                semantics="market",
                transmission_order=1,
            )
        )

    # ----- Macro: Inflation / FX / GDP (selected) -----
    for macro, industry, rtype, sem in (
        ("inflation", "fmcg", "inflation_sensitivity", "market"),
        ("inflation", "private_banks", "inflation_sensitivity", "market"),
        ("fx", "it_services", "fx_sensitivity", "market"),
        ("fx", "pharma", "fx_sensitivity", "market"),
        ("gdp", "cement", "commodity_exposure", "market"),
        ("gdp", "passenger_vehicles", "commodity_exposure", "market"),
        ("credit", "nbfc", "credit_dependency", "financial"),
        ("liquidity", "private_banks", "interest_rate_sensitivity", "market"),
        ("consumption", "retail", "commodity_exposure", "market"),
        ("government_spending", "capital_goods", "government_dependency", "policy"),
    ):
        seeds.append(
            _r(
                source_kind="macro",
                source_id=macro,
                target_kind="industry",
                target_id=industry,
                relationship_type=rtype,
                direction="affects",
                strength="moderate",
                confidence=0.8,
                evidence=f"macro_{macro}_industry_link_public",
                source="rbi",
                collector="ieri.fixtures.macro",
                available_from="2016-01-01",
                semantics=sem,
                transmission_order=1,
            )
        )

    # ----- Government / policy -----
    for industry, order in (
        ("electronics", 1),
        ("consumer_durables", 1),
        ("auto_electronics", 2),
        ("semiconductor_ecosystem", 1),
        ("ems", 1),
    ):
        seeds.append(
            _r(
                source_kind="policy",
                source_id="PLI-ELECTRONICS",
                target_kind="industry",
                target_id=industry,
                relationship_type="policy_dependency",
                direction="affects",
                strength="high" if order == 1 else "moderate",
                confidence=0.85 if order == 1 else 0.75,
                evidence="pli_scheme_notifications",
                source="government_publications",
                collector="ieri.fixtures.pli",
                available_from="2020-04-01",
                semantics="policy",
                transmission_order=order,
                shock_direction="incentive_expansion_benefits",
            )
        )
    # PLI second / third order company beneficiaries
    for co, order in (("DIXON", 1), ("KAYNES", 1), ("SYRMA", 1), ("HAVELLS", 2), ("POLYCAB", 3)):
        seeds.append(
            _r(
                source_kind="policy",
                source_id="PLI-ELECTRONICS",
                target_kind="company",
                target_id=co,
                relationship_type="policy_dependency",
                direction="affects",
                strength="high" if order == 1 else "moderate",
                confidence=max(0.7, 0.9 - 0.08 * (order - 1)),
                evidence="pli_electronics_listed_beneficiaries_public",
                source="government_publications",
                collector="ieri.fixtures.pli_companies",
                available_from="2020-04-01",
                semantics="policy",
                transmission_order=order,
            )
        )

    # Budget / railway capex chain
    for src, sk, tgt, tk, order in (
        ("BUDGET-CAPEX", "policy", "railways", "industry", 1),
        ("railways", "industry", "capital_goods", "industry", 2),
        ("capital_goods", "industry", "engineering", "industry", 2),
        ("railways", "industry", "cement", "industry", 3),
        ("railways", "industry", "steel", "industry", 3),
    ):
        seeds.append(
            _r(
                source_kind=sk,
                source_id=src,
                target_kind=tk,
                target_id=tgt,
                relationship_type="government_dependency" if sk == "policy" else "downstream_industry",
                direction="affects",
                strength="high" if order == 1 else "moderate",
                confidence=0.85 if order <= 2 else 0.75,
                evidence="union_budget_railway_capex_public",
                source="government_publications",
                collector="ieri.fixtures.budget_rail",
                available_from="2018-01-01",
                semantics="policy" if sk == "policy" else "structural",
                transmission_order=order,
                shock_direction="higher_railway_capex_benefits",
            )
        )
    for co in ("LT", "SIEMENS", "ULTRACEMCO", "TATASTEEL"):
        seeds.append(
            _r(
                source_kind="policy",
                source_id="BUDGET-CAPEX",
                target_kind="company",
                target_id=co,
                relationship_type="government_dependency",
                direction="affects",
                strength="moderate",
                confidence=0.8,
                evidence="infra_capex_beneficiary_sectors_public",
                source="government_publications",
                collector="ieri.fixtures.budget_cos",
                available_from="2018-01-01",
                semantics="policy",
                transmission_order=2 if co in ("LT", "SIEMENS") else 3,
            )
        )

    # GST → consumption → retail → autos
    for src, sk, tgt, tk, order in (
        ("GST", "policy", "consumption", "macro", 1),
        ("consumption", "macro", "retail", "industry", 2),
        ("retail", "industry", "passenger_vehicles", "industry", 3),
        ("GST", "policy", "fmcg", "industry", 2),
    ):
        seeds.append(
            _r(
                source_kind=sk,
                source_id=src,
                target_kind=tk,
                target_id=tgt,
                relationship_type="policy_dependency" if sk == "policy" else "downstream_industry",
                direction="affects",
                strength="moderate",
                confidence=0.8,
                evidence="gst_consumption_channel_public",
                source="government_publications",
                collector="ieri.fixtures.gst",
                available_from="2017-07-01",
                semantics="policy" if sk == "policy" else "structural",
                transmission_order=order,
            )
        )

    # Trade / import duty
    seeds.append(
        _r(
            source_kind="policy",
            source_id="IMPORT-DUTY",
            target_kind="industry",
            target_id="electronics",
            relationship_type="policy_dependency",
            direction="affects",
            strength="high",
            confidence=0.85,
            evidence="customs_duty_electronics_public",
            source="government_publications",
            collector="ieri.fixtures.trade",
            available_from="2018-01-01",
            semantics="policy",
        )
    )
    seeds.append(
        _r(
            source_kind="policy",
            source_id="TRADE-POLICY",
            target_kind="industry",
            target_id="logistics",
            relationship_type="logistics_dependency",
            direction="affects",
            strength="moderate",
            confidence=0.8,
            evidence="trade_ports_shipping_logistics",
            source="ministry_reports",
            collector="ieri.fixtures.trade",
            available_from="2016-01-01",
            semantics="operational",
        )
    )
    seeds.append(
        _r(
            source_kind="policy",
            source_id="TRADE-POLICY",
            target_kind="port",
            target_id="major_ports",
            relationship_type="transport_dependency",
            direction="affects",
            strength="high",
            confidence=0.85,
            evidence="trade_policy_ports",
            source="ministry_reports",
            collector="ieri.fixtures.trade",
            available_from="2016-01-01",
            semantics="operational",
        )
    )

    # ----- Industry structural links -----
    industry_links = [
        ("iron_ore_mining", "steel", "upstream_industry"),
        ("steel", "passenger_vehicles", "downstream_industry"),
        ("steel", "construction", "downstream_industry"),
        ("cement", "construction", "downstream_industry"),
        ("private_banks", "nbfc", "complementary_industry"),
        ("nbfc", "housing_finance", "supporting_industry"),
        ("it_services", "bfsi", "customer"),
        ("electronics", "consumer_durables", "complementary_industry"),
        ("power", "aluminium", "supporting_industry"),
        ("logistics", "retail", "supporting_industry"),
    ]
    for src, tgt, rtype in industry_links:
        seeds.append(
            _r(
                source_kind="industry",
                source_id=src,
                target_kind="industry",
                target_id=tgt,
                relationship_type=rtype,
                direction="outbound",
                strength="moderate",
                confidence=0.8,
                evidence="iivi_value_chain_soft_prior",
                source="industry_associations",
                collector="ieri.fixtures.industry_links",
                available_from="2016-01-01",
                semantics="behavioural" if "complement" in rtype or "substitute" in rtype else "structural",
            )
        )

    # ----- Known competitors (structural) -----
    competitor_pairs = [
        ("INFY", "TCS"),
        ("INFY", "HCLTECH"),
        ("TCS", "WIPRO"),
        ("HDFCBANK", "ICICIBANK"),
        ("HDFCBANK", "KOTAKBANK"),
        ("ULTRACEMCO", "AMBUJACEM"),
        ("TATASTEEL", "JSWSTEEL"),
        ("ASIANPAINT", "BERGEPAINT"),
        ("MARUTI", "M&M"),
        ("HINDUNILVR", "NESTLEIND"),
    ]
    for a, b in competitor_pairs:
        seeds.append(
            _r(
                source_kind="company",
                source_id=a,
                target_kind="company",
                target_id=b,
                relationship_type="competitor",
                direction="bidirectional",
                strength="high",
                confidence=0.9,
                evidence="listed_peer_set_public",
                source="investor_presentations",
                collector="ieri.fixtures.competitors",
                available_from="2018-01-01",
                semantics="structural",
            )
        )

    # ----- Operational dependencies -----
    for industry in ("aluminium", "cement", "steel"):
        seeds.append(
            _r(
                source_kind="industry",
                source_id=industry,
                target_kind="commodity",
                target_id="electricity",
                relationship_type="power_dependency",
                direction="outbound",
                strength="high",
                confidence=0.9,
                evidence="industrial_power_cost_public",
                source="ministry_reports",
                collector="ieri.fixtures.power",
                available_from="2015-01-01",
                semantics="operational",
            )
        )
    seeds.append(
        _r(
            source_kind="industry",
            source_id="steel",
            target_kind="railway",
            target_id="indian_railways",
            relationship_type="transport_dependency",
            direction="outbound",
            strength="moderate",
            confidence=0.8,
            evidence="bulk_commodity_rail_logistics",
            source="ministry_reports",
            collector="ieri.fixtures.rail",
            available_from="2015-01-01",
            semantics="operational",
        )
    )

    # Bank relationships (credit dependency for rate-sensitive cos — selected)
    for bank, co in (("HDFCBANK", "BAJFINANCE"), ("SBIN", "LT")):
        seeds.append(
            _r(
                source_kind="bank",
                source_id=bank,
                target_kind="company",
                target_id=co,
                relationship_type="credit_dependency",
                direction="affects",
                strength="moderate",
                confidence=0.7,
                evidence="systemic_credit_channel_public",
                source="rbi",
                collector="ieri.fixtures.banking",
                available_from="2018-01-01",
                semantics="financial",
                notes="Systemic credit-channel link — not a specific loan disclosure.",
            )
        )

    return seeds
