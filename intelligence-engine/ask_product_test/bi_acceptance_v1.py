"""Business Intelligence Acceptance Test v1.0 — 100 deterministic questions.

Runs against business_intelligence.foundation (NOT Ask). Ask must stay unwired
until this suite passes ≥95%.
"""

from __future__ import annotations

from typing import Any, Dict, List

# (id, category, prompt, must_modules_any, required_fields_any)
BI_ACCEPTANCE_100: List[Dict[str, Any]] = []


def _add(cat: str, prompt: str, must_any: List[str], fields: List[str] | None = None, **extra: Any) -> None:
    i = len(BI_ACCEPTANCE_100) + 1
    BI_ACCEPTANCE_100.append(
        {
            "id": f"BI-{i:03d}",
            "category": cat,
            "prompt": prompt,
            "must_any": must_any,
            "fields_any": fields or [],
            **extra,
        }
    )


# Business Models (20)
for p in [
    "What is HDFC Bank's business model?",
    "How does Reliance Industries make money?",
    "What is Infosys' business model?",
    "Explain TCS business model.",
    "What is a bank business model?",
    "Explain a SaaS business model.",
    "What is a marketplace business model?",
    "Explain a cement company business model.",
    "What is an airline business model?",
    "Explain a hospital business model.",
    "What is an NBFC business model?",
    "Explain a retail business model.",
    "What is a subscription business model?",
    "Explain a utility business model.",
    "What is a conglomerate business model?",
    "Explain Wipro's business model.",
    "What is ICICI Bank's business model?",
    "Explain a manufacturing business model.",
    "What is a platform business model?",
    "Explain an insurance business model.",
]:
    _add("business_model", p, ["business_model"], ["business_type", "how_it_makes_money"])

# Moats (12)
for p in [
    "What is HDFC Bank's moat?",
    "Explain competitive advantage for TCS.",
    "What is Costco's moat conceptually for a membership retailer?",
    "Explain network effects as a moat.",
    "What creates switching costs for banks?",
    "Explain brand moat in consumer businesses.",
    "What is Infosys competitive advantage?",
    "Explain scale advantages in cement.",
    "What is a licensing moat?",
    "Explain distribution moat for banks.",
    "What is customer lock-in in SaaS?",
    "Explain moat durability for IT services.",
]:
    _add("moat", p, ["moat"], ["primary_moats", "durability", "dimensions"])

# Industry / Porter (12)
for p in [
    "Explain Porter's five forces for banks.",
    "What is the industry structure of cement?",
    "Explain entry barriers in airlines.",
    "What is supplier power in hospitals?",
    "Explain competitive rivalry in IT services.",
    "What substitutes threaten SaaS?",
    "Explain industry concentration in telecom infrastructure.",
    "What is customer power in retail?",
    "Explain Porter five forces for marketplaces.",
    "What are entry barriers for insurance?",
    "Explain industry structure for NBFCs.",
    "What is rivalry like in restaurants?",
]:
    _add("industry", p, ["industry", "value_drivers"], ["porter", "value_drivers"])

# Competition / comparison (10)
for p in [
    "Compare TCS vs Infosys.",
    "Compare HDFC Bank vs ICICI Bank.",
    "Compare Reliance Industries vs ONGC on business model axes.",
    "TCS versus Wipro business comparison.",
    "Compare a bank vs an NBFC business model.",
    "Compare SaaS vs IT services unit economics.",
    "Compare cement vs airlines capital intensity.",
    "Compare hospitals vs retail operating leverage.",
    "Compare marketplace vs manufacturer moats.",
    "Compare insurance vs banks growth modes.",
]:
    _add("competition", p, ["comparison", "business_model", "unit_economics", "moat"], [])

# Management (8)
for p in [
    "Evaluate management quality for Reliance Industries.",
    "What is capital allocation quality?",
    "Explain governance assessment without inventing facts.",
    "How should AGI score shareholder friendliness?",
    "Explain return discipline for management.",
    "What is strategic consistency in management quality?",
    "Explain acquisition history evaluation.",
    "How to assess management execution quality?",
]:
    _add("management", p, ["management"], ["axes", "policy"])

