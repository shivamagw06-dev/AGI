"""Classify a question into a Reasoning Family (soft, heuristic)."""

from __future__ import annotations

import re
from typing import Any

from institutional_reasoning.families import (
    ACCOUNTING,
    CAUSALITY,
    COMPARISON,
    CONTRADICTION,
    DUAL_HYPOTHESIS,
    EVIDENCE,
    SELF_CRITIQUE,
    UNCERTAINTY,
    VALUATION,
)

_CONFLICT = re.compile(
    r"\b(but|however|despite|whereas|while|although|yet|even\s+though)\b",
    re.I,
)
_UP = re.compile(
    r"\b(increas\w*|grew|growth|rose|rises|rise|rising|accelerat\w*|higher|up|doubled|faster|"
    r"strong|surged|jumped|improved|hit\s+a\s+record|soared|expanded|raised?)\b",
    re.I,
)
_DOWN = re.compile(
    r"\b(declin\w*|fell|fall|drop\w*|down|lower|slowed|slower|weak\w*|compress\w*|"
    r"negative|worsened|collapsed|lengthened|aged|stagnat\w*)\b",
    re.I,
)

_ASK = re.compile(
    r"\b("
    r"which\s+(signal|metric)|more\s+important|what\s+does\s+this\s+suggest|"
    r"what\s+does\s+this\s+mean|what\s+could\s+explain|what\s+questions|can\s+both\s+be\s+true|"
    r"is\s+this\s+(positive|healthy)|how\s+should|interpret|explain|"
    r"possible\s+reasons|what\s+might|what\s+risks|how\s+is\s+that\s+possible|"
    r"how\s+can\s+both|how\s+might|outline|trace|give\s+three|what\s+else|"
    r"how\s+do\s+you|what\s+caution|what\s+process|how\s+to\s+weight|"
    r"list\s+the|list\s+falsifiers|argue\s+against|which\s+prevails|"
    r"more\s+exposed|what\s+should\s+an\s+analyst|questions\s+arise|sketch"
    r")\b",
    re.I,
)


def _has_conflict_directions(text: str) -> bool:
    return bool(_CONFLICT.search(text) and _UP.search(text) and _DOWN.search(text))


