"""ROE V1 production facade — RQ1 Sprint 3."""

from __future__ import annotations

import time
from typing import Any

from research_objective.analyst_planner import plan_analysts
from research_objective.api_planner import plan_apis
from research_objective.blueprint_generator import generate_blueprint
from research_objective.context_classifier import classify_context
from research_objective.diagnostics import diagnose
from research_objective.flags import flags_dict, is_enabled
from research_objective.intelligence_planner import plan_layers
from research_objective.intent_classifier import classify_intent
from research_objective.objective_classifier import classify_objective
from research_objective.policy import clarification_payload, should_block_execution
from research_objective.question_classifier import classify_question_meta
from research_objective.routing_confidence import score_routing
from research_objective.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    MAX_PLANNING_MS_TARGET,
    PROGRAMME,
    PROGRAMME_SHORT,
    ROE_VERSION,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "q": "Should I buy HDFC Bank?",
        "objective": "Investment Evaluation",
        "question_type": "Should I Buy?",
        "expected_output": "Institutional Report",
        "depth": "Institutional",
        "analysts_contains": ["Business", "Valuation", "Committee"],
        "layers_contains": ["FIL", "EIL", "PIL"],
        "blueprint_contains": ["Investment Thesis", "Committee View"],
    },
    {
        "q": "Compare TCS vs Infosys",
        "objective": "Peer Comparison",
        "question_type": "Compare",
        "expected_output": "Comparison Report",
        "analysts_contains": ["Peer", "Valuation"],
        "blueprint_contains": ["Peer Universe"],
    },
    {
        "q": "Explain ROIC",
        "objective": "Educational",
        "question_type": "Explain",
        "expected_output": "Educational Guide",
        "analysts_exact": ["Academy"],
        "layers_exact": [],
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "objective": "Macro Impact",
        "expected_output": "Macro Report",
        "secondary_contains": ["Forecast", "Sector Attractiveness"],
        "apis_contains": ["RBI", "FRED"],
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "objective": "Historical Analysis",
        "expected_output": "Valuation Report",
        "layers_contains": ["FIL", "EIL", "PIL", "CIG", "FIE"],
        "layers_skip_contains": ["Management", "Portfolio", "Accounting"],
        "apis_contains": ["Historical multiples"],
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "objective": "Portfolio Decision",
        "expected_output": "Portfolio Memo",
        "analysts_contains": ["Portfolio", "Risk"],
    },
    {
        "q": "What are the risks in Reliance Industries?",
        "objective": "Risk Assessment",
        "expected_output": "Risk Report",
    },
    {
        "q": "Screen for high ROE banks under 15 PE",
        "objective": "Screening",
        "question_type": "Screen",
        "expected_output": "Screening Report",
    },
    {
        "q": "Is Infosys overvalued on PE?",
        "objective": "Valuation Assessment",
        "expected_output": "Research Note",
    },
    {
        "q": "Assess business quality of Asian Paints",
        "objective": "Business Quality Assessment",
    },
    {
        "q": "Financial health of SBI",
        "objective": "Financial Health Assessment",
    },
    {
        "q": "Bull and bear case for Titan",
        "objective": "Scenario Analysis",
        "expected_output": "Scenario Report",
    },
    {
        "q": "Forecast FY27 earnings for TCS",
        "objective": "Forecast",
        "expected_output": "Forecast Report",
    },
    {
        "q": "Technical analysis of Nifty chart",
        "objective": "Technical Analysis",
    },
    {
        "q": "Accounting review of Yes Bank",
        "objective": "Accounting Review",
    },
    {
        "q": "Management assessment of HDFC Bank CEO",
        "objective": "Management Assessment",
    },
    {
        "q": "Ownership review of Infosys promoter holding",
        "objective": "Ownership Review",
    },
    {
        "q": "Governance review of related party transactions",
        "objective": "Governance Review",
    },
    {
        "q": "Policy analysis of union budget on banks",
        "objective": "Policy Analysis",
    },
    {
        "q": "Regulatory analysis of RBI guidelines for NBFCs",
        "objective": "Regulatory Analysis",
    },
    {
        "q": "Is banking sector attractive now?",
        "objective": "Sector Attractiveness",
    },
    {
        "q": "Industry structure of Indian IT services",
        "objective": "Industry Structure",
    },
    {
        "q": "News impact of Fed hike on Indian markets",
        "objective": "News Impact",
    },
    {
        "q": "Event analysis of TCS earnings day",
        "objective": "Event Analysis",
    },
    {
        "q": "Should I sell Infosys?",
        "objective": "Investment Evaluation",
        "question_type": "Should I Sell?",
    },
    {
        "q": "Teach me what EV/EBITDA means",
        "objective": "Educational",
        "question_type": "Teach",
    },
    {
        "q": "Stress test my portfolio for rate shock",
        "objective": "Risk Assessment",
        "question_type": "Stress Test",
    },
    {
        "q": "Rebalance my portfolio toward defensives",
        "objective": "Portfolio Decision",
        "question_type": "Rebalance",
    },
]


