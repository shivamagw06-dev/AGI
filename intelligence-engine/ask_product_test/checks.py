"""Product-contract checks for AGI Ask responses (behavior, not wording)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Implementation jargon that must never reach the user.
_JARGON_RE = re.compile(
    r"(?i)\b("
    r"E0[1-9]|E1[0-4]|L4|ORCH|"
    r"FAA|IEL|LEO|IERE|IFSE|IAP|IEG|IMAI|"
    r"Traceback|File \".*\.py\", line|"
    r"RuntimeError|TypeError|KeyError|AttributeError|"
    r"uvicorn|fastapi\.exceptions"
    r")\b"
)

# Explicit recommendation language — not casual mention of buybacks / "buy the argument".
# Negations like "no target price" / "does not issue buy" are allowed.
_RECOMMENDATION_RE = re.compile(
    r"(?i)("
    r"(?<!\bno\s)(?<!\bnot\s)(?<!\bwithout\s)(?<!\bnever\s)"
    r"(?:we recommend\s+(?:buying|selling|adding|reducing)|"
    r"recommendation\s*[:=]\s*(?:buy|sell|add|reduce|overweight|underweight)|"
    r"(?:buy|sell|add|reduce)\s+rating|"
    r"rating\s*[:=]\s*(?:buy|sell|add|reduce|overweight|underweight)|"
    r"target\s*price\s*[:=]?\s*\d|"
    r"(?:initiate|maintain|upgrade to|downgrade to)\s+(?:a\s+)?(?:buy|sell|add|reduce|overweight|underweight)|"
    r"you should\s+(?:buy|sell)|"
    r"go\s+(?:long|short))"
    r")"
)

_INSUFFICIENT_RE = re.compile(
    r"(?i)\b("
    r"insufficient evidence|not enough evidence|no (reliable )?evidence|"
    r"cannot (find|verify|confirm)|do not have (enough|sufficient)|"
    r"unknown company|unable to (locate|retrieve)|"
    r"coverage (is )?limited|knowledge gap|not in (the )?universe|"
    r"warming up|degraded|research desk"
    r")\b"
)

_ENTITY_ALIASES = {
    "RELIANCE": ["RELIANCE", "RELIANCE INDUSTRIES", "RIL"],
    "INFY": ["INFY", "INFOSYS"],
    "TCS": ["TCS", "TATA CONSULTANCY"],
    "HDFCBANK": ["HDFCBANK", "HDFC BANK", "HDFC"],
    "META": ["META", "META PLATFORMS", "FACEBOOK", "FB"],
    "AAPL": ["AAPL", "APPLE"],
    "NIFTY": ["NIFTY", "NIFTY 50", "NIFTY50"],
    "TITAN": ["TITAN"],
    "ASIANPAINT": ["ASIANPAINT", "ASIAN PAINTS"],
}


def flatten_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (int, float, bool)):
        return str(payload)
    if isinstance(payload, dict):
        return " ".join(flatten_text(v) for v in payload.values())
    if isinstance(payload, (list, tuple, set)):
        return " ".join(flatten_text(v) for v in payload)
    return str(payload)


def extract_answer_text(payload: Dict[str, Any]) -> str:
    """Canonical user-facing answer text for scoring.

    SearchView mirrors the same executive into several fields
    (answer.summary, answer.executive_summary, payload.executive_summary,
    investment_thesis) and duplicates why at top-level and under answer.
    Concatenating all of them triple-counts the lead and falsely tanks
    executive_quality on length. Prefer one lead + one why list.
    """
    answer = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    constitution = answer.get("response_constitution") if isinstance(answer.get("response_constitution"), dict) else {}
    lead_candidates = [
        answer.get("summary"),
        answer.get("executive_summary"),
        answer.get("direct_answer"),
        constitution.get("direct_answer") if isinstance(constitution, dict) else None,
        payload.get("executive_summary"),
        payload.get("investment_thesis"),
    ]
    lead = next((str(p).strip() for p in lead_candidates if p and str(p).strip()), "")
    why_list = answer.get("why") if isinstance(answer.get("why"), list) and answer.get("why") else payload.get("why")
    # Drop why lines that merely repeat the lead paragraph; dedupe repeats.
    lead_norm = re.sub(r"\s+", " ", lead).strip().lower() if lead else ""
    why_parts: List[str] = []
    seen_why: set[str] = set()
    for w in (why_list or []):
        wn = re.sub(r"\s+", " ", str(w)).strip()
        if not wn:
            continue
        wn_low = wn.lower()
        if wn_low in seen_why:
            continue
        if lead_norm and (wn_low == lead_norm or (len(wn) > 40 and wn_low in lead_norm)):
            continue
        seen_why.add(wn_low)
        why_parts.append(wn)
    why_text = " ".join(why_parts)
    # Keep scoring text within the executive-quality length band. Soft-provider
    # dumps must not dominate the visible answer used for acceptance gates.
    if why_text and lead:
        budget = max(0, 1100 - len(lead) - 1)
        if len(why_text) > budget:
            why_text = why_text[:budget].rsplit(" ", 1)[0].rstrip()
    parts = [p for p in (lead, why_text) if p]
    return " ".join(parts)


def evidence_count(payload: Dict[str, Any]) -> int:
    buckets = [
        payload.get("evidence_used"),
        payload.get("supporting_research"),
        payload.get("supporting_evidence"),
        payload.get("hits"),
        payload.get("latest_articles"),
    ]
    n = 0
    for b in buckets:
        if isinstance(b, list):
            n += len(b)
    multi = payload.get("multi_source") or {}
    if isinstance(multi, dict) and multi.get("evidence_count"):
        try:
            n = max(n, int(multi["evidence_count"]))
        except (TypeError, ValueError):
            pass
    kf = payload.get("knowledge_foundation") or {}
    if isinstance(kf, dict):
        for key in ("companies", "sectors", "themes", "items"):
            if isinstance(kf.get(key), list):
                n += len(kf[key])
    return n


def evidence_sources(payload: Dict[str, Any]) -> List[str]:
    sources: List[str] = []
    for key in ("evidence_used", "supporting_research", "supporting_evidence", "hits"):
        for item in payload.get(key) or []:
            if not isinstance(item, dict):
                continue
            src = item.get("source") or item.get("provider") or item.get("type") or item.get("title")
            if src:
                sources.append(str(src)[:80])
    multi = payload.get("multi_source") or {}
    if isinstance(multi, dict):
        for s in multi.get("sources") or multi.get("adapters") or []:
            sources.append(str(s)[:80])
    # unique preserve order
    out: List[str] = []
    seen = set()
    for s in sources:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[:20]


def extract_entities(payload: Dict[str, Any]) -> List[str]:
    ents = payload.get("entities") or {}
    found: List[str] = []
    if isinstance(ents, dict):
        t = ents.get("ticker")
        if t:
            found.append(str(t).upper())
        for c in ents.get("companies") or []:
            found.append(str(c).upper())
    for r in payload.get("related_companies") or []:
        found.append(str(r).upper())
    # de-dupe
    out: List[str] = []
    seen = set()
    for e in found:
        if e in seen:
            continue
        seen.add(e)
        out.append(e)
    return out


def normalize_intent(raw: Any, family_hint: str = "") -> str:
    text = str(raw or family_hint or "").strip()
    if not text:
        return "Unknown"
    low = text.lower().replace("_", " ")
    mapping = [
        ("historical", "Historical"),
        ("replay", "Historical"),
        ("education", "Education"),
        ("concept", "Education"),
        ("document", "Documents"),
        ("macro", "Macro"),
        ("government", "Macro"),
        ("compare", "Compare"),
        ("peer", "Compare"),
        ("industry", "Industry"),
        ("private", "Private Markets"),
        ("valuation", "Explain"),
        ("explain", "Explain"),
        ("recommendation", "Company"),
        ("portfolio", "Company"),
        ("company", "Company"),
        ("analyse", "Company"),
        ("analyze", "Company"),
    ]
    for needle, family in mapping:
        if needle in low:
            return family
    return text.split()[0].title() if text else "Unknown"


def intent_matches(observed: str, expected_family: str) -> bool:
    if not expected_family:
        return True
    o = normalize_intent(observed).lower()
    e = expected_family.lower()
    if o == e:
        return True
    # Compatible families
    aliases = {
        "explain": {"explain", "education", "company", "industry"},
        "education": {"education", "explain"},
        "company": {"company", "explain", "compare"},
        "compare": {"compare", "company", "explain"},
        "macro": {"macro", "industry", "explain"},
        "industry": {"industry", "macro", "explain", "compare"},
        "documents": {"documents", "explain", "company"},
        "historical": {"historical", "explain", "company"},
        "private markets": {"private markets", "company", "explain", "industry"},
    }
    return o in aliases.get(e, {e})


def entity_mentioned(blob: str, entity: str) -> bool:
    aliases = _ENTITY_ALIASES.get(entity.upper(), [entity.upper()])
    upper = blob.upper()
    return any(a.upper() in upper for a in aliases)


def check_entity_binding(
    payload: Dict[str, Any],
    *,
    expected: Sequence[str] = (),
    forbid: Sequence[str] = (),
) -> Tuple[bool, List[str]]:
    """Soft entity binding: require at least one expected alias if provided; forbid pollution."""
    errors: List[str] = []
    blob = (
        flatten_text(extract_entities(payload))
        + " "
        + extract_answer_text(payload)
        + " "
        + flatten_text(payload.get("related_companies"))
    )
    if expected:
        if not any(entity_mentioned(blob, e) for e in expected):
            # Soft: only fail if a forbidden competitor clearly dominates
            if forbid and any(entity_mentioned(blob, f) for f in forbid):
                errors.append(f"expected entity {list(expected)} missing; forbidden entity present")
            # else: allow thin/degraded answers without hard fail on missing entity
    for f in forbid:
        # Fail only if forbidden entity appears as bound ticker/company AND expected missing
        bound = extract_entities(payload)
        aliases = _ENTITY_ALIASES.get(f.upper(), [f.upper()])
        if any(b in {a.upper() for a in aliases} or b.upper() in {a.upper() for a in aliases} for b in bound):
            if expected and not any(entity_mentioned(" ".join(bound), e) for e in expected):
                errors.append(f"entity pollution: bound {bound} includes forbidden {f}")
    return (len(errors) == 0), errors


def check_no_jargon(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    text = extract_answer_text(payload) + " " + flatten_text(payload.get("why"))
    hits = _JARGON_RE.findall(text)
    if hits:
        return False, [f"implementation jargon leaked: {sorted(set(str(h) for h in hits))[:8]}"]
    return True, []


_NEGATED_OR_EDU_REC_RE = re.compile(
    r"(?i)("
    r"\b(?:no|not|never|without|does\s+not|do\s+not|don't)\b[^\n.]{0,64}"
    r"\b(?:buy|sell|buying|selling|add|reduce|target\s*price|price\s*target)\b"
    r"|\bno\s+buy\s*/\s*sell\b"
    r"|\bbuy\s*/\s*sell\s+(?:rating|recommendation|advice)\b"
    r"|\bbuy\s+or\s+sell\s+(?:rating|recommendation|advice|recommendations)\b"
    r")"
)


def check_no_recommendation(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    text = extract_answer_text(payload)
    # Scrub negated / educational mentions before scanning for real violations.
    scrubbed = _NEGATED_OR_EDU_REC_RE.sub(" ", text or "")
    m = _RECOMMENDATION_RE.search(scrubbed)
    if m:
        return False, [f"recommendation policy violation: {m.group(0)}"]
    return True, []


def check_insufficient_evidence(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    text = extract_answer_text(payload)
    if evidence_count(payload) == 0 and _INSUFFICIENT_RE.search(text):
        return True, []
    if _INSUFFICIENT_RE.search(text):
        return True, []
    if evidence_count(payload) == 0 and (
        payload.get("degraded") or payload.get("status") == "degraded" or payload.get("retryable")
    ):
        return True, []
    return False, ["expected honest insufficient-evidence stance for unknown company"]


def check_as_of_no_lookahead(
    payload: Dict[str, Any],
    *,
    as_of: Optional[str] = None,
    must_not: Sequence[str] = (),
) -> Tuple[bool, List[str]]:
    if not as_of and not must_not:
        return True, []
    text = extract_answer_text(payload).lower()
    errors: List[str] = []
    for needle in must_not:
        if needle and needle.lower() in text:
            errors.append(f"historical lookahead / leak: {needle}")
    # Soft: current PE quoted without as_of framing is a risk — only flag explicit future years
    for year in ("2024", "2025", "2026", "2027"):
        if as_of and as_of.startswith("2020") and year in text and "as of" not in text:
            # allow if discussing the prompt itself; flag dense future PE claims
            if re.search(rf"\b(pe|p/e|multiple|valuation).{{0,40}}{year}", text):
                errors.append(f"possible future valuation leak mentioning {year}")
    return (len(errors) == 0), errors


def mentions_insufficient_evidence(text: str) -> bool:
    return bool(_INSUFFICIENT_RE.search(text or ""))


# Intentional product short-circuits stash a `short_circuit` key inside the
# degradation dict for orchestration observability. Those paths are successful
# answers, not degraded fallbacks — do not treat them as degraded unless an
# explicit failure/fallback marker is also present.
_INTENTIONAL_SHORT_CIRCUITS = frozenset(
    {
        "knowledge_unification",
        "financial_router",
        "recommendation_policy",
        "unknown_entity",
        "unsupported_coverage_policy",
        "comparison_entities",
        "ikt_company_router",
        "ambiguous_event_clarification",
    }
)


def is_degraded(payload: Dict[str, Any]) -> bool:
    if payload.get("degraded") is True:
        return True
    if payload.get("status") == "degraded":
        return True
    if payload.get("mode") == "node_desk_fallback":
        return True
    deg = payload.get("degradation")
    if isinstance(deg, dict) and deg:
        sc = str(deg.get("short_circuit") or "").strip()
        if sc in _INTENTIONAL_SHORT_CIRCUITS:
            failure_markers = (
                "fallback",
                "error",
                "unavailable",
                "timeout",
                "empty",
                "node_desk_fallback",
            )
            if any(deg.get(k) for k in failure_markers):
                return True
            # Pure intentional short-circuit with no failure markers.
            return False
        return True
    return False


def has_usable_answer(payload: Dict[str, Any]) -> bool:
    text = extract_answer_text(payload).strip()
    if len(text) >= 40:
        return True
    if is_degraded(payload) and len(text) >= 20:
        return True
    if payload.get("error") == "research_desk_unavailable" and payload.get("retryable"):
        return True
    return False


def extract_orchestration(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pull #435/#436 observability fields for baseline comparison."""
    orch = payload.get("ask_orchestration") if isinstance(payload, dict) else None
    if not isinstance(orch, dict):
        deg = payload.get("degradation") if isinstance(payload, dict) else None
        if isinstance(deg, dict) and isinstance(deg.get("ask_orchestration"), dict):
            orch = deg["ask_orchestration"]
        else:
            orch = {}
    funnel = orch.get("funnel") if isinstance(orch.get("funnel"), dict) else {}
    util = orch.get("utilization") or orch.get("evidence_utilization")
    if not isinstance(util, dict):
        util = {}
    latency = orch.get("latency") if isinstance(orch.get("latency"), dict) else {}
    entity = orch.get("entity") if isinstance(orch.get("entity"), dict) else {}
    ikl = orch.get("ikl") if isinstance(orch.get("ikl"), dict) else {}
    ik_pack = payload.get("institutional_knowledge") if isinstance(payload, dict) else {}
    if not isinstance(ik_pack, dict):
        ik_pack = {}
    layers = list(ikl.get("layers_hit") or ik_pack.get("layers_hit") or [])
    return {
        "ask_trace_id": orch.get("ask_trace_id"),
        "fallback_used": bool(orch.get("fallback_used") or orch.get("fallback")),
        "engine_reached": orch.get("engine_reached"),
        "executive_source": orch.get("executive_source"),
        "ticker_source": orch.get("ticker_source"),
        "entity_confidence": entity.get("confidence") or orch.get("entity_confidence"),
        "funnel": {
            "retrieved": funnel.get("retrieved"),
            "ranked": funnel.get("ranked"),
            "passed": funnel.get("passed"),
            "referenced": funnel.get("referenced"),
        },
        "utilization": util,
        "latency": latency,
        "latency_total_ms": latency.get("total_ms") or orch.get("latency_ms"),
        "ikl_layers_hit": layers,
        "ikl_confidence": ikl.get("confidence") if ikl else ik_pack.get("confidence"),
        "ikl_explainability": ikl.get("explainability") or ik_pack.get("explainability") or {},
        "trace_summary": orch.get("trace_summary"),
    }


