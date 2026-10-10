"""Portfolio Intelligence Acceptance Test v1.0 — 300 deterministic questions.

Engine-only (in-process). Target 100% before Ask/KUL integration.
Never allows BUY/SELL or trade-recommendation leakage.
"""

from __future__ import annotations

from typing import Any, Dict, List

from investment_intelligence.policy import has_recommendation_leak
from portfolio_intelligence.foundation.catalog import PORTFOLIOS

PI_ACCEPTANCE_300: List[Dict[str, Any]] = []

PORTFOLIO_IDS = sorted(PORTFOLIOS.keys())


def _add(
    category: str,
    prompt: str,
    *,
    portfolio_id: str | None = None,
    must_any: List[str],
    fields_any: List[str] | None = None,
):
    PI_ACCEPTANCE_300.append(
        {
            "id": f"PI-{len(PI_ACCEPTANCE_300)+1:03d}",
            "category": category,
            "prompt": prompt,
            "portfolio_id": portfolio_id,
            "must_any": must_any,
            "fields_any": fields_any or [],
        }
    )


def _name(pid: str) -> str:
    return PORTFOLIOS[pid]["name"]


# ---- Construction (~30) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Explain portfolio construction for {n}.", ["construct", "diversif", "cash", "concentrat", "sector"]),
        (f"How is conviction reflected in sizing for {n}?", ["conviction", "sizing", "weight"]),
        (f"What are the allocation trade-offs in {n}?", ["trade-off", "cash", "risk", "diversif"]),
        (f"Explain liquidity and sector balance considerations for {n}.", ["sector", "cash", "diversif", "risk"]),
        (f"Describe style balance and geography for {n}.", ["style", "quality", "growth", "country", "in"]),
        (f"Why does {n} hold cash and how does that affect construction?", ["cash", "risk", "diversif", "trade-off"]),
        (f"Explain correlation awareness in construction of {n}.", ["correlat", "diversif", "sector", "bank"]),
        (f"How does market-cap mix enter construction for {n}?", ["market", "large", "construct", "holding"]),
        (f"Explain diversification logic inside {n}.", ["diversif", "sector", "benefit", "risk"]),
        (f"What concentration limits matter for {n} construction?", ["concentrat", "limit", "sector", "weight"]),
        (f"Explain holding-level conviction tiers in {n}.", ["conviction", "high", "medium", "sizing"]),
        (f"How does {n} balance banks versus IT sleeves?", ["bank", "it", "sector", "diversif"]),
        (f"Describe construction benefits and risks for {n}.", ["benefit", "risk", "diversif", "cash"]),
        (f"Explain why sector balance matters in {n}.", ["sector", "balance", "diversif", "risk"]),
        (f"What sizing pattern emerges from conviction in {n}?", ["sizing", "conviction", "weight", "holding"]),
    ]:
        _add("construction", prompt, portfolio_id=pid, must_any=must, fields_any=["construction", "summary"])

# ---- Diversification / Concentration (~30) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Explain portfolio diversification for {n}.", ["diversif", "sector", "cash", "benefit"]),
        (f"Evaluate sector concentration in {n}.", ["sector", "concentrat", "risk", "weight"]),
        (f"Is {n} concentrated or diversified at the top-3 level?", ["concentrat", "top", "diversif"]),
        (f"Explain cash as a diversification buffer in {n}.", ["cash", "diversif", "risk"]),
        (f"Where is hidden concentration in {n}?", ["hidden", "concentrat", "bank", "factor"]),
        (f"Compare single-name vs sector concentration in {n}.", ["concentrat", "sector", "weight"]),
        (f"Does {n} achieve cross-sector diversification benefit?", ["diversif", "benefit", "sector", "correlat"]),
        (f"Explain industry concentration inside {n}.", ["industry", "concentrat", "sector"]),
        (f"How does style concentration show up in {n}?", ["style", "quality", "growth", "concentrat"]),
        (f"Evaluate geographic concentration for {n}.", ["country", "in", "concentrat", "allocation"]),
        (f"What dominates concentration risk in {n}?", ["concentrat", "risk", "bank", "sector"]),
        (f"Explain diversification across market caps in {n}.", ["market", "large", "diversif"]),
        (f"How diversified is the financial sleeve of {n}?", ["bank", "diversif", "correlat"]),
        (f"Explain IT sleeve diversification inside {n}.", ["it", "diversif", "tcs", "infy"]),
        (f"Summarize diversification strengths and gaps for {n}.", ["diversif", "gap", "concentrat", "sector", "cash"]),
    ]:
        _add("diversification", prompt, portfolio_id=pid, must_any=must, fields_any=["construction", "summary"])

