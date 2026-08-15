"""Concise client-safe Phase 2A answer assembly."""
from __future__ import annotations
from typing import Any


def format_technology_answer(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status")!="OPERATIONAL_NOT_CERTIFIED":
        return {"status":result.get("status") or "DATA_UNAVAILABLE","answer":"AGI cannot form a reliable IT-services valuation view from the available point-in-time evidence.","limitations":result.get("input_issues") or result.get("risk_flags") or ["Evidence gates did not pass."],"execution_eligible":False}
    if (result.get("model") or {}).get("subsector")=="SOFTWARE_SAAS":
        return _format_software_saas_answer(result)
    if (result.get("model") or {}).get("subsector")=="INTERNET_PLATFORMS_MARKETPLACES":
        return _format_platform_answer(result)
    if (result.get("model") or {}).get("subsector")=="CONSUMER_INTERNET_DIGITAL_COMMERCE":
        return _format_consumer_answer(result)
    if (result.get("model") or {}).get("subsector")=="SEMICONDUCTOR_RELATED":
        return _format_semiconductor_answer(result)
    if (result.get("model") or {}).get("subsector")=="TELECOM":
        return _format_telecom_answer(result)
    if (result.get("model") or {}).get("subsector")=="TELECOM_INFRASTRUCTURE_TOWERS":
        return _format_tower_answer(result)
    company=result.get("company_id") or "The company"; valuation=result["valuation"]; expectations=result["market_expectations"]; kpis=result["kpis"]
    expectation_text={"EXPECTATIONS_STRETCHED":"the market requires stronger growth than AGI's base expectation","EXPECTATIONS_FAVORABLE":"the market embeds less growth than AGI's base expectation","EXPECTATIONS_NEUTRAL":"market-implied growth is broadly aligned with AGI's base expectation"}.get(expectations.get("classification"),"market expectations cannot yet be resolved")
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} trades at {valuation['current_pe']:.2f}x normalized earnings and {valuation['ev_ebitda']:.2f}x EBITDA; {expectation_text}.",
        "business_quality":"IT-services value depends on durable client demand, execution, pricing, utilization and cash conversion rather than the headline multiple alone.",
        "growth":f"Book-to-bill is {kpis['book_to_bill']:.2f}x; signed contract value must still convert into reported revenue.",
        "margin_economics":f"EBIT margin is {kpis['ebit_margin']:.1%}. Utilization, billing rates, wages, attrition, delivery mix and AI sharing determine its durability.",
        "cash_flow":f"FCF margin is {kpis['fcf_margin']:.1%}.","valuation":valuation,"market_implied_expectations":expectations,
        "scenarios":result.get("scenarios"),"key_risks":result.get("model",{}).get("valuation_risks") or [],
        "ai_impact":result.get("business_economics",{}).get("ai_analysis"),"what_to_monitor":result.get("monitoring") or [],
        "confidence":result.get("confidence"),"as_of":result.get("as_of"),"sources":sorted({v.get("source_id") for v in (result.get("provenance") or {}).values() if v.get("source_id")}),
        "limitations":"Operational research curriculum, not investment-certified or personalized advice.","execution_eligible":False}


def _format_software_saas_answer(result:dict[str,Any])->dict[str,Any]:
    company=result.get("company_id") or "The company"; valuation=result["valuation"]; k=result["kpis"]; expectations=result["market_expectations"]
    expectation_text={"EXPECTATIONS_STRETCHED":"the quoted value requires stronger ARR growth than AGI's base expectation","EXPECTATIONS_FAVORABLE":"the quoted value embeds less ARR growth than AGI's base expectation","EXPECTATIONS_NEUTRAL":"market-implied ARR growth is broadly aligned with AGI's base expectation"}.get(expectations.get("classification"),"market expectations remain unresolved")
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} is valued at {valuation['current_ev_arr']:.2f}x ARR and {valuation['ev_gross_profit']:.2f}x gross profit; {expectation_text}.",
        "business_quality":"Recurring revenue quality depends on contract terms, retention, customer concentration and pricing power; recurring, contracted and committed revenue are not interchangeable.",
        "growth":f"ARR growth is {k['arr_growth']:.1%}, with NRR of {k['nrr']:.1%} and GRR of {k['grr']:.1%}.",
        "unit_economics":f"CAC payback is {k['cac_payback_months']:.1f} months and LTV/CAC is {k['ltv_cac']:.2f}x.",
        "cash_flow":f"FCF margin is {k['fcf_margin']:.1%}; Rule of 40 is {k['rule_of_40']:.1%} and is context, not fair value.",
        "valuation":valuation,"market_implied_expectations":expectations,"scenarios":result.get("scenarios"),
        "key_risks":result.get("model",{}).get("valuation_risks") or [],"ai_impact":result.get("business_economics",{}).get("ai_analysis"),
        "what_to_monitor":result.get("monitoring") or [],"confidence":result.get("confidence"),"as_of":result.get("as_of"),
        "sources":sorted({v.get("source_id") for v in (result.get("provenance") or {}).values() if v.get("source_id")}),
        "limitations":"Operational research curriculum, not investment-certified or personalized advice.","execution_eligible":False}


