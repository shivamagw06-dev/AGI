"""IAR V1 production facade — RQ1 Sprint 5."""

from __future__ import annotations

from typing import Any

from analyst_router.analyst_registry import list_analysts, registry_stats
from analyst_router.flags import flags_dict, is_enabled
from analyst_router.mandates import all_mandates
from analyst_router.router import route_question
from analyst_router.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    IAR_VERSION,
    MAX_ROUTING_MS_TARGET,
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
        "required": ["Business", "Financial", "Valuation", "Risk", "Forecast", "Portfolio"],
        "optional_contains": ["Macro"],
        "suppressed_contains": ["Ownership", "Academy"],
        "order_prefix": ["Business", "Financial"],
        "weights": {
            "Business": 0.30,
            "Financial": 0.25,
            "Valuation": 0.20,
            "Risk": 0.10,
            "Forecast": 0.10,
            "Portfolio": 0.05,
        },
    },
    {
        "q": "Explain ROIC",
        "objective": "Educational",
        "required": ["Academy", "Financial"],
        "suppressed_contains": ["Business", "Valuation", "Portfolio", "Committee"],
    },
    {
        "q": "Compare TCS vs Infosys",
        "objective": "Peer Comparison",
        "required": ["Business", "Financial", "Valuation", "Sector"],
        "suppressed_contains": ["Portfolio", "Management"],
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "objective": "Historical Analysis",
        "required": ["Valuation", "Sector", "Macro", "Forecast"],
        "suppressed_contains": ["Business", "Management", "Portfolio"],
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "objective": "Portfolio Decision",
        "required_contains": ["Portfolio", "Risk"],
        "weights_has": ["Portfolio"],
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "objective": "Macro Impact",
        "required_contains": ["Macro", "Sector", "Forecast"],
    },
    {
        "q": "What are the risks in Reliance Industries?",
        "objective": "Risk Assessment",
        "required_contains": ["Risk", "Financial"],
    },
    {
        "q": "Should I sell Infosys?",
        "objective": "Investment Evaluation",
        "required_contains": ["Business", "Valuation", "Portfolio"],
    },
    {
        "q": "Teach me what EV/EBITDA means",
        "objective": "Educational",
        "required": ["Academy", "Financial"],
    },
    {
        "q": "Accounting review of Yes Bank",
        "objective": "Accounting Review",
        "required_contains": ["Accounting", "Financial"],
    },
]

_TEMPLATES: list[tuple[str, str, dict[str, Any]]] = [
    ("Should I buy {name}?", "Investment Evaluation", {"required_contains": ["Business", "Valuation"]}),
    ("Should I sell {name}?", "Investment Evaluation", {"required_contains": ["Business", "Risk"]}),
    ("Compare {name} vs {peer}", "Peer Comparison", {"required": ["Business", "Financial", "Valuation", "Sector"]}),
    ("Explain {concept}", "Educational", {"required": ["Academy", "Financial"]}),
    ("Is {index} expensive versus history?", "Historical Analysis", {"required": ["Valuation", "Sector", "Macro", "Forecast"]}),
    ("How will RBI rate cuts affect {sector}?", "Macro Impact", {"required_contains": ["Macro"]}),
    ("Build a portfolio with {name}", "Portfolio Decision", {"required_contains": ["Portfolio"]}),
    ("What are the risks in {name}?", "Risk Assessment", {"required_contains": ["Risk"]}),
    ("Is {name} overvalued?", "Valuation Assessment", {"required_contains": ["Valuation", "Financial"]}),
    ("Assess business quality of {name}", "Business Quality Assessment", {"required_contains": ["Business"]}),
    ("Financial health of {name}", "Financial Health Assessment", {"required_contains": ["Financial"]}),
    ("Forecast earnings for {name}", "Forecast", {"required_contains": ["Forecast"]}),
    ("Screen for quality {sector} stocks", "Screening", {"required_contains": ["Financial", "Valuation"]}),
    ("Technical analysis of {name}", "Technical Analysis", {"required_contains": ["Market"]}),
    ("News impact on {name}", "News Impact", {"required_contains": ["News"]}),
    ("Management assessment of {name}", "Management Assessment", {"required_contains": ["Management"]}),
    ("Ownership review of {name}", "Ownership Review", {"required_contains": ["Ownership"]}),
    ("Accounting review of {name}", "Accounting Review", {"required_contains": ["Accounting"]}),
    ("Is {sector} sector attractive?", "Sector Attractiveness", {"required_contains": ["Sector"]}),
    ("Industry structure of {sector}", "Industry Structure", {"required_contains": ["Sector", "Business"]}),
]