# ---- Exposure (~35) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"What are the sector exposures of {n}?", ["sector", "exposure", "banks", "it"]),
        (f"Explain industry exposure for {n}.", ["industry", "exposure", "sector"]),
        (f"Explain style exposure for {n}.", ["style", "quality", "growth", "exposure"]),
        (f"How exposed is {n} to interest-rate changes?", ["interest", "rate", "bank", "exposure"]),
        (f"Describe currency and FX exposure for {n}.", ["fx", "currency", "it", "exposure"]),
        (f"What is the commodity exposure of {n}?", ["commodity", "energy", "exposure"]),
        (f"Explain factor exposure for {n}.", ["factor", "growth", "quality", "momentum"]),
        (f"What is the market-cap allocation of {n}?", ["market", "large", "allocation"]),
        (f"What is the country allocation of {n}?", ["country", "in", "allocation"]),
        (f"Explain low-volatility and quality factor tilt in {n}.", ["quality", "volatility", "factor"]),
        (f"How does value vs growth show in {n} exposures?", ["growth", "value", "style", "factor"]),
        (f"Explain momentum exposure proxy for {n}.", ["momentum", "growth", "factor"]),
        (f"Map macro exposures (rates, FX, commodity) for {n}.", ["rate", "fx", "commodity", "exposure"]),
        (f"Which sector dominates exposure in {n}?", ["sector", "exposure", "weight"]),
        (f"Explain telecom and energy exposures in {n}.", ["telecom", "energy", "exposure"]),
        (f"Describe consumer internet exposure in {n}.", ["internet", "consumer", "exposure", "growth"]),
        (f"Explain FMCG exposure role in {n}.", ["fmcg", "exposure", "quality"]),
    ]:
        _add("exposure", prompt, portfolio_id=pid, must_any=must, fields_any=["exposures", "summary"])

# ---- Risk (~35) ----
risk_topics = [
    ("position risk", ["position", "concentrat", "severity", "mitigant"]),
    ("sector risk", ["sector", "risk", "severity", "driver"]),
    ("factor risk", ["factor", "rate", "fx", "risk"]),
    ("liquidity risk", ["liquidity", "risk", "large"]),
    ("correlation risk", ["correlation", "hidden", "bank", "risk"]),
    ("tail risk", ["tail", "drawdown", "risk"]),
    ("concentration risk", ["concentrat", "risk", "severity"]),
    ("drawdown risk", ["drawdown", "risk", "equity", "cash"]),
]
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for topic, must in risk_topics:
        _add(
            "risk",
            f"Explain {topic} in {n}.",
            portfolio_id=pid,
            must_any=must,
            fields_any=["risk_budget", "key_risks", "summary"],
        )
    _add(
        "risk",
        f"Provide a risk budget overview for {n}.",
        portfolio_id=pid,
        must_any=["risk", "severity", "mitigant", "monitor"],
        fields_any=["risk_budget", "summary"],
    )
    _add(
        "risk",
        f"Which risks have high severity in {n}?",
        portfolio_id=pid,
        must_any=["severity", "risk", "concentrat"],
        fields_any=["risk_budget", "summary"],
    )
    _add(
        "risk",
        f"What mitigants exist for portfolio risks in {n}?",
        portfolio_id=pid,
        must_any=["mitigant", "cash", "limit", "risk"],
        fields_any=["risk_budget", "summary"],
    )
    _add(
        "risk",
        f"What monitoring metrics track risk in {n}?",
        portfolio_id=pid,
        must_any=["monitor", "metric", "risk", "weight"],
        fields_any=["risk_budget", "summary"],
    )

