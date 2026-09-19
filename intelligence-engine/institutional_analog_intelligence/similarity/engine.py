"""Deterministic similarity ranking for historical analogues."""

from __future__ import annotations

import re
from typing import Any

from institutional_analog_intelligence.schema import SIMILARITY_WEIGHTS


def score_similarity(
    memory: dict[str, Any],
    *,
    question: str,
    entities: list[str],
    industries: list[str],
    regimes: list[str],
    playbook_id: str | None,
    evidence_graph: dict[str, Any] | None,
    as_of: str | None,
) -> tuple[float, list[str]]:
    """Return (0–100 similarity, reason tags). Never invents features."""
    low = (question or "").lower()
    reasons: list[str] = []
    parts: dict[str, float] = {k: 0.0 for k in SIMILARITY_WEIGHTS}

    mem_entities = {str(x).upper() for x in (memory.get("entities") or [])}
    q_entities = {str(x).upper() for x in entities}
    if mem_entities & q_entities:
        parts["industry"] = 1.0
        parts["sector"] = 0.8
        reasons.append(f"entity_overlap:{','.join(sorted(mem_entities & q_entities)[:4])}")
    elif memory.get("industry") and memory.get("industry") in industries:
        parts["industry"] = 0.85
        parts["sector"] = 0.7
        reasons.append(f"industry:{memory.get('industry')}")

    # Cue matches (strong analog signal)
    cue_hits = 0
    for cue in memory.get("cues") or []:
        if _cue_hit(str(cue), low):
            cue_hits += 1
    if cue_hits:
        boost = min(1.0, 0.35 * cue_hits)
        parts["historical_behaviour"] = boost
        parts["corporate_event_type"] = max(parts["corporate_event_type"], min(1.0, 0.4 * cue_hits))
        reasons.append(f"cues:{cue_hits}")

    # Macro / policy regime overlap
    mem_regimes = {str(x) for x in (memory.get("macro_regime") or [])}
    if memory.get("market_regime"):
        mem_regimes.add(str(memory["market_regime"]))
    overlap_r = mem_regimes & set(regimes)
    if overlap_r:
        parts["macro_regime"] = min(1.0, 0.5 * len(overlap_r))
        parts["policy_regime"] = 0.6 if memory.get("policy_context") else 0.3
        reasons.append(f"regime:{','.join(sorted(overlap_r)[:3])}")

    # Commodity exposure via evidence graph chains / question
    mem_cmd = {str(x).lower() for x in (memory.get("commodity_exposure") or [])}
    eg_text = " ".join((evidence_graph or {}).get("chain_bullets") or []).lower()
    eg_ents = {str(x).lower() for x in ((evidence_graph or {}).get("entities") or [])}
    if mem_cmd and (mem_cmd & eg_ents or any(c in low or c in eg_text for c in mem_cmd)):
        parts["commodity_exposure"] = 0.9
        reasons.append("commodity_exposure")

    # Playbook alignment soft boost
    pb = (playbook_id or "").lower()
    mtype = str(memory.get("type") or "")
    if pb:
        if "rate" in pb and "rate" in mtype:
            parts["policy_regime"] = max(parts["policy_regime"], 0.7)
        if "premium" in pb and "premium" in " ".join(memory.get("cues") or []):
            parts["valuation_profile"] = 0.85
            reasons.append("playbook_valuation")
        if "results" in pb and mtype == "previous_earnings":
            parts["corporate_event_type"] = 0.9
            reasons.append("playbook_earnings")
        if "annual" in pb or "doc" in pb:
            pass
        if "bank" in pb and memory.get("valuation_profile") == "pb_roe":
            parts["valuation_profile"] = 0.9
            parts["financial_profile"] = 0.8
            reasons.append("playbook_bank_val")

    # Financial / valuation profile soft match via question language
    # Do not let bare "banks" inflate P/B·RI analogs on rate-transmission questions.
    # Avoid substring traps (e.g. "repo" inside "reports").
    rate_tx = any(
        _cue_hit(k, low)
        for k in (
            "rate cut",
            "rate cuts",
            "repo rate",
            "repo cut",
            "transmission",
            "basis point",
            "basis points",
            "nbfc",
            "easing",
            "rbi",
        )
    )
    if memory.get("valuation_profile") == "pb_roe" and any(
        k in low for k in ("p/b", "price to book", "residual income")
    ):
        parts["valuation_profile"] = max(parts["valuation_profile"], 0.85)
        parts["financial_profile"] = max(parts["financial_profile"], 0.7)
    elif (
        memory.get("valuation_profile") == "pb_roe"
        and "bank" in low
        and not rate_tx
    ):
        parts["valuation_profile"] = max(parts["valuation_profile"], 0.55)
        parts["financial_profile"] = max(parts["financial_profile"], 0.45)
    if memory.get("valuation_profile") == "quality_premium" and any(
        k in low for k in ("premium", "expensive", "quality")
    ):
        parts["valuation_profile"] = max(parts["valuation_profile"], 0.8)

    # Prefer rate-cycle memories when question is about cuts/hikes
    if rate_tx and mtype in {"previous_rate_cycle", "liquidity_cycle", "credit_cycle"}:
        parts["policy_regime"] = max(parts["policy_regime"], 0.95)
        parts["macro_regime"] = max(parts["macro_regime"], 0.85)
        parts["historical_behaviour"] = max(parts["historical_behaviour"], 0.7)
        reasons.append("rate_transmission_analog")

    # Risk profile
    if memory.get("risk_profile") and any(
        k in low for k in str(memory.get("risk_profile")).split("_")
    ):
        parts["risk_profile"] = 0.6

    # Time distance — prefer nearer history mildly; still allow deep history
    parts["time_distance"] = _time_distance_score(memory.get("available_from"), as_of)

    # Evidence quality from seed confidence
    conf = float(memory.get("confidence") or 0.5)
    parts["evidence_quality"] = max(0.0, min(1.0, conf))
    if memory.get("evidence_ids"):
        parts["evidence_quality"] = max(parts["evidence_quality"], 0.7)

    # Weighted total
    total = 0.0
    for k, w in SIMILARITY_WEIGHTS.items():
        total += w * float(parts.get(k) or 0.0)
    score = round(100.0 * total, 1)

    # Require some signal — cues or entity/industry/regime
    if score < 12 and cue_hits == 0 and not (mem_entities & q_entities) and not overlap_r:
        return 0.0, []

    return score, reasons


def _cue_hit(cue: str, question_low: str) -> bool:
    cue = (cue or "").strip().lower()
    if not cue:
        return False
    if " " in cue or "/" in cue or "-" in cue:
        return cue in question_low
    return re.search(rf"(?<![a-z0-9]){re.escape(cue)}(?![a-z0-9])", question_low) is not None


def _time_distance_score(available_from: str | None, as_of: str | None) -> float:
    if not available_from:
        return 0.4
    # Prefer memories whose period is not absurdly far if as_of present
    year = int(str(available_from)[:4]) if str(available_from)[:4].isdigit() else 2015
    ref = int(str(as_of)[:4]) if as_of and str(as_of)[:4].isdigit() else 2025
    dist = abs(ref - year)
    if dist <= 3:
        return 1.0
    if dist <= 7:
        return 0.75
    if dist <= 12:
        return 0.55
    return 0.35