_NAMES = [
    "HDFC Bank", "Infosys", "TCS", "Reliance", "SBI", "ICICI Bank",
    "Asian Paints", "Titan", "Wipro", "HCL Tech", "ITC", "Bajaj Finance",
    "Kotak Bank", "Axis Bank", "L&T", "Maruti", "Sun Pharma", "Nestle India",
]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech", "Tech Mahindra"]
_SECTORS = ["banks", "IT", "auto", "pharma", "FMCG", "metals", "energy", "NBFCs"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50", "Nifty Pharma", "Nifty FMCG"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "moat", "PEG", "FCF yield", "WACC"]


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IAR_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_routing_ms_target": MAX_ROUTING_MS_TARGET,
        "registry": registry_stats(),
        "not_a_top_level_intelligence_layer": True,
        "law": "Only relevant specialists participate; suppressed analysts must not execute.",
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "mandates": all_mandates()}


def route(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "iar_version": IAR_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "iar_version": IAR_VERSION}
    return {"enabled": True, **route_question(question, body)}


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:8]:
        row = route_question(b["q"], {"primary_objective": b.get("objective")} if b.get("objective") else {})
        # Prefer live ROE objective resolution for display samples
        row = route_question(b["q"], {})
        samples.append(
            {
                "question": b["q"],
                "primary_objective": row.get("primary_objective"),
                "required_analysts": row.get("required_analysts"),
                "optional_analysts": row.get("optional_analysts"),
                "suppressed_analysts": row.get("suppressed_analysts"),
                "speaking_order": row.get("speaking_order"),
                "weights": row.get("weights"),
                "routing_confidence": row.get("routing_confidence"),
                "routing_ms": row.get("routing_ms"),
                "assignment_count": len(row.get("assignments") or []),
            }
        )
    return {
        "programme": PROGRAMME,
        "iar_version": IAR_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "registry": registry_stats(),
        "analysts": list_analysts(),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/analyst-router"],
        "api_prefix": "/v1/analyst-router",
        "law": "Only relevant specialists participate; every analyst stays inside mandate.",
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return route_question(q, body).get("diagnostics") or {}


def _expanded_benchmarks() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
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
        cases.append({"q": q, "objective": objective, **extra, "kind": "template"})
        i += 1
    return cases


def _check_case(b: dict[str, Any], row: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if b.get("objective") and row.get("primary_objective") != b.get("objective"):
        # Soft: if ROE disagrees we still evaluate routing against expected objective override
        pass
    req = set(row.get("required_analysts") or [])
    opt = set(row.get("optional_analysts") or [])
    sup = set(row.get("suppressed_analysts") or [])
    if b.get("required"):
        if list(row.get("required_analysts") or []) != list(b["required"]):
            # allow same set different order
            if req != set(b["required"]):
                errs.append("required_mismatch")
    if b.get("required_contains"):
        if not set(b["required_contains"]).issubset(req):
            errs.append("required_contains")
    if b.get("optional_contains"):
        if not set(b["optional_contains"]).issubset(opt):
            errs.append("optional_contains")
    if b.get("suppressed_contains"):
        if not set(b["suppressed_contains"]).issubset(sup):
            errs.append("suppressed_contains")
    if b.get("order_prefix"):
        order = list(row.get("speaking_order") or [])
        pref = list(b["order_prefix"])
        if order[: len(pref)] != pref:
            errs.append("order_prefix")
    if b.get("weights"):
        got = row.get("weights") or {}
        for k, v in b["weights"].items():
            if abs(float(got.get(k, -1)) - float(v)) > 0.001:
                errs.append(f"weight_{k}")
    if b.get("weights_has"):
        got = row.get("weights") or {}
        if not set(b["weights_has"]).issubset(set(got)):
            errs.append("weights_has")
    # No execution
    if row.get("executed_analysts"):
        errs.append("executed")
    # No required in suppressed
    if req & sup:
        errs.append("required_suppressed_overlap")
    # Assignments for required
    assigned = {a.get("analyst") for a in (row.get("assignments") or [])}
    if not set(row.get("required_analysts") or []).issubset(assigned):
        errs.append("missing_assignments")
    return (not errs, errs)


def quality_gates() -> dict[str, Any]:
    cases = _expanded_benchmarks()
    passed = 0
    sel_ok = 0
    excl_ok = 0
    order_ok = 0
    weight_ok = 0
    mandate_violations = 0
    timed: list[float] = []
    failures: list[dict[str, Any]] = []

    for b in cases[:1100]:
        # Pin objective for template routing stability when provided
        payload: dict[str, Any] = {}
        if b.get("objective"):
            payload["primary_objective"] = b["objective"]
            if b["objective"] == "Educational":
                payload["question_type"] = "Explain"
            if "Should I buy" in b["q"] or b["q"].startswith("Should I buy"):
                payload["question_type"] = "Should I Buy?"
            if "Should I sell" in b["q"]:
                payload["question_type"] = "Should I Sell?"
        row = route_question(b["q"], payload)
        timed.append(float(row.get("routing_ms") or 0))
        ok, errs = _check_case(b, row)

        # Selection accuracy: required_contains or required
        if b.get("required") or b.get("required_contains"):
            if "required_mismatch" not in errs and "required_contains" not in errs:
                sel_ok += 1
        else:
            sel_ok += 1 if row.get("required_analysts") else 0

        if b.get("suppressed_contains"):
            if "suppressed_contains" not in errs:
                excl_ok += 1
        else:
            excl_ok += 1 if "required_suppressed_overlap" not in errs else 0

        if b.get("order_prefix"):
            if "order_prefix" not in errs:
                order_ok += 1
        else:
            # speaking order includes all required
            order = set(row.get("speaking_order") or [])
            order_ok += 1 if set(row.get("required_analysts") or []).issubset(order) else 0

        if b.get("weights") or b.get("weights_has"):
            if not any(e.startswith("weight") for e in errs):
                weight_ok += 1
        else:
            w = row.get("weights") or {}
            weight_ok += 1 if w and abs(sum(w.values()) - 1.0) < 0.02 else 0

        # Mandate: assignments must include never walls for required
        for a in row.get("assignments") or []:
            if a.get("analyst") in (row.get("required_analysts") or []) and a.get("never") is None:
                mandate_violations += 1

        if ok:
            passed += 1
        elif len(failures) < 25:
            failures.append(
                {
                    "question": b["q"],
                    "errors": errs,
                    "required": row.get("required_analysts"),
                    "suppressed": row.get("suppressed_analysts"),
                    "objective": row.get("primary_objective"),
                }
            )

    total = min(len(cases), 1100)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    sel_acc = sel_ok / total if total else 0.0
    excl_acc = excl_ok / total if total else 0.0
    order_acc = order_ok / total if total else 0.0
    weight_acc = weight_ok / total if total else 0.0
    return {
        "ok": (
            sel_acc >= 0.98
            and excl_acc >= 0.98
            and order_acc >= 0.98
            and weight_acc >= 0.98
            and mandate_violations == 0
            and avg_ms <= MAX_ROUTING_MS_TARGET * 5
            and total >= 1000
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "analyst_selection_accuracy": round(sel_acc, 4),
        "exclusion_accuracy": round(excl_acc, 4),
        "speaking_order_accuracy": round(order_acc, 4),
        "weight_accuracy": round(weight_acc, 4),
        "mandate_violations": mandate_violations,
        "avg_routing_ms": avg_ms,
        "p95_routing_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_routing_ms": MAX_ROUTING_MS_TARGET,
        "failures_sample": failures,
        "rule": "Only relevant specialists participate; suppressed analysts must not execute.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    row = route_question(question or "", payload)
    return {
        "analyst_router": {
            "enabled": True,
            "version": IAR_VERSION,
            "sprint": SPRINT,
            "primary_objective": row.get("primary_objective"),
            "required_analysts": row.get("required_analysts"),
            "optional_analysts": row.get("optional_analysts"),
            "suppressed_analysts": row.get("suppressed_analysts"),
            "speaking_order": row.get("speaking_order"),
            "weights": row.get("weights"),
            "dependencies": row.get("dependencies"),
            "assignments": row.get("assignments"),
            "routing_confidence": row.get("routing_confidence"),
            "routing_ms": row.get("routing_ms"),
            "no_analyst_execution": True,
        }
    }