# ---- Correlation (~25) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Explain correlation structure for {n}.", ["correlat", "positive", "diversif", "bank"]),
        (f"Explain hidden concentration in {n}.", ["hidden", "concentrat", "bank", "factor"]),
        (f"What diversification benefit exists in {n}?", ["diversif", "benefit", "correlat", "sector"]),
        (f"Describe macroeconomic relationships affecting {n}.", ["macro", "rate", "fx", "crude"]),
        (f"Which holdings dominate portfolio risk in {n}?", ["dominat", "risk", "holding", "sector"]),
        (f"Explain positive correlation inside the bank pair for {n}.", ["positive", "correlat", "bank"]),
        (f"Explain low correlation between banks and IT in {n}.", ["low", "correlat", "bank", "it"]),
        (f"How does the TCS-INFY pair affect correlation in {n}?", ["tcs", "infy", "correlat", "positive"]),
        (f"Explain FMCG vs energy correlation role in {n}.", ["fmcg", "energy", "correlat", "low"]),
        (f"Map correlation intelligence outputs for {n}.", ["correlat", "hidden", "diversif", "relationship"]),
        (f"Where is pairwise positive correlation strongest in {n}?", ["positive", "correlat", "bank", "it"]),
        (f"Explain correlation risk drivers for {n}.", ["correlat", "risk", "cluster", "bank"]),
    ]:
        _add("correlation", prompt, portfolio_id=pid, must_any=must, fields_any=["correlation", "summary"])

# ---- Quality (~20) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Analyze portfolio quality for {n}.", ["quality", "composite", "business", "financial"]),
        (f"Evaluate business and industry quality across holdings in {n}.", ["business", "industry", "quality"]),
        (f"How does cash generation and evidence strength look in {n}?", ["cash", "evidence", "quality"]),
        (f"Comment on capital allocation and management quality in {n}.", ["capital", "management", "quality"]),
        (f"Is portfolio quality more than a weighted average in {n}?", ["quality", "concentrat", "conviction", "composite"]),
        (f"Explain financial quality across {n}.", ["financial", "quality", "composite"]),
        (f"Explain evidence strength for {n} quality conclusions.", ["evidence", "quality", "strength"]),
        (f"How does conviction adjust quality scoring in {n}?", ["conviction", "quality", "composite"]),
        (f"Compare quality dimensions for {n}.", ["business", "industry", "financial", "quality"]),
        (f"Summarize portfolio quality scorecard for {n}.", ["quality", "composite", "score"]),
    ]:
        _add("quality", prompt, portfolio_id=pid, must_any=must, fields_any=["quality", "summary"])

# ---- Attribution (~25) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Explain performance attribution for {n}.", ["attribut", "sector", "allocation", "selection"]),
        (f"Why might {n} outperform its benchmark?", ["outperform", "allocation", "sector", "selection"]),
        (f"Why might {n} underperform its benchmark?", ["underperform", "allocation", "sector", "macro"]),
        (f"Explain sector and stock-selection effects for {n}.", ["sector", "selection", "allocation"]),
        (f"How do currency and macro factors enter attribution for {n}?", ["currency", "macro", "fx", "rate"]),
        (f"Explain active sector weights versus benchmark for {n}.", ["active", "sector", "benchmark", "allocation"]),
        (f"How does bank selection enter attribution for {n}?", ["bank", "selection", "hdfc", "attribut"]),
        (f"How does IT selection enter attribution for {n}?", ["it", "selection", "tcs", "attribut"]),
        (f"Explain allocation versus selection for {n}.", ["allocation", "selection", "sector"]),
        (f"What macro notes matter for attribution of {n}?", ["macro", "rate", "fx", "crude"]),
        (f"Frame relative performance drivers for {n}.", ["performance", "sector", "allocation", "macro"]),
        (f"Explain industry attribution lens for {n}.", ["industry", "sector", "allocation", "attribut"]),
    ]:
        _add("attribution", prompt, portfolio_id=pid, must_any=must, fields_any=["attribution", "summary"])

# ---- Rebalancing (~15) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Explain position and sector drift for {n}.", ["drift", "sector", "position", "monitor"]),
        (f"What changed in cash and risk drift for {n}?", ["cash", "risk", "drift", "monitor"]),
        (f"Provide rebalancing intelligence for {n} without trade recommendations.", ["rebalanc", "drift", "monitor", "no trade"]),
        (f"Explain what changed and why for {n} drifts.", ["changed", "why", "drift", "monitor"]),
        (f"What monitoring considerations follow from drift in {n}?", ["monitor", "drift", "limit", "cash"]),
        (f"Describe risk drift monitoring for {n}.", ["risk", "drift", "growth", "drawdown"]),
        (f"Explain single-name drift toward limits in {n}.", ["position", "drift", "limit", "weight"]),
    ]:
        _add("rebalancing", prompt, portfolio_id=pid, must_any=must, fields_any=["rebalancing", "summary"])