def _format_platform_answer(result:dict[str,Any])->dict[str,Any]:
    company=result.get("company_id") or "The company"; v=result["valuation"]; k=result["kpis"]
    expectation={"EXPECTATIONS_STRETCHED":"the valuation requires stronger growth than AGI's base case","EXPECTATIONS_FAVORABLE":"the valuation embeds less growth than AGI's base case","EXPECTATIONS_NEUTRAL":"market-implied growth broadly matches AGI's base case"}.get(result["market_expectations"].get("classification"),"market expectations remain unresolved")
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} trades at {v['current_ev_sales']:.2f}x revenue and {v['ev_gmv']:.2f}x GMV; {expectation}.",
        "business_quality":"A defensible platform requires repeat transactions, balanced buyer-seller liquidity and trust. User growth alone is not evidence of a network effect.",
        "growth":f"GMV growth is {k['gmv_growth']:.1%}, take rate is {k['take_rate']:.1%}, and order frequency is {k['order_frequency']:.2f} per active buyer.",
        "unit_economics":f"Contribution margin is {k['contribution_margin']:.1%}; customer acquisition cost is {k['cac']:.2f} in the reported currency.",
        "cash_flow":f"FCF margin is {k['fcf_margin']:.1%}.","valuation":v,"market_implied_expectations":result.get("market_expectations"),"scenarios":result.get("scenarios"),
        "key_risks":result.get("model",{}).get("valuation_risks") or [],"ai_impact":result.get("business_economics",{}).get("ai_analysis"),"what_to_monitor":result.get("monitoring") or [],
        "confidence":result.get("confidence"),"as_of":result.get("as_of"),"sources":sorted({x.get("source_id") for x in (result.get("provenance") or {}).values() if x.get("source_id")}),
        "limitations":"Operational research curriculum, not investment-certified or personalized advice.","execution_eligible":False}


def _format_consumer_answer(result:dict[str,Any])->dict[str,Any]:
    company=result.get("company_id") or "The company"; v=result["valuation"]; k=result["kpis"]
    expectation={"EXPECTATIONS_STRETCHED":"the valuation requires stronger growth than AGI's base case","EXPECTATIONS_FAVORABLE":"the valuation embeds less growth than AGI's base case","EXPECTATIONS_NEUTRAL":"market-implied growth broadly matches AGI's base case"}.get(result["market_expectations"].get("classification"),"market expectations remain unresolved")
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} trades at {v['current_ev_sales']:.2f}x net revenue and {v['ev_gross_profit']:.2f}x gross profit; {expectation}.","business_quality":"Consumer digital quality depends on retained customers, repeat purchases and contribution economics. Downloads, GMV and subsidized orders are not recognized revenue or proof of loyalty.","growth":f"Net revenue growth is {k['revenue_growth']:.1%}, order frequency is {k['order_frequency']:.2f}, and repeat rate is {k['repeat_rate']:.1%}.","unit_economics":f"Gross margin is {k['gross_margin']:.1%}, contribution margin is {k['contribution_margin']:.1%}, and CAC is {k['cac']:.2f} in the reported currency.","operations":f"Return rate is {k['return_rate']:.1%} and inventory turns are {k['inventory_turns']:.2f}x.","cash_flow":f"FCF margin is {k['fcf_margin']:.1%}.","valuation":v,"market_implied_expectations":result.get("market_expectations"),"scenarios":result.get("scenarios"),"key_risks":result.get("model",{}).get("valuation_risks") or [],"ai_impact":result.get("business_economics",{}).get("ai_analysis"),"what_to_monitor":result.get("monitoring") or [],"confidence":result.get("confidence"),"as_of":result.get("as_of"),"sources":sorted({x.get("source_id") for x in (result.get("provenance") or {}).values() if x.get("source_id")}),"limitations":"Operational research curriculum, not investment-certified or personalized advice.","execution_eligible":False}