def classify_family(query: str) -> dict[str, Any]:
    """Return family_id, confidence, and signals. Never raises."""
    q = str(query or "").strip()
    ql = q.lower()
    signals: list[str] = []

    # --- Dual hypothesis / hardest multi-metric ---
    metrics = [
        "revenue",
        "profit",
        "free cash",
        "fcf",
        "inventory",
        "debt",
        "share price",
        "stock price",
    ]
    metric_hits = sum(1 for m in metrics if m in ql)
    if metric_hits >= 4 and (
        re.search(r"two\s+(equally\s+)?plausible|two\s+explanations|do\s+not\s+decide", ql)
        or re.search(r"different\s+directions|moved\s+in\s+different", ql)
        or re.search(r"distinguish\s+between|do\s+not\s+pick\s+a\s+winner|do\s+not\s+conclude", ql)
        or re.search(r"two\s+coherent\s+stories|two\s+plausible\s+readings", ql)
    ):
        return {
            "family_id": DUAL_HYPOTHESIS,
            "confidence": 0.95,
            "signals": ["multi_metric", "dual_hypothesis_request"],
        }

    # --- Self-critique ---
    if re.search(
        r"\b(challenge|devil.?s?\s+advocate|argue.{0,40}wrong|list.{0,40}assumption|"
        r"list\s+falsifiers|falsif|against\s+your\s+own|what\s+would\s+invalidate|"
        r"how\s+could\s+that\s+be\s+wrong|prove\s+that\s+view\s+wrong)\b",
        ql,
    ):
        signals.append("self_critique_lexicon")
        return {"family_id": SELF_CRITIQUE, "confidence": 0.9, "signals": signals}

    # --- Uncertainty / missing data ---
    if re.search(
        r"\b(not\s+yet\s+published|have\s+not\s+published|missing\s+data|"
        r"what\s+cannot\s+be\s+concluded|insufficient\s+evidence|"
        r"no\s+financial\s+results|results\s+have\s+not|results\s+are\s+delayed|"
        r"withdrawn|undisclosed|only\s+nine\s+months|"
        r"what\s+remains\s+unknown|conclusions\s+are\s+blocked|"
        r"must\s+now\s+be\s+withheld|estimation\s+uncertainty)\b",
        ql,
    ):
        signals.append("missing_evidence")
        return {"family_id": UNCERTAINTY, "confidence": 0.88, "signals": signals}

    # --- Valuation before evidence so DCF / multiple questions stay in Valuation ---
    if re.search(
        r"\b(p/?e|price[\s-]?to[\s-]?earnings|price[\s-]?to[\s-]?book|p/?b|"
        r"ev/?ebitda|\bev\b|enterprise\s+value|multiple|dcf|valuation|fair\s+values?|"
        r"price[\s-]?to[\s-]?sales|re-?rates?|de-?rated)\b",
        ql,
    ):
        signals.append("valuation_multiple")
        return {"family_id": VALUATION, "confidence": 0.86, "signals": signals}

    # --- Evidence hierarchy ---
    if re.search(
        r"\b(providers?|sources?|brokers?|terminals?|notes?).{0,100}"
        r"(different|conflict|disagree|differ|p/?e|fair\s+value)|"
        r"(news|article|newspaper|wire|social\s+post|slides?|press\s+release|"
        r"channel\s+checks?|footnotes?).{0,100}"
        r"(filing|nse|bse|exchange|filings?|press\s+release|disagree|conflict)|"
        r"(no\s+(nse|bse|exchange)\s+filing)|(which\s+value\s+should).{0,40}trust|"
        r"(how\s+should\s+(this|aig|confidence)\s+be\s+(weighted|treat|set|respond))|"
        r"(unverified|no\s+exchange\s+(filing|disclosure|update))|"
        r"(footnotes?).{0,80}(press\s+release)|(press\s+release).{0,80}(footnotes?)|"
        r"which\s+prevails",
        ql,
    ):
        signals.append("source_conflict")
        return {"family_id": EVIDENCE, "confidence": 0.88, "signals": signals}

    # --- Comparison early when explicit peer framing is present ---
    if re.search(
        r"\b(two\s+companies|two\s+(saas|platforms|auto|chemicals|retailers|nbfc)|"
        r"company\s+a|firm\s+a|nbfc\s+a|which\s+is\s+stronger|which\s+looks\s+stronger|"
        r"identical\s+revenue\s+growth|same\s+revenue\s+growth|"
        r"both\s+\w+\s+companies|how\s+should\s+quality\s+be\s+compared|"
        r"what\s+else\s+is\s+(needed|required)\s+to\s+rank|"
        r"shallow\s+ranking|avoid\s+a\s+shallow)\b",
        ql,
    ):
        signals.append("peer_compare")
        return {"family_id": COMPARISON, "confidence": 0.86, "signals": signals}

    # --- Causality / macro (before comparison so "versus" sectors don't steal) ---
    if re.search(
        r"\b(rbi|central\s+bank|interest\s+rate|rate\s+cut|rate\s+hike|rate\s+pause|oil|crude|"
        r"inflation|bond\s+yields?|yields?|macro|rupee|monsoon|fiscal|"
        r"liquidity|shipping\s+costs?|credit\s+growth|carbon\s+tax|"
        r"employment|wage\s+growth|us\s+yields?|bank\s+stocks?)\b",
        ql,
    ) and (
        _ASK.search(ql)
        or re.search(
            r"\b(affect|impact|benefit|hurt|transmit|channel|implications?|"
            r"explanations?|exposed|sketch|differential)\b",
            ql,
        )
        or _has_conflict_directions(ql)
    ):
        signals.append("macro_causal")
        return {"family_id": CAUSALITY, "confidence": 0.85, "signals": signals}

    # --- Accounting / working capital / credit costs ---
    if re.search(
        r"\b(inventory|receivables|payable|vendor\s+advances?|working\s+capital|"
        r"free\s+cash\s+flow|fcf|operating\s+cash|cash\s+flow|cash\s+conversion|"
        r"provisions?|credit\s+costs?|slippage|write-?downs?|deferred\s+revenue|"
        r"warranty|capitalised|stock-based\s+compensation)\b",
        ql,
    ) and (
        _has_conflict_directions(ql)
        or _ASK.search(ql)
        or _CONFLICT.search(ql)
        or re.search(r"\b(after|alongside|while|combination)\b", ql)
    ):
        signals.append("accounting_bridge")
        return {"family_id": ACCOUNTING, "confidence": 0.84, "signals": signals}

    # Banking volume vs quality (deposits/CASA/loan growth) — contradiction family
    if re.search(
        r"\b(casa|deposit|loan\s+growth|advances|unsecured|priority-sector|"
        r"wholesale\s+deposits|retail\s+deposits|cost\s+of\s+funds|"
        r"net\s+interest\s+margin|nim)\b",
        ql,
    ) and (_has_conflict_directions(ql) or _ASK.search(ql) or _CONFLICT.search(ql)):
        signals.append("banking_quality_vs_volume")
        return {"family_id": CONTRADICTION, "confidence": 0.82, "signals": signals}

    # Production / order book / occupancy style ops contradictions → accounting if inventory-ish else contradiction
    if re.search(
        r"\b(production|output|order\s+book|capacity\s+utilisation|footfalls|"
        r"occupancy|throughput|volumes?|billings|take-rate|net\s+retention|"
        r"customer\s+growth|paid\s+users|same-store|deal\s+sizes)\b",
        ql,
    ) and (_has_conflict_directions(ql) or _ASK.search(ql) or _CONFLICT.search(ql)):
        if re.search(r"\b(inventory|receivables|cash|freight|payables)\b", ql):
            signals.append("ops_accounting")
            return {"family_id": ACCOUNTING, "confidence": 0.8, "signals": signals}
        signals.append("ops_contradiction")
        return {"family_id": CONTRADICTION, "confidence": 0.8, "signals": signals}

    # --- Comparison (company vs company — avoid bare "versus" alone) ---
    if re.search(
        r"\b(two\s+companies|two\s+(saas|platforms|auto|chemicals|retailers|nbfc)|"
        r"company\s+a|firm\s+a|which\s+is\s+stronger|which\s+looks\s+stronger|"
        r"identical\s+revenue\s+growth|same\s+revenue\s+growth|"
        r"both\s+\w+\s+companies|how\s+should\s+quality\s+be\s+compared|"
        r"what\s+else\s+is\s+(needed|required)\s+to\s+rank)\b",
        ql,
    ):
        signals.append("peer_compare")
        return {"family_id": COMPARISON, "confidence": 0.84, "signals": signals}

    # --- Contradiction (general opposing signals) ---
    if _has_conflict_directions(ql) or (
        _CONFLICT.search(ql) and _ASK.search(ql)
    ):
        signals.append("opposing_signals")
        conf = 0.8 if _has_conflict_directions(ql) else 0.7
        return {"family_id": CONTRADICTION, "confidence": conf, "signals": signals}

    # Soft catch-all for analytical finance prompts that still need a family habit.
    if _ASK.search(ql) and len(ql) >= 40:
        signals.append("soft_finance_ask")
        return {"family_id": CONTRADICTION, "confidence": 0.58, "signals": signals}

    return {"family_id": None, "confidence": 0.0, "signals": signals}


__all__ = ["classify_family"]