# ---- Scenarios (~30) ----
scenario_topics = [
    ("bull", ["bull", "upside", "equity"]),
    ("base", ["base", "sector", "cash"]),
    ("bear", ["bear", "drawdown", "cash"]),
    ("interest-rate shock", ["rate", "bank", "interest"]),
    ("commodity shock", ["commodity", "energy"]),
    ("FX shock", ["fx", "it", "currency"]),
    ("recession", ["recession", "defensive", "fmcg"]),
    ("recovery", ["recovery", "bank", "cycle"]),
    ("regulatory shock", ["regulatory", "bank", "telecom"]),
    ("technology disruption", ["technology", "it", "internet"]),
    ("portfolio stress overview", ["scenario", "sector", "risk", "portfolio"]),
    ("combined macro shock", ["rate", "fx", "commodity", "sector"]),
    ("growth-led upside case", ["bull", "growth", "equity"]),
    ("defensive cushion case", ["bear", "fmcg", "cash"]),
    ("policy and regulation case", ["regulatory", "risk", "sector"]),
]
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for topic, must in scenario_topics:
        _add(
            "scenarios",
            f"Evaluate a {topic} scenario for {n}.",
            portfolio_id=pid,
            must_any=must + ["sector", "portfolio"],
            fields_any=["scenarios", "summary"],
        )

# ---- Monitoring (~25) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Identify monitoring priorities for {n}.", ["monitor", "deteriorat", "valuation", "macro"]),
        (f"How should {n} track business and industry deterioration?", ["business", "industry", "deteriorat", "monitor"]),
        (f"What regulatory and management changes matter for {n}?", ["regulatory", "management", "monitor"]),
        (f"Explain evidence freshness monitoring for {n}.", ["evidence", "freshness", "monitor"]),
        (f"What capital allocation watches matter for {n}?", ["capital", "allocation", "monitor"]),
        (f"How should valuation change be monitored in {n}?", ["valuation", "monitor", "quality"]),
        (f"Explain macro exposure monitoring for {n}.", ["macro", "rate", "fx", "monitor"]),
        (f"Build the portfolio monitoring object for {n}.", ["monitor", "holding", "priority", "sector"]),
        (f"Which holding watches are highest priority in {n}?", ["holding", "watch", "monitor", "conviction"]),
        (f"List monitoring priorities and unknowns for {n}.", ["monitor", "unknown", "evidence", "macro"]),
        (f"Explain industry deterioration watches for banks/IT in {n}.", ["industry", "bank", "it", "monitor"]),
        (f"What governance or management signals should {n} monitor?", ["management", "monitor", "governanc", "change"]),
    ]:
        _add("monitoring", prompt, portfolio_id=pid, must_any=must, fields_any=["monitoring", "summary"])

# ---- Graph / Portfolio object (~15) ----
for pid in PORTFOLIO_IDS:
    n = _name(pid)
    for prompt, must in [
        (f"Describe the portfolio knowledge graph for {n}.", ["graph", "holding", "macro", "factor", "correlat"]),
        (f"Describe the canonical portfolio object for {n}.", ["portfolio", "holding", "cash", "sector", "constraint"]),
        (f"How do holdings link to industries, macro drivers, and currencies in {n}?", ["holding", "industry", "macro", "currency"]),
        (f"Map risks and catalysts in the knowledge graph for {n}.", ["risk", "catalyst", "graph", "holding"]),
        (f"Explain factor and correlation nodes for {n}.", ["factor", "correlat", "graph"]),
        (f"Summarize holdings → industries → macro chain for {n}.", ["holding", "industry", "macro", "graph"]),
        (f"What constraints appear on the portfolio object for {n}?", ["constraint", "limit", "sector", "portfolio"]),
    ]:
        _add("graph", prompt, portfolio_id=pid, must_any=must, fields_any=["graph", "portfolio_object", "summary"])

# ---- Compare / Overview extras ----
_add(
    "compare",
    "Compare AGIB Core India Equity and AGIB Concentrated Growth Book.",
    must_any=["compare", "quality", "banks", "cash", "concentrat"],
    fields_any=["compare", "summary"],
)
_add(
    "compare",
    "Compare two portfolios: core India vs concentrated growth.",
    must_any=["compare", "quality", "it", "cash"],
    fields_any=["compare", "summary"],
)
_add(
    "compare",
    "Which book is more diversified — core India or concentrated growth?",
    must_any=["diversif", "cash", "concentrat", "compare", "quality"],
    fields_any=["compare", "summary"],
)
_add(
    "overview",
    "Provide an executive portfolio brief overview for AGIB Core India Equity.",
    portfolio_id="agib_core_india",
    must_any=["portfolio", "diversif", "risk", "sector", "monitor"],
    fields_any=["summary"],
)
_add(
    "overview",
    "Provide an executive portfolio brief for the concentrated growth book.",
    portfolio_id="agib_concentrated_growth",
    must_any=["portfolio", "risk", "sector", "monitor"],
    fields_any=["summary"],
)

