"""CRE investment-research benchmark: four gold questions per industry model."""
from __future__ import annotations
from industry_intelligence.dna_catalog import INDUSTRY_DNA
from institutional_evaluation_lab.datasets.models import question

CATEGORIES = (
    ("business_model", "What actually drives earnings in Indian {name}, and which KPIs prove it?"),
    ("causal_financial", "Why can margins change in Indian {name}, and how does that transmit to cash flow and returns?"),
    ("valuation_thesis", "What does valuation need to assume for an Indian {name} company, and what would invalidate the thesis?"),
    ("monitoring_risk", "What should an investor monitor next in Indian {name}, why does each indicator matter, and what is the trigger?"),
)

def build_cre_investment_144() -> list[dict]:
    rows = []
    for key, dna in sorted(INDUSTRY_DNA.items()):
        kpis = [x.name for x in dna.kpis[:4]]
        common = [*dna.revenue_drivers[:2], *dna.margin_drivers[:2], *kpis[:3]]
        for index, (category, template) in enumerate(CATEGORIES, 1):
            expected = list(dict.fromkeys(common + (
                dna.valuation_methods[:2] if category == "valuation_thesis" else
                dna.typical_risks[:2] if category == "monitoring_risk" else []
            )))
            rows.append(question(
                f"CRE-{key.upper()}-{index:02d}", text=template.format(name=dna.name),
                category="industry", intent=["Industry", "Analyse"],
                frameworks=["FW_INDUSTRY_STRUCTURE", "FW_KPI", "FW_SCENARIO"],
                expected_evidence=expected, expected_reasoning=[category, "causal", "decision relevance"],
                difficulty="hard", sector=key, concept_mode=True,
                must_not=["unsupported fact", "personalized recommendation", "future leakage"],
                tags=["cre_benchmark", category, key], answer_format="institutional_cre",
                suite="cre_investment_144", version="cre-benchmark-v1",
            ))
    return rows

CRE_INVESTMENT_144 = build_cre_investment_144()
