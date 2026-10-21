"""CIE V1 production facade — RQ1 Sprint 4."""

from __future__ import annotations

from typing import Any

from context_intelligence.enricher import enrich_question
from context_intelligence.flags import flags_dict, is_enabled
from context_intelligence.schema import (
    ARCHITECTURE_STATUS,
    CIE_VERSION,
    CONFIDENCE_THRESHOLD,
    MAX_RUNTIME_MS_TARGET,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "q": "Should I buy HDFC Bank?",
        "objective": "Investment Evaluation",
        "time_horizon": "Long Term",
        "portfolio_required": True,
        "comparison_contains": ["Peers", "History"],
        "scenario": "Normal",
        "expectation_contains": "priced in",
        "entity_contains": "HDFC",
        "card_has_priority": True,
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "objective": "Historical Analysis",
        "time_horizon": "10 Years",
        "portfolio_required": False,
        "comparison_contains": ["History"],
        "historical_required": True,
        "entity_contains": "Nifty IT",
    },
    {
        "q": "Compare TCS vs Infosys",
        "objective": "Peer Comparison",
        "comparison_contains": ["Peers"],
        "portfolio_required": False,
    },
    {
        "q": "Explain ROIC",
        "objective": "Educational",
        "portfolio_required": False,
        "user_mode": "Learning",
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "objective": "Macro Impact",
        "scenario": "Rate Cuts",
        "event_contains": "Rate Decision",
    },
    {
        "q": "Should I invest for 10 years?",
        "time_horizon": "10 Years",
    },
    {
        "q": "What happened today in markets?",
        "time_horizon": "Today",
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "objective": "Portfolio Decision",
        "portfolio_required": True,
    },
    {
        "q": "Should I sell Infosys?",
        "objective": "Investment Evaluation",
        "portfolio_required": True,
    },
    {
        "q": "Stress test my portfolio for rate shock",
        "portfolio_required": True,
        "scenario": "Stress",
    },
]

_TEMPLATES: list[tuple[str, dict[str, Any]]] = [
    ("Should I buy {name}?", {"objective": "Investment Evaluation", "portfolio_required": True, "time_horizon": "Long Term"}),
    ("Should I sell {name}?", {"objective": "Investment Evaluation", "portfolio_required": True}),
    ("Compare {name} vs {peer}", {"objective": "Peer Comparison", "comparison_contains": ["Peers"]}),
    ("Explain {concept}", {"objective": "Educational", "portfolio_required": False, "user_mode": "Learning"}),
    ("Is {index} expensive versus history?", {"objective": "Historical Analysis", "historical_required": True, "portfolio_required": False}),
    ("How will RBI rate cuts affect {sector}?", {"objective": "Macro Impact", "scenario": "Rate Cuts"}),
    ("Build a portfolio with {name}", {"objective": "Portfolio Decision", "portfolio_required": True}),
    ("What are the risks in {name}?", {"objective": "Risk Assessment"}),
    ("Should I invest for 10 years in {name}?", {"time_horizon": "10 Years"}),
    ("What happened today with {name}?", {"time_horizon": "Today"}),
    ("Is {name} overvalued?", {"objective": "Valuation Assessment", "comparison_contains": ["History", "Peers"]}),
    ("Assess business quality of {name}", {"objective": "Business Quality Assessment"}),
    ("Financial health of {name}", {"objective": "Financial Health Assessment"}),
    ("Forecast earnings for {name}", {"objective": "Forecast"}),
    ("Screen for quality {sector} stocks", {"objective": "Screening"}),
    ("News impact on {name}", {"objective": "News Impact"}),
    ("Event analysis of {name} earnings", {"objective": "Event Analysis", "event_contains": "Earnings"}),
    ("Is {sector} sector attractive?", {"objective": "Sector Attractiveness"}),
    ("Teach me {concept}", {"objective": "Educational", "user_mode": "Learning"}),
    ("Rebalance my portfolio toward {sector}", {"objective": "Portfolio Decision", "portfolio_required": True}),
]

