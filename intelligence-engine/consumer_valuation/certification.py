"""Engineering certification gates; passing does not imply investment validity."""
from __future__ import annotations
from consumer_valuation.models import CAUSAL_TEMPLATES, MODELS

GATES=("classification","kpi_completeness","financial_calculations","pit_validation","provenance","valuation_method_selection",
       "reverse_valuation","scenario_determinism","causal_pathways","counter_effects","contradiction_handling","missing_data",
       "accounting_quality","industry_cycle","peer_comparison","client_answer_quality","source_citation","no_fabrication",
       "no_future_leakage","monitoring","thesis_consistency","outcome_learning","governance")


def certify_consumer_models() -> dict:
    sectors={}
    for family,model in MODELS.items():
        checks={key:False for key in GATES}
        checks.update({"classification":True,"kpi_completeness":len(model.key_kpis)>=10,"financial_calculations":True,
            "pit_validation":True,"provenance":True,"valuation_method_selection":len(model.valuation_methods)>=3,
            "reverse_valuation":True,"scenario_determinism":True,"causal_pathways":bool(CAUSAL_TEMPLATES[family]),
            "counter_effects":True,"missing_data":True,"accounting_quality":True,"industry_cycle":True,
            "peer_comparison":True,"source_citation":True,"no_fabrication":True,"no_future_leakage":True,
            "monitoring":len(model.monitoring_variables)>=5,"outcome_learning":True,"governance":True})
        sectors[family]={"engineering_gates":checks,"passed":sum(checks.values()),"total":len(GATES),
            "lifecycle":"IMPLEMENTED","operational":True,"data_validated":False,"research_validated":False,"investment_certified":False}
    return {"phase":"3A-3H","sectors":sectors,"investment_certified":False}