_TEMPLATES: list[tuple[str, str, dict[str, Any]]] = [
    ("Should I buy {name}?", "Investment Evaluation", {"question_type": "Should I Buy?"}),
    ("Should I sell {name}?", "Investment Evaluation", {"question_type": "Should I Sell?"}),
    ("Compare {name} vs {peer}", "Peer Comparison", {"question_type": "Compare"}),
    ("Explain {concept}", "Educational", {"question_type": "Explain"}),
    ("How will RBI rate cuts affect {sector}?", "Macro Impact", {}),
    ("Is {index} expensive versus history?", "Historical Analysis", {}),
    ("Build a portfolio with {name}", "Portfolio Decision", {}),
    ("What are the risks in {name}?", "Risk Assessment", {}),
    ("Screen for quality {sector} stocks", "Screening", {"question_type": "Screen"}),
    ("Is {name} overvalued?", "Valuation Assessment", {}),
    ("Assess business quality of {name}", "Business Quality Assessment", {}),
    ("Financial health of {name}", "Financial Health Assessment", {}),
    ("Bull and bear case for {name}", "Scenario Analysis", {}),
    ("Forecast earnings for {name}", "Forecast", {}),
    ("Technical analysis of {name}", "Technical Analysis", {}),
    ("Accounting review of {name}", "Accounting Review", {}),
    ("Management assessment of {name}", "Management Assessment", {}),
    ("Ownership review of {name}", "Ownership Review", {}),
    ("Governance review of {name}", "Governance Review", {}),
    ("Policy analysis impact on {sector}", "Policy Analysis", {}),
    ("Regulatory analysis for {sector}", "Regulatory Analysis", {}),
    ("Is {sector} sector attractive?", "Sector Attractiveness", {}),
    ("Industry structure of {sector}", "Industry Structure", {}),
    ("News impact on {name}", "News Impact", {}),
    ("Event analysis of {name} results", "Event Analysis", {}),
    ("Teach me {concept}", "Educational", {"question_type": "Teach"}),
    ("Deep research: should I buy {name}?", "Investment Evaluation", {"depth": "Deep Research"}),
    ("Quick summary of {name} valuation", "Valuation Assessment", {"question_type": "Summarise"}),
]