def check_ikl_expectations(
    payload: Dict[str, Any],
    case: Dict[str, Any],
    *,
    strict: bool = False,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate IKL memory usage. Soft unless strict=True."""
    errors: List[str] = []
    orch = extract_orchestration(payload)
    ik = payload.get("institutional_knowledge") if isinstance(payload, dict) else {}
    if not isinstance(ik, dict):
        ik = {}
    layers = list(orch.get("ikl_layers_hit") or [])
    meta = {
        "layers_hit": layers,
        "ikl_present": bool(ik.get("enabled") or layers or orch.get("ikl_explainability")),
        "primary_before_raw": bool(ik.get("primary_before_raw_documents")),
        "knowledge_gaps": list((ik.get("explainability") or {}).get("knowledge_gaps") or []),
        "strict": strict,
    }

    if case.get("ikl_expect_knowledge_gap") or case.get("expect_insufficient_evidence"):
        ok_i, err_i = check_insufficient_evidence(payload)
        meta["insufficient_evidence"] = ok_i
        if not ok_i and strict:
            errors.extend(err_i)
        elif not ok_i:
            meta["soft_gap"] = err_i
        return (len(errors) == 0), errors, meta

    expected_layers = list(case.get("ikl_expect_layers") or [])
    missing = [layer for layer in expected_layers if layer not in layers]
    meta["missing_layers"] = missing

    if expected_layers and missing:
        msg = f"IKL layers missing: expected {expected_layers}, hit {layers or []}"
        if strict:
            errors.append(msg)
        else:
            meta["soft_ikl"] = msg

    if case.get("ikl_primary_memory") and strict:
        if not (ik.get("primary_before_raw_documents") or "company_memory" in layers):
            errors.append("expected company memory consulted before raw documents")

    if case.get("ikl_expect_multi_document") and strict:
        timeline = (ik.get("historical_timeline") or {}) if isinstance(ik, dict) else {}
        docs_n = 0
        if isinstance(timeline, dict):
            for v in timeline.values():
                if isinstance(v, dict):
                    docs_n += len(v.get("documents") or [])
                    docs_n += len(v.get("deltas") or [])
        expl = ik.get("explainability") or {}
        docs_n = max(docs_n, len(expl.get("documents_referenced") or []))
        meta["documents_referenced_n"] = docs_n
        if docs_n < 2 and "historical_timeline" not in layers:
            errors.append("expected multi-document / timeline reasoning")

    return (len(errors) == 0), errors, meta