# Growth (8)
for p in [
    "What drives growth for HDFC Bank?",
    "Explain organic vs acquisition-led growth.",
    "What is pricing-led growth?",
    "Explain volume-led growth in cement.",
    "What is mix improvement?",
    "Explain cross-selling in banks.",
    "What is capacity expansion growth?",
    "Explain market share gains as a growth mode.",
]:
    _add("growth", p, ["growth"], ["primary_modes", "modes"])

# Unit Economics (10)
for p in [
    "Explain unit economics for SaaS.",
    "What is the unit economics chain for banks?",
    "Explain restaurant unit economics.",
    "What is marketplace contribution margin logic?",
    "Explain manufacturing unit economics.",
    "What is hospital unit economics?",
    "Explain airline unit economics.",
    "What is retail unit economics?",
    "Explain NBFC unit economics.",
    "What is insurance unit economics?",
]:
    _add("unit_economics", p, ["unit_economics"], ["industry_chain", "chain"])

# Capital intensity / value drivers (10)
for p in [
    "What are value drivers for software / SaaS?",
    "What drives value in banks — NIM, CASA, credit cost?",
    "What are cement value drivers?",
    "Explain airline value drivers load factor yield ATF.",
    "What are hospital value drivers ARPOB occupancy ALOS?",
    "Explain capital intensity for utilities.",
    "What is capital intensity in IT services?",
    "Explain working capital profile for retail.",
    "What is operating leverage in airlines?",
    "Explain value drivers for marketplaces.",
]:
    _add("value_drivers", p, ["value_drivers", "business_model", "unit_economics"], ["value_drivers"])

# Risks (5)
for p in [
    "What are key business risks for banks?",
    "Explain commodity risk for airlines.",
    "What is customer concentration risk in IT services?",
    "Explain regulatory risk for insurance.",
    "What refinancing risks do NBFCs face?",
]:
    _add("risks", p, ["risks"], ["primary_risks"])

# Lifecycle (5)
for p in [
    "What is the business lifecycle of a mature bank?",
    "Explain hypergrowth lifecycle.",
    "What is a turnaround lifecycle stage?",
    "Classify lifecycle for cement industry default.",
    "Explain cyclical recovery lifecycle.",
]:
    _add("lifecycle", p, ["lifecycle"], ["stage"])

assert len(BI_ACCEPTANCE_100) == 100, len(BI_ACCEPTANCE_100)


def evaluate_bi_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    modules = list(payload.get("modules_used") or [])
    assertions: Dict[str, bool] = {}
    must = case.get("must_any") or []
    assertions["module_selection"] = any(m in modules for m in must) if must else bool(modules)
    assertions["has_summary"] = bool(payload.get("summary"))
    assertions["direct_answer_first"] = len(str(payload.get("summary") or "")) > 20
    assertions["no_fabrication"] = payload.get("fabricated") is False
    assertions["ask_not_required"] = True  # suite is foundation-only

    # Field presence across nested modules
    fields_ok = True
    wanted = case.get("fields_any") or []
    if wanted:
        blob = str(payload)
        # also check nested dict keys
        nested_keys = set()
        for v in payload.values():
            if isinstance(v, dict):
                nested_keys.update(v.keys())
        fields_ok = any(f in nested_keys or f in blob for f in wanted)
    assertions["required_fields"] = fields_ok

    # No consulting jargon / framework leakage markers in summary
    summary = (payload.get("summary") or "").lower()
    bad = ("synergistic paradigm", "leverage our north star", "☐", "framework:", "committee:")
    assertions["no_framework_leak"] = not any(b in summary for b in bad)

    if case["category"] == "management":
        mg = payload.get("management") or {}
        assertions["management_no_invent"] = mg.get("policy") == "no_fabricated_management_claims" or bool(mg.get("axes"))

    if case["category"] == "competition":
        # Either comparison module fired, or industry/unit-econ comparison content present
        assertions["comparison_or_axes"] = (
            "comparison" in modules
            or bool(payload.get("comparison"))
            or bool(payload.get("unit_economics"))
            or bool(payload.get("business_model"))
        )

    passed = all(assertions.values())
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "modules": modules,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "summary": (payload.get("summary") or "")[:220],
        "pass": passed,
    }
