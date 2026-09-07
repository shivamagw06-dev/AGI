"""Intent detection and Investment Intelligence orchestration."""

from __future__ import annotations

import re
from typing import Any, Optional

from investment_intelligence import engines
from investment_intelligence.policy import assert_no_recommendation, strip_recommendation_language
from investment_intelligence.profiles import get_profile, resolve_entity
from investment_intelligence.schema import InvestmentPackage, RECOMMENDATION_POLICY


def detect_intents(question: str) -> list[str]:
    q = (question or "").lower()
    intents: list[str] = []
    if re.search(r"\b(thesis|investment case|so what|attractiveness)\b", q):
        intents.append("thesis")
    if re.search(r"\b(quality|scorecard|management quality|business quality)\b", q):
        intents.append("quality")
    if re.search(r"\b(catalysts?|rerate|what could (improve|drive|lift))\b", q):
        intents.append("catalysts")
    if re.search(r"\b(risks?|tail risks?)\b", q):
        intents.append("risks")
    if re.search(
        r"\b(scenarios?|bull case|bear case|base case|bull,? base,? and bear)\b",
        q,
    ):
        intents.append("scenarios")
    if re.search(
        r"\b(valuat\w*|multiples?|why might .+ (improve|expand)|roic improve)\b",
        q,
    ):
        intents.append("valuation")
    if re.search(
        r"\b(capital allocat\w*|buybacks?|dividends?|incremental roic|capex)\b",
        q,
    ):
        intents.append("capital_allocation")
    # Bare "roic" without "improve" → capital allocation lens
    if re.search(r"\broic\b", q) and "valuation" not in intents and "capital_allocation" not in intents:
        intents.append("capital_allocation")
    if re.search(r"\b(committee|analyst view|deliberat\w*)\b", q):
        intents.append("committee")
    if re.search(r"\b(monitor|monitoring|watch|leading indicators?)\b", q):
        intents.append("monitoring")
    if re.search(
        r"\b(unknowns?|uncertainty|missing data|evidence strength|confidence)\b",
        q,
    ):
        intents.append("evidence")
    if re.search(r"\b(governanc\w*|board|related party)\b", q):
        intents.append("governance")
    if re.search(r"\b(compare|vs\.?|versus|quality perspective)\b", q):
        intents.append("compare")
    if not intents:
        intents.append("thesis")
    # dedupe
    seen = set()
    out = []
    for i in intents:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def analyse(question: str, *, entity: Optional[str] = None) -> dict[str, Any]:
    intents = detect_intents(question)
    key = entity or resolve_entity(question)
    pkg = InvestmentPackage(ok=False, question=question, recommendation_policy=RECOMMENDATION_POLICY)

    # Comparison path
    if "compare" in intents:
        # Try extract two entities
        from investment_intelligence.profiles import ENTITY_ALIASES, PROFILES

        found = []
        low = question.lower()
        for alias, k in sorted(ENTITY_ALIASES.items(), key=lambda kv: -len(kv[0])):
            if alias in low and k in PROFILES and k not in found:
                found.append(k)
            if len(found) >= 2:
                break
        if len(found) >= 2:
            cmp = engines.compare_quality(found[0], found[1])
            pkg.ok = True
            pkg.entity = " vs ".join(found)
            pkg.executive_summary = cmp["summary"]
            pkg.summary = cmp["summary"]
            pkg.quality = cmp
            pkg.modules_used = ["compare", "quality"]
            pkg.unknowns = ["Company-specific near-term catalysts may differ"]
            pkg.monitoring_points = ["Relative volume/margin/share trends"]
            pkg.confidence = 0.85
            pkg.fabricated = False
            out = pkg.to_dict()
            assert assert_no_recommendation(out)
            return out

    if not key:
        pkg.executive_summary = (
            "Investment Intelligence needs a supported company or industry "
            "(e.g. Reliance, TCS, HDFC Bank, Asian Paints, hospitals, banks). "
            "Ask about thesis, quality, risks, catalysts, scenarios, valuation drivers, "
            "or capital allocation. No BUY/SELL recommendations are issued."
        )
        pkg.summary = pkg.executive_summary
        pkg.confidence = 0.25
        pkg.unknowns = ["Entity not resolved"]
        return pkg.to_dict()

    profile = get_profile(key)
    assert profile is not None
    pkg.entity = profile["name"]
    pkg.industry = profile.get("industry")
    modules: list[str] = []
    supporting: list[str] = []
    summary = ""

    if "thesis" in intents or intents == ["monitoring"]:
        th = engines.thesis(profile)
        pkg.thesis = th
        modules.append("thesis")
        if not summary:
            summary = th["summary"]
        supporting.append(th["business_quality"])

    if "quality" in intents or "governance" in intents:
        ql = engines.quality(profile)
        pkg.quality = ql
        modules.append("quality")
        if "quality" in intents[:1] or not summary:
            summary = ql["summary"]
        supporting.append(f"Composite quality {ql['composite_score']}/100")

    if "catalysts" in intents:
        cat = engines.catalysts(profile)
        pkg.catalysts = cat["catalysts"]
        modules.append("catalysts")
        if "catalysts" in intents[:1] or not summary:
            summary = cat["summary"]

    if "risks" in intents:
        rk = engines.risks(profile)
        pkg.risks = rk["risks"]
        modules.append("risks")
        if "risks" in intents[:1] or not summary:
            summary = rk["summary"]

    if "scenarios" in intents:
        sc = engines.scenarios(profile)
        pkg.scenarios = sc
        modules.append("scenarios")
        if "scenarios" in intents[:1] or not summary:
            summary = sc["summary"]

    if "valuation" in intents:
        val = engines.valuation_intel(profile)
        pkg.valuation = val
        modules.append("valuation")
        if "valuation" in intents[:1] or not summary:
            summary = val["summary"]

    if "capital_allocation" in intents:
        ca = engines.capital_allocation(profile)
        pkg.capital_allocation = ca
        modules.append("capital_allocation")
        if "capital_allocation" in intents[:1] or not summary:
            summary = ca["summary"]

    if "committee" in intents:
        cm = engines.committee(profile)
        pkg.committee = cm
        modules.append("committee")
        if "committee" in intents[:1] or not summary:
            summary = cm["summary"]

    if "evidence" in intents or True:
        ev = engines.evidence_card(profile)
        pkg.evidence = ev
        if "evidence" in intents:
            modules.append("evidence")
            if "evidence" in intents[:1] or not summary:
                summary = (
                    f"Evidence strength for {profile['name']} is {ev['strength']}. "
                    f"Missing data: {', '.join(ev['missing_data'][:3]) or 'none listed'}. "
                    f"Uncertainty is explicit; no recommendation is issued."
                )

    # Always attach graph for investment object completeness when thesis/quality run
    if modules:
        g = engines.graph(profile)
        pkg.graph = g
        modules.append("graph")

    if "monitoring" in intents or modules:
        pkg.monitoring_points = list(profile.get("monitoring") or [])[:8]
        if "monitoring" in intents and (not summary or intents[0] == "monitoring"):
            unk = "; ".join(list(profile.get("unknowns") or [])[:2]) or "none listed"
            summary = strip_recommendation_language(
                f"Investors should monitor for {profile['name']}: "
                + "; ".join(pkg.monitoring_points[:5])
                + f". Unknowns to track: {unk}. "
                + "Monitoring points are observational — not trade instructions."
            )
            if "monitoring" not in modules:
                modules.append("monitoring")

    pkg.unknowns = list(profile.get("unknowns") or [])[:8]
    pkg.executive_summary = strip_recommendation_language(summary)[:900]
    pkg.summary = pkg.executive_summary
    pkg.supporting_analysis = [strip_recommendation_language(s) for s in supporting if s][:8]
    pkg.modules_used = []
    seen = set()
    for m in modules:
        if m not in seen:
            seen.add(m)
            pkg.modules_used.append(m)
    pkg.ok = bool(pkg.executive_summary)
    pkg.confidence = 0.88 if pkg.ok else 0.2
    pkg.fabricated = False
    pkg.recommendation = None
    pkg.recommendation_policy = RECOMMENDATION_POLICY

    # Executive communication order is encoded in fields:
    # executive_summary → supporting_analysis → evidence → unknowns → monitoring_points
    out = pkg.to_dict()
    out["executive_summary"] = strip_recommendation_language(out.get("executive_summary") or "")
    out["summary"] = out["executive_summary"]
    out["recommendation"] = None
    out["recommendation_policy"] = RECOMMENDATION_POLICY
    if not assert_no_recommendation(out):
        # Last-resort sanitize rather than crash the engine.
        out["executive_summary"] = strip_recommendation_language(
            (out.get("executive_summary") or "")
            + " Observations only under recommendation policy (no buy / no sell)."
        )
        out["summary"] = out["executive_summary"]
    return out