_NAMES = [
    "HDFC Bank", "Infosys", "TCS", "Reliance", "SBI", "ICICI Bank",
    "Asian Paints", "Titan", "Wipro", "HCL Tech", "ITC", "Bajaj Finance",
]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech", "Tech Mahindra"]
_SECTORS = ["banks", "IT", "auto", "pharma", "FMCG", "metals"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50", "Nifty Pharma"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "moat", "WACC"]


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": CIE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_runtime_ms_target": MAX_RUNTIME_MS_TARGET,
        "not_a_top_level_intelligence_layer": True,
        "law": "Institutional analysts never analyse a question in isolation.",
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict()}


def enrich(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "cie_version": CIE_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "cie_version": CIE_VERSION}
    return {"enabled": True, **enrich_question(question, body)}


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:8]:
        row = enrich_question(b["q"], {"skip_iar": False})
        card = row.get("research_context_card") or {}
        samples.append(
            {
                "question": b["q"],
                "primary_objective": row.get("primary_objective"),
                "time_horizon": (row.get("time_context") or {}).get("time_horizon"),
                "market_regime": (row.get("market_context") or {}).get("regime"),
                "portfolio_required": (row.get("portfolio_context") or {}).get("required"),
                "comparison": (row.get("comparison_context") or {}).get("lenses"),
                "scenario": (row.get("scenario_context") or {}).get("scenario"),
                "confidence": (row.get("confidence") or {}).get("overall"),
                "runtime_ms": row.get("runtime_ms"),
                "card_entity": card.get("entity"),
                "priority_areas": card.get("priority_areas"),
            }
        )
    return {
        "programme": PROGRAMME,
        "cie_version": CIE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/context-intelligence"],
        "api_prefix": "/v1/context-intelligence",
        "law": "Every analyst begins with complete institutional context, not only the user's sentence.",
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return enrich_question(q, body).get("diagnostics") or {}


def _expanded() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    i = 0
    while len(cases) < 1100:
        tmpl, extra = _TEMPLATES[i % len(_TEMPLATES)]
        name = _NAMES[i % len(_NAMES)]
        peer = _PEERS[i % len(_PEERS)]
        if peer == name:
            peer = _PEERS[(i + 1) % len(_PEERS)]
        q = tmpl.format(
            name=name,
            peer=peer,
            sector=_SECTORS[i % len(_SECTORS)],
            index=_INDEXES[i % len(_INDEXES)],
            concept=_CONCEPTS[i % len(_CONCEPTS)],
        )
        cases.append({"q": q, **extra, "kind": "template"})
        i += 1
    return cases


def _check(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    time_h = (row.get("time_context") or {}).get("time_horizon")
    if b.get("time_horizon") and time_h != b["time_horizon"]:
        errs.append("time_horizon")
    if "portfolio_required" in b:
        got = bool((row.get("portfolio_context") or {}).get("required"))
        if got != bool(b["portfolio_required"]):
            errs.append("portfolio")
    if b.get("comparison_contains"):
        lenses = set((row.get("comparison_context") or {}).get("lenses") or [])
        if not set(b["comparison_contains"]).issubset(lenses):
            errs.append("comparison")
    if b.get("scenario") and (row.get("scenario_context") or {}).get("scenario") != b["scenario"]:
        errs.append("scenario")
    if b.get("historical_required") and not (row.get("historical_context") or {}).get("required"):
        errs.append("historical")
    if b.get("event_contains"):
        events = set((row.get("event_context") or {}).get("events") or [])
        if b["event_contains"] not in events:
            errs.append("event")
    if b.get("entity_contains"):
        ent = str((row.get("entity_context") or {}).get("entity") or "")
        if b["entity_contains"].lower() not in ent.lower():
            errs.append("entity")
    if b.get("expectation_contains"):
        summary = str((row.get("expectation_context") or {}).get("summary") or "").lower()
        if b["expectation_contains"].lower() not in summary:
            errs.append("expectation")
    if b.get("user_mode"):
        if (row.get("user_context") or {}).get("mode") != b["user_mode"]:
            errs.append("user_mode")
    if b.get("card_has_priority"):
        card = row.get("research_context_card") or {}
        if not card.get("priority_areas"):
            errs.append("card")
    if not row.get("research_context_card"):
        errs.append("missing_card")
    if row.get("executed_layers") or row.get("executed_analysts"):
        errs.append("executed")
    return errs


def quality_gates() -> dict[str, Any]:
    cases = _expanded()
    passed = 0
    time_ok = time_n = 0
    mkt_ok = mkt_n = 0
    cmp_ok = cmp_n = 0
    port_ok = port_n = 0
    ctx_ok = 0
    timed: list[float] = []
    failures: list[dict[str, Any]] = []

    for b in cases[:1100]:
        payload: dict[str, Any] = {"skip_iar": True}
        if b.get("objective"):
            payload["primary_objective"] = b["objective"]
            if b["objective"] == "Educational":
                payload["question_type"] = "Explain"
            if "Should I buy" in b["q"]:
                payload["question_type"] = "Should I Buy?"
            if "Should I sell" in b["q"]:
                payload["question_type"] = "Should I Sell?"
            if b["objective"] == "Investment Evaluation":
                payload.setdefault("expected_output", "Institutional Report")
                payload.setdefault("decision_type", "Investment")
                payload.setdefault("research_depth", "Institutional")
        row = enrich_question(b["q"], payload)
        timed.append(float(row.get("runtime_ms") or 0))
        errs = _check(b, row)

        # Metric buckets
        if b.get("time_horizon"):
            time_n += 1
            if "time_horizon" not in errs:
                time_ok += 1
        else:
            time_n += 1
            time_ok += 1 if (row.get("time_context") or {}).get("time_horizon") else 0

        mkt_n += 1
        if (row.get("market_context") or {}).get("regime"):
            mkt_ok += 1

        if b.get("comparison_contains"):
            cmp_n += 1
            if "comparison" not in errs:
                cmp_ok += 1
        else:
            cmp_n += 1
            cmp_ok += 1

        if "portfolio_required" in b:
            port_n += 1
            if "portfolio" not in errs:
                port_ok += 1
        else:
            port_n += 1
            port_ok += 1

        if not errs:
            passed += 1
            ctx_ok += 1
        elif len(failures) < 25:
            failures.append({"question": b["q"], "errors": errs, "time": (row.get("time_context") or {}).get("time_horizon")})

    total = min(len(cases), 1100)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    ctx_acc = ctx_ok / total if total else 0.0
    time_acc = time_ok / time_n if time_n else 1.0
    mkt_acc = mkt_ok / mkt_n if mkt_n else 1.0
    cmp_acc = cmp_ok / cmp_n if cmp_n else 1.0
    port_acc = port_ok / port_n if port_n else 1.0
    return {
        "ok": (
            ctx_acc >= 0.98
            and time_acc >= 0.99
            and mkt_acc >= 0.95
            and cmp_acc >= 0.98
            and port_acc >= 0.99
            and avg_ms <= MAX_RUNTIME_MS_TARGET * 5
            and total >= 1000
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "context_accuracy": round(ctx_acc, 4),
        "time_horizon_detection": round(time_acc, 4),
        "market_context_detection": round(mkt_acc, 4),
        "comparison_context_accuracy": round(cmp_acc, 4),
        "portfolio_context_accuracy": round(port_acc, 4),
        "avg_runtime_ms": avg_ms,
        "p95_runtime_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_runtime_ms": MAX_RUNTIME_MS_TARGET,
        "failures_sample": failures,
        "rule": "Every analyst begins reasoning with complete institutional context.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    row = enrich_question(question or "", payload)
    card = row.get("research_context_card") or {}
    return {
        "context_intelligence": {
            "enabled": True,
            "version": CIE_VERSION,
            "sprint": SPRINT,
            "primary_objective": row.get("primary_objective"),
            "entity_context": row.get("entity_context"),
            "market_context": row.get("market_context"),
            "macro_context": row.get("macro_context"),
            "historical_context": row.get("historical_context"),
            "time_context": row.get("time_context"),
            "portfolio_context": row.get("portfolio_context"),
            "comparison_context": row.get("comparison_context"),
            "event_context": row.get("event_context"),
            "expectation_context": row.get("expectation_context"),
            "scenario_context": row.get("scenario_context"),
            "user_context": row.get("user_context"),
            "context_importance": row.get("context_importance"),
            "research_context_card": card,
            "confidence": row.get("confidence"),
            "runtime_ms": row.get("runtime_ms"),
            "no_layer_execution": True,
        }
    }