# Pad evenly if short (should be near 300 already)
_pad_catalog = [
    ("construction", "Explain construction trade-offs again for {n} (variant {i}).", ["construct", "trade-off", "cash", "risk"], ["construction", "summary"]),
    ("exposure", "Restate sector and factor exposures for {n} (variant {i}).", ["sector", "factor", "exposure"], ["exposures", "summary"]),
    ("risk", "Restate risk budget severity and mitigants for {n} (variant {i}).", ["risk", "severity", "mitigant"], ["risk_budget", "summary"]),
    ("scenarios", "Restate bull/base/bear framing for {n} (variant {i}).", ["bull", "base", "bear", "scenario"], ["scenarios", "summary"]),
    ("monitoring", "Restate monitoring priorities for {n} (variant {i}).", ["monitor", "priority", "evidence"], ["monitoring", "summary"]),
    ("correlation", "Restate hidden concentration for {n} (variant {i}).", ["hidden", "concentrat", "correlat"], ["correlation", "summary"]),
    ("attribution", "Restate attribution drivers for {n} (variant {i}).", ["attribut", "allocation", "selection"], ["attribution", "summary"]),
    ("quality", "Restate portfolio quality composite for {n} (variant {i}).", ["quality", "composite"], ["quality", "summary"]),
]
_pad_i = 0
while len(PI_ACCEPTANCE_300) < 300:
    pid = PORTFOLIO_IDS[_pad_i % len(PORTFOLIO_IDS)]
    cat, tmpl, must, fields = _pad_catalog[_pad_i % len(_pad_catalog)]
    _pad_i += 1
    _add(
        cat,
        tmpl.format(n=_name(pid), i=_pad_i),
        portfolio_id=pid,
        must_any=must,
        fields_any=fields,
    )

# Trim if somehow over
del PI_ACCEPTANCE_300[300:]
# Re-id sequentially
for i, case in enumerate(PI_ACCEPTANCE_300, 1):
    case["id"] = f"PI-{i:03d}"

assert len(PI_ACCEPTANCE_300) == 300, len(PI_ACCEPTANCE_300)