def _format_semiconductor_answer(result:dict[str,Any])->dict[str,Any]:
    company=result.get("company_id") or "The company";v=result["valuation"];k=result["kpis"]
    expectation={"EXPECTATIONS_STRETCHED":"the valuation requires stronger growth than AGI's base case","EXPECTATIONS_FAVORABLE":"the valuation embeds less growth than AGI's base case","EXPECTATIONS_NEUTRAL":"market-implied growth broadly matches AGI's base case"}.get(result["market_expectations"].get("classification"),"market expectations remain unresolved")
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} trades at {v['current_ev_ebitda']:.2f}x EBITDA and {v['ev_sales']:.2f}x revenue; {expectation}.","business_quality":"Semiconductor value depends on the operating model, design wins, qualified capacity, utilization, yield and cycle-normalized cash returns. Announced capacity is not saleable output.","cycle":f"Revenue growth is {k['revenue_growth']:.1%}, book-to-bill is {k['book_to_bill']:.2f}x, and inventory turns are {k['inventory_turns']:.2f}x.","manufacturing":f"Utilization is {k['utilization']:.1%}, yield is {k['yield_rate']:.1%}, and gross margin is {k['gross_margin']:.1%}.","reinvestment":f"R&D intensity is {k['rnd_intensity']:.1%}, capex intensity is {k['capex_intensity']:.1%}, and FCF margin is {k['fcf_margin']:.1%}.","valuation":v,"market_implied_expectations":result.get("market_expectations"),"scenarios":result.get("scenarios"),"key_risks":result.get("model",{}).get("valuation_risks") or [],"ai_impact":result.get("business_economics",{}).get("ai_analysis"),"what_to_monitor":result.get("monitoring") or [],"confidence":result.get("confidence"),"as_of":result.get("as_of"),"sources":sorted({x.get("source_id") for x in (result.get("provenance") or {}).values() if x.get("source_id")}),"limitations":"Cycle-normalized operational research, not investment-certified or personalized advice.","execution_eligible":False}


def _format_telecom_answer(result:dict[str,Any])->dict[str,Any]:
    company=result.get("company_id") or "The company";v=result["valuation"];k=result["kpis"]
    expectation={"EXPECTATIONS_STRETCHED":"the valuation requires stronger EBITDA growth than AGI's base case","EXPECTATIONS_FAVORABLE":"the valuation embeds less growth than AGI's base case","EXPECTATIONS_NEUTRAL":"market-implied growth broadly matches AGI's base case"}.get(result["market_expectations"].get("classification"),"market expectations remain unresolved")
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} trades at {v['current_ev_ebitda']:.2f}x EBITDA and {v['ev_per_subscriber']:.2f} enterprise value per subscriber; {expectation}.","operating_view":f"ARPU is {k['arpu']:.2f}, subscriber growth is {k['subscriber_growth']:.1%}, churn is {k['churn']:.1%}, and EBITDA margin is {k['ebitda_margin']:.1%}.","cash_and_leverage":f"Capex intensity is {k['capex_intensity']:.1%}, net debt including spectrum is {k['net_debt_ebitda']:.2f}x EBITDA, interest coverage is {k['interest_coverage']:.2f}x, and FCF margin is {k['fcf_margin']:.1%}.","tariff_view":"Tariff upside is scenario-dependent: AGI deducts churn/down-trading risk, realization, incremental costs, spectrum liabilities and debt before estimating equity value.","valuation":v,"market_implied_expectations":result.get("market_expectations"),"scenarios":result.get("scenarios"),"key_risks":result.get("model",{}).get("valuation_risks") or [],"ai_impact":result.get("business_economics",{}).get("ai_analysis"),"what_to_monitor":result.get("monitoring") or [],"confidence":result.get("confidence"),"as_of":result.get("as_of"),"sources":sorted({x.get("source_id") for x in (result.get("provenance") or {}).values() if x.get("source_id")}),"limitations":"Operational telecom research, not investment-certified or personalized advice.","execution_eligible":False}


def _format_tower_answer(result:dict[str,Any])->dict[str,Any]:
    company=result.get("company_id") or "The company";v=result["valuation"];k=result["kpis"]
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} trades at {v['current_ev_ebitda']:.2f}x EBITDA and {v['ev_per_site']:.2f} enterprise value per active site.","operating_view":f"Tenancy is {k['tenancy_ratio']:.2f}x, rental revenue per tenant is {k['revenue_per_tenant']:.2f}, and net tenant additions are {k['tenant_additions']:.2f}.","contract_quality":f"Weighted contract duration is {k['contract_duration']:.1f} years, customer concentration is {k['customer_concentration']:.1%}, and energy pass-through coverage is {k['energy_coverage']:.2f}x.","cash_and_leverage":f"EBITDA margin is {k['ebitda_margin']:.1%}, capex intensity is {k['capex_intensity']:.1%}, leverage is {k['net_debt_ebitda']:.2f}x, and FCF margin is {k['fcf_margin']:.1%}.","valuation":v,"market_implied_expectations":result.get("market_expectations"),"scenarios":result.get("scenarios"),"key_risks":result.get("model",{}).get("valuation_risks") or [],"what_to_monitor":result.get("monitoring") or [],"confidence":result.get("confidence"),"as_of":result.get("as_of"),"sources":sorted({x.get("source_id") for x in (result.get("provenance") or {}).values() if x.get("source_id")}),"limitations":"Operational tower research, not investment-certified or personalized advice.","execution_eligible":False}