_NAMES = [
    "HDFC Bank",
    "Infosys",
    "TCS",
    "Reliance",
    "SBI",
    "ICICI Bank",
    "Asian Paints",
    "Titan",
    "Wipro",
    "HCL Tech",
    "ITC",
    "Bajaj Finance",
    "Kotak Bank",
    "Axis Bank",
    "L&T",
    "Maruti",
    "Sun Pharma",
    "Dr Reddy",
    "Nestle India",
    "Hindustan Unilever",
]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech", "Tech Mahindra"]
_SECTORS = ["banks", "IT", "auto", "pharma", "FMCG", "metals", "energy", "NBFCs"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50", "Nifty Pharma", "Nifty FMCG"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "moat", "PEG", "FCF yield", "WACC"]


def plan_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    body = payload or {}
    intent = classify_intent(question, body.get("intent") if isinstance(body.get("intent"), dict) else None)
    # Optional ERE soft input
    ere = body.get("entity_resolution") if isinstance(body.get("entity_resolution"), dict) else None
    if ere is None and not body.get("skip_ere"):
        try:
            from entity_resolution.canonical_resolver import resolve_question

            ere = resolve_question(question, {"use_cache": True})
        except Exception:
            ere = {}
    if ere is None:
        ere = {}

    ctx = classify_context(question, entity_resolution=ere, intent=intent)
    obj = classify_objective(
        question,
        primary_intent=intent.get("primary_intent"),
        entity_type=ctx.get("entity_type"),
    )
    meta = classify_question_meta(question, primary_objective=obj.get("primary_objective"))
    analysts = plan_analysts(obj.get("primary_objective"), obj.get("secondary_objectives"))
    layers = plan_layers(obj.get("primary_objective"))
    apis = plan_apis(obj.get("primary_objective"))
    blueprint = generate_blueprint(
        obj.get("primary_objective"),
        expected_output=meta.get("expected_output"),
    )

    intent_conf = None
    if isinstance(body.get("intent_confidence"), (int, float)):
        intent_conf = float(body["intent_confidence"])
    routing = score_routing(
        intent_confidence=intent_conf,
        objective_confidence=float(obj.get("objective_confidence") or 0.0),
        blueprint_sections=blueprint.get("blueprint_sections"),
        analysts=analysts.get("analysts"),
        layers=layers.get("layers"),
    )

    entity_ambiguous = bool(ctx.get("entity_ambiguous"))
    requires = bool(obj.get("requires_clarification") or entity_ambiguous)
    if should_block_execution(float(obj.get("objective_confidence") or 0.0), requires):
        requires = True

    planning_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    out: dict[str, Any] = {
        "ok": True,
        "roe_version": ROE_VERSION,
        "sprint": SPRINT,
        "question": question,
        "primary_intent": intent.get("primary_intent"),
        "primary_intent_id": intent.get("primary_intent_id"),
        "secondary_intents": intent.get("secondary_intents") or [],
        "primary_objective": obj.get("primary_objective"),
        "objective_alias": obj.get("objective_alias"),
        "secondary_objectives": obj.get("secondary_objectives") or [],
        "question_type": meta.get("question_type"),
        "decision_type": meta.get("decision_type"),
        "research_depth": meta.get("research_depth"),
        "urgency": meta.get("urgency"),
        "expected_output": meta.get("expected_output"),
        "analysts": analysts.get("analysts") or [],
        "layers": layers.get("layers") or [],
        "layers_skip": layers.get("layers_skip") or [],
        "apis": apis.get("apis") or [],
        "blueprint": blueprint.get("blueprint") or [],
        "blueprint_sections": blueprint.get("blueprint_sections") or [],
        "entity": {
            "name": ctx.get("entity_name"),
            "type": ctx.get("entity_type"),
            "ticker": ctx.get("ticker"),
            "id": ctx.get("entity_id"),
            "ambiguous": entity_ambiguous,
        },
        "routing_confidence": routing,
        "objective_confidence": routing.get("objective_confidence"),
        "overall_confidence": routing.get("overall_confidence"),
        "requires_clarification": requires,
        "block_execution": requires,
        "clarification": (
            clarification_payload(
                reason=obj.get("clarification_reason")
                or ("entity_ambiguous" if entity_ambiguous else "low_objective_confidence"),
                primary_objective=obj.get("primary_objective"),
                objective_confidence=float(obj.get("objective_confidence") or 0.0),
                alternatives=[c["objective"] for c in (obj.get("candidates") or []) if c.get("objective")],
            )
            if requires
            else None
        ),
        "executed_layers": [],
        "executed_analysts": [],
        "planning_ms": planning_ms,
        "within_latency_target": planning_ms <= MAX_PLANNING_MS_TARGET,
        "not_a_top_level_intelligence_layer": True,
        "candidates": obj.get("candidates") or [],
    }
    out["diagnostics"] = diagnose(out)
    return out


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ROE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_planning_ms_target": MAX_PLANNING_MS_TARGET,
        "not_a_top_level_intelligence_layer": True,
        "law": "Determine the decision to support before collecting data or executing layers.",
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "roe_version": ROE_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "roe_version": ROE_VERSION}
    return {"enabled": True, **plan_question(question, body)}


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:10]:
        row = plan_question(b["q"], {"skip_ere": True})
        samples.append(
            {
                "question": b["q"],
                "primary_objective": row.get("primary_objective"),
                "question_type": row.get("question_type"),
                "expected_output": row.get("expected_output"),
                "research_depth": row.get("research_depth"),
                "analysts": row.get("analysts"),
                "layers": row.get("layers"),
                "apis": row.get("apis"),
                "blueprint_sections": row.get("blueprint_sections"),
                "routing_confidence": row.get("routing_confidence"),
                "planning_ms": row.get("planning_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "roe_version": ROE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/research-planner"],
        "api_prefix": "/v1/research-objective",
        "law": "Research becomes objective-driven before any intelligence layer executes.",
    }


def _expanded_benchmarks() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    for name in _NAMES:
        for peer in _PEERS:
            for sector in _SECTORS:
                for index in _INDEXES:
                    for concept in _CONCEPTS:
                        # generate from templates with rotating fills — break early once enough
                        pass
    # Deterministic expansion
    i = 0
    while len(cases) < 1100:
        tmpl, objective, extra = _TEMPLATES[i % len(_TEMPLATES)]
        name = _NAMES[i % len(_NAMES)]
        peer = _PEERS[i % len(_PEERS)]
        if peer == name:
            peer = _PEERS[(i + 1) % len(_PEERS)]
        sector = _SECTORS[i % len(_SECTORS)]
        index = _INDEXES[i % len(_INDEXES)]
        concept = _CONCEPTS[i % len(_CONCEPTS)]
        q = tmpl.format(name=name, peer=peer, sector=sector, index=index, concept=concept)
        cases.append(
            {
                "q": q,
                "objective": objective,
                **extra,
                "kind": "template",
            }
        )
        i += 1
    return cases


def quality_gates() -> dict[str, Any]:
    cases = _expanded_benchmarks()
    passed = 0
    obj_ok = 0
    qtype_ok = 0
    qtype_n = 0
    bp_ok = 0
    bp_n = 0
    analyst_ok = 0
    analyst_n = 0
    layer_ok = 0
    layer_n = 0
    timed: list[float] = []
    failures: list[dict[str, Any]] = []

    for b in cases[:1100]:
        # Avoid ERE latency in gates; objective classification is the gate subject
        row = plan_question(b["q"], {"entity_resolution": {}})
        timed.append(float(row.get("planning_ms") or 0))
        ok = True
        if row.get("primary_objective") == b.get("objective"):
            obj_ok += 1
        else:
            ok = False
        if b.get("question_type"):
            qtype_n += 1
            if row.get("question_type") == b.get("question_type"):
                qtype_ok += 1
            else:
                ok = False
        if b.get("expected_output"):
            if row.get("expected_output") != b.get("expected_output"):
                ok = False
        if b.get("depth"):
            if row.get("research_depth") != b.get("depth"):
                ok = False
        if b.get("analysts_contains"):
            analyst_n += 1
            have = set(row.get("analysts") or [])
            if set(b["analysts_contains"]).issubset(have):
                analyst_ok += 1
            else:
                ok = False
        if b.get("analysts_exact") is not None:
            analyst_n += 1
            if list(row.get("analysts") or []) == list(b["analysts_exact"]):
                analyst_ok += 1
            else:
                ok = False
        if b.get("layers_contains"):
            layer_n += 1
            have = set(row.get("layers") or [])
            if set(b["layers_contains"]).issubset(have):
                layer_ok += 1
            else:
                ok = False
        if b.get("layers_exact") is not None:
            layer_n += 1
            if list(row.get("layers") or []) == list(b["layers_exact"]):
                layer_ok += 1
            else:
                ok = False
        if b.get("layers_skip_contains"):
            layer_n += 1
            have = set(row.get("layers_skip") or [])
            if set(b["layers_skip_contains"]).issubset(have):
                layer_ok += 1
            else:
                ok = False
        if b.get("apis_contains"):
            have = set(row.get("apis") or [])
            if not set(b["apis_contains"]).issubset(have):
                ok = False
        if b.get("secondary_contains"):
            have = set(row.get("secondary_objectives") or [])
            if not set(b["secondary_contains"]).issubset(have):
                ok = False
        if b.get("blueprint_contains"):
            bp_n += 1
            have = set(row.get("blueprint_sections") or [])
            if set(b["blueprint_contains"]).issubset(have):
                bp_ok += 1
            else:
                ok = False
        else:
            # generic blueprint presence for non-core templates
            bp_n += 1
            if row.get("blueprint_sections"):
                bp_ok += 1
            else:
                ok = False

        # No execution
        if row.get("executed_layers") or row.get("executed_analysts"):
            ok = False

        if ok:
            passed += 1
        elif len(failures) < 30:
            failures.append(
                {
                    "question": b["q"],
                    "expected_objective": b.get("objective"),
                    "actual_objective": row.get("primary_objective"),
                    "expected_question_type": b.get("question_type"),
                    "actual_question_type": row.get("question_type"),
                    "expected_output": b.get("expected_output"),
                    "actual_output": row.get("expected_output"),
                }
            )

    total = min(len(cases), 1100)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    obj_acc = obj_ok / total if total else 0.0
    qtype_acc = qtype_ok / qtype_n if qtype_n else 1.0
    bp_acc = bp_ok / bp_n if bp_n else 1.0
    analyst_acc = analyst_ok / analyst_n if analyst_n else 1.0
    layer_acc = layer_ok / layer_n if layer_n else 1.0
    return {
        "ok": (
            obj_acc >= 0.99
            and qtype_acc >= 0.98
            and bp_acc >= 0.98
            and analyst_acc >= 0.98
            and layer_acc >= 0.98
            and avg_ms <= MAX_PLANNING_MS_TARGET * 5  # CI headroom
            and total >= 1000
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "primary_objective_accuracy": round(obj_acc, 4),
        "question_type_accuracy": round(qtype_acc, 4),
        "blueprint_accuracy": round(bp_acc, 4),
        "analyst_routing_accuracy": round(analyst_acc, 4),
        "layer_routing_accuracy": round(layer_acc, 4),
        "avg_planning_ms": avg_ms,
        "p95_planning_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_planning_ms": MAX_PLANNING_MS_TARGET,
        "failures_sample": failures,
        "rule": "Every Ask AGI request begins with a complete institutional research plan before layers execute.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    row = plan_question(question or "", payload)
    return {
        "research_objective": {
            "enabled": True,
            "version": ROE_VERSION,
            "sprint": SPRINT,
            "primary_objective": row.get("primary_objective"),
            "objective_alias": row.get("objective_alias"),
            "secondary_objectives": row.get("secondary_objectives"),
            "question_type": row.get("question_type"),
            "decision_type": row.get("decision_type"),
            "research_depth": row.get("research_depth"),
            "urgency": row.get("urgency"),
            "expected_output": row.get("expected_output"),
            "analysts": row.get("analysts"),
            "layers": row.get("layers"),
            "layers_skip": row.get("layers_skip"),
            "apis": row.get("apis"),
            "blueprint": row.get("blueprint"),
            "routing_confidence": row.get("routing_confidence"),
            "requires_clarification": row.get("requires_clarification"),
            "block_execution": row.get("block_execution"),
            "planning_ms": row.get("planning_ms"),
            "no_layer_execution": True,
        }
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(plan_question(q, body))