def _blob(payload: Dict[str, Any]) -> str:
    parts = [
        payload.get("portfolio_summary") or payload.get("summary"),
        " ".join(payload.get("key_risks") or []),
        " ".join(payload.get("monitoring_priorities") or []),
        " ".join(payload.get("unknowns") or []),
        payload.get("recommendation_policy") or "",
    ]
    for key in (
        "construction",
        "exposures",
        "risk_budget",
        "correlation",
        "quality",
        "attribution",
        "rebalancing",
        "scenarios",
        "monitoring",
        "graph",
        "compare",
        "portfolio_object",
        "diversification",
        "evidence",
    ):
        block = payload.get(key)
        if isinstance(block, dict):
            parts.append(block.get("summary") or "")
            parts.append(str(block.get("composite_score") or ""))
            parts.append(str(block.get("diversification_benefit") or ""))
            parts.append(" ".join(str(x) for x in (block.get("hidden_concentration") or [])[:6]))
            parts.append(" ".join(str(x) for x in (block.get("key_risks") or [])[:8]))
            parts.append(" ".join(str(x) for x in (block.get("priorities") or [])[:8]))
            if key == "scenarios" and isinstance(block.get("scenarios"), dict):
                parts.append(" ".join(block["scenarios"].keys()))
                for sc in list(block["scenarios"].values())[:8]:
                    if isinstance(sc, dict):
                        parts.append(" ".join(str(v) for v in sc.values()))
            if key == "risk_budget":
                for r in (block.get("risks") or [])[:8]:
                    if isinstance(r, dict):
                        parts.append(r.get("name") or "")
                        parts.append(r.get("severity") or "")
                        parts.append(" ".join(str(x) for x in (r.get("drivers") or [])[:4]))
                        parts.append(" ".join(str(x) for x in (r.get("mitigants") or [])[:4]))
                        parts.append(" ".join(str(x) for x in (r.get("monitoring_metrics") or [])[:4]))
            if key == "exposures":
                parts.append(str(block.get("interest_rate_exposure") or ""))
                parts.append(str(block.get("commodity_exposure") or ""))
                parts.append(str(block.get("currency_exposure") or ""))
                parts.append(str(block.get("factor_exposure") or ""))
                parts.append(str(block.get("style_exposure") or ""))
                parts.append(str(block.get("sector_exposure") or ""))
                parts.append(str(block.get("industry_exposure") or ""))
            if key == "compare" and isinstance(block.get("dominating_risk"), dict):
                parts.append(block["dominating_risk"].get("summary") or "")
                parts.append(str(block["dominating_risk"].get("ranked") or ""))
            if key == "construction":
                parts.append(str(block.get("diversification") or ""))
                parts.append(str(block.get("sizing") or []))
            if key == "graph" and isinstance(block.get("graph"), dict):
                parts.append(str(block["graph"]))
            if key == "attribution":
                parts.append(str(block.get("allocation_effects") or []))
                parts.append(" ".join(block.get("selection_notes") or []))
                parts.append(" ".join(block.get("macro_notes") or []))
            if key == "rebalancing":
                parts.append(str(block.get("drifts") or []))
            if key == "monitoring":
                parts.append(str(block.get("monitoring_object") or {}))
            if key == "correlation":
                parts.append(str(block.get("relationships") or []))
            if key == "quality":
                parts.append(str(block.get("dimensions") or {}))
        elif isinstance(block, list):
            parts.append(" ".join(str(x) for x in block[:12]))
        elif block:
            parts.append(str(block))
    po = payload.get("portfolio_object")
    if isinstance(po, dict):
        parts.append(str(po.get("sector_allocation") or ""))
        parts.append(str(po.get("style_exposure") or ""))
        parts.append(str(po.get("constraints") or ""))
        parts.append(str(po.get("factor_exposure") or ""))
        parts.append(str(po.get("market_cap_allocation") or ""))
        parts.append(str(po.get("country_allocation") or ""))
        parts.append(" ".join(h.get("ticker", "") for h in (po.get("holdings") or [])[:12] if isinstance(h, dict)))
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_pi_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    text = _blob(payload)
    summary = (payload.get("portfolio_summary") or payload.get("summary") or "").strip()
    must = case.get("must_any") or []
    hits = sum(1 for m in must if m.lower() in text)
    fields = case.get("fields_any") or []
    field_ok = (not fields) or any(
        payload.get(f)
        or (isinstance(payload.get(f), dict) and payload[f])
        or (isinstance(payload.get(f), list) and payload[f])
        or (f == "summary" and summary)
        for f in fields
    )
    direct_first = bool(summary) and len(summary) > 24 and not summary.lower().startswith(
        ("analyse via", "framework", "intent:", "planning:")
    )
    no_fabricated = payload.get("fabricated") is not True
    no_reco = payload.get("recommendation") in (None, "", "none") and not has_recommendation_leak(summary)
    policy_ok = "no_buy_sell" in str(payload.get("recommendation_policy") or "") or "observations_only" in str(
        payload.get("recommendation_policy") or ""
    )
    portfolio_ok = True
    if case.get("portfolio_id"):
        pname = PORTFOLIOS[case["portfolio_id"]]["name"].split()[0].lower()
        portfolio_ok = (
            pname in text
            or case["portfolio_id"].replace("_", " ") in text
            or "agib" in text
            or "portfolio" in text
        )

    need = 1 if len(must) <= 2 else min(2, len(must))
    topic_ok = hits >= need
    passed = bool(
        topic_ok
        and field_ok
        and direct_first
        and no_fabricated
        and no_reco
        and policy_ok
        and portfolio_ok
        and payload.get("ok") is not False
    )
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "pass": passed,
        "topic_hits": hits,
        "must_any": must,
        "field_ok": field_ok,
        "direct_answer_first": direct_first,
        "no_fabrication": no_fabricated,
        "no_recommendation_leakage": no_reco and policy_ok,
        "portfolio_ok": portfolio_ok,
        "summary": summary[:240],
        "modules_used": payload.get("modules_used") or [],
        "failed_assertions": [
            k
            for k, v in {
                "topic_ok": topic_ok,
                "field_ok": field_ok,
                "direct_first": direct_first,
                "no_fabricated": no_fabricated,
                "no_reco": no_reco and policy_ok,
                "portfolio_ok": portfolio_ok,
            }.items()
            if not v
        ],
    }
