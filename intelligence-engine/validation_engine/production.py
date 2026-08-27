"""IVCE V1 production facade — RQ1 Sprint 9."""

from __future__ import annotations

from typing import Any

from validation_engine.diagnostics import diagnose
from validation_engine.flags import flags_dict, is_enabled
from validation_engine.readiness_gate import validate_request
from validation_engine.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    IVCE_VERSION,
    MAX_VALIDATION_MS_TARGET,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "q": "Should I buy HDFC Bank?",
        "expect_state_in": ["READY", "READY_WITH_WARNINGS"],
        "expect_execution": True,
        "expect_no_clarification": True,
    },
    {
        "q": "Analyse Tata",
        "expect_state_in": ["CLARIFICATION_REQUIRED"],
        "expect_execution": False,
        "expect_clarification_type": "entity_disambiguation",
    },
    {
        "q": "Should I buy Tata?",
        "expect_state_in": ["CLARIFICATION_REQUIRED"],
        "expect_execution": False,
        "expect_clarification_type": "entity_disambiguation",
    },
    {
        "q": "Compare Infosys",
        "expect_state_in": ["CLARIFICATION_REQUIRED"],
        "expect_execution": False,
        "expect_clarification_type": "comparison_target",
    },
    {
        "q": "Compare",
        "expect_state_in": ["CLARIFICATION_REQUIRED", "BLOCKED"],
        "expect_execution": False,
    },
    {
        "q": "Build portfolio",
        "expect_state_in": ["CLARIFICATION_REQUIRED", "READY_WITH_WARNINGS"],
        "expect_clarification_type": "portfolio_inputs",
    },
    {
        "q": "Explain ROIC",
        "expect_state_in": ["READY", "READY_WITH_WARNINGS"],
        "expect_execution": True,
    },
    {
        "q": "Compare TCS vs Infosys",
        "expect_state_in": ["READY", "READY_WITH_WARNINGS"],
        "expect_execution": True,
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "expect_state_in": ["READY", "READY_WITH_WARNINGS"],
        "expect_execution": True,
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "expect_state_in": ["READY", "READY_WITH_WARNINGS"],
        "expect_execution": True,
    },
    {
        "q": "guaranteed returns on Infosys",
        "expect_state_in": ["BLOCKED"],
        "expect_execution": False,
    },
    {
        "q": "What are the risks in Reliance Industries?",
        "expect_state_in": ["READY", "READY_WITH_WARNINGS"],
        "expect_execution": True,
    },
]

_TEMPLATES: list[tuple[str, dict[str, Any]]] = [
    ("Should I buy {name}?", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("Should I sell {name}?", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("Compare {name} vs {peer}", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("Explain {concept}", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("Is {index} expensive versus history?", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("How will RBI rate cuts affect {sector}?", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("What are the risks in {name}?", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("Analyse {group}", {"expect_state_in": ["CLARIFICATION_REQUIRED"], "expect_execution": False}),
    ("Should I buy {group}?", {"expect_state_in": ["CLARIFICATION_REQUIRED"], "expect_execution": False}),
    ("Compare {name}", {"expect_state_in": ["CLARIFICATION_REQUIRED"], "expect_execution": False, "expect_clarification_type": "comparison_target"}),
    ("Build portfolio", {"expect_state_in": ["CLARIFICATION_REQUIRED", "READY_WITH_WARNINGS"]}),
    ("guaranteed returns on {name}", {"expect_state_in": ["BLOCKED"], "expect_execution": False}),
    ("sure shot profit in {name}", {"expect_state_in": ["BLOCKED"], "expect_execution": False}),
    ("Accounting review of {name}", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("Forecast earnings for {name}", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
    ("News impact on {name}", {"expect_state_in": ["READY", "READY_WITH_WARNINGS"], "expect_execution": True}),
]

_NAMES = ["HDFC Bank", "Infosys", "TCS", "Reliance Industries", "ICICI Bank", "Wipro", "Titan", "ITC"]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech"]
_SECTORS = ["banks", "IT", "auto", "pharma"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "WACC"]
_GROUPS = ["Tata", "Adani", "HDFC"]


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IVCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_validation_ms_target": MAX_VALIDATION_MS_TARGET,
        "not_a_top_level_intelligence_layer": True,
        "law": "No institutional research begins until validation gates pass.",
        "research_readiness_memo": True,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate(payload)


def validate(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "ivce_version": IVCE_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "ivce_version": IVCE_VERSION}
    return {"enabled": True, **validate_request(question, body)}


def enrich(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate(payload)


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:10]:
        row = validate_request(b["q"], {})
        samples.append(
            {
                "question": b["q"],
                "readiness_state": row.get("readiness_state"),
                "overall_readiness": row.get("overall_readiness"),
                "execution_allowed": row.get("execution_allowed"),
                "warnings": row.get("warnings"),
                "clarifications": row.get("clarifications"),
                "validation_ms": (row.get("metrics") or {}).get("validation_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "ivce_version": IVCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/validation-engine"],
        "api_prefix": "/v1/validation-engine",
        "law": "Every Ask AGI request receives an Institutional Readiness Score before research execution.",
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    row = validate_request(question, payload or {})
    return {
        "ivce_version": IVCE_VERSION,
        "question": row.get("question"),
        "readiness_state": row.get("readiness_state"),
        "overall_readiness": row.get("overall_readiness"),
        "execution_allowed": row.get("execution_allowed"),
        "warnings": row.get("warnings"),
        "clarifications": row.get("clarifications"),
        "confidence": row.get("confidence"),
        "component_scores": row.get("component_scores"),
        "readiness_memo": {
            "status": (row.get("readiness_memo") or {}).get("status"),
            "readiness_pct": (row.get("readiness_memo") or {}).get("readiness_pct"),
            "strengths": (row.get("readiness_memo") or {}).get("strengths"),
            "weaknesses": (row.get("readiness_memo") or {}).get("weaknesses"),
            "risks": (row.get("readiness_memo") or {}).get("risks"),
            "recommended_analysts": (row.get("readiness_memo") or {}).get("recommended_analysts"),
            "suppressed": (row.get("readiness_memo") or {}).get("suppressed"),
            "expected_confidence": (row.get("readiness_memo") or {}).get("expected_confidence"),
            "expected_runtime_seconds": (row.get("readiness_memo") or {}).get("expected_runtime_seconds"),
        },
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
    }


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
            group=_GROUPS[i % len(_GROUPS)],
        )
        cases.append({"q": q, **extra, "kind": "template"})
        i += 1
    return cases


def _check(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    state = row.get("readiness_state")
    if b.get("expect_state_in") and state not in b["expect_state_in"]:
        errs.append("state")
    if b.get("expect_execution") is True and not row.get("execution_allowed"):
        errs.append("execution_false")
    if b.get("expect_execution") is False and row.get("execution_allowed"):
        errs.append("execution_true")
    if b.get("expect_no_clarification") and row.get("clarifications"):
        # warnings ok; clarifications that block should be empty
        if row.get("readiness_state") == "CLARIFICATION_REQUIRED":
            errs.append("unexpected_clarification")
    if b.get("expect_clarification_type"):
        types = {c.get("type") for c in (row.get("clarifications") or [])}
        if b["expect_clarification_type"] not in types:
            errs.append("clarification_type")
    if not row.get("mandatory_fields_present", True):
        errs.append("mandatory_fields")
    if not row.get("readiness_memo"):
        errs.append("memo")
    return errs


def quality_gates() -> dict[str, Any]:
    cases = _expanded()
    validation_ok = 0
    clarification_ok = 0
    clarification_total = 0
    false_ready = 0
    false_block = 0
    should_block_or_clarify = 0
    should_ready = 0
    times: list[float] = []
    failures: list[dict[str, Any]] = []
    checked = 0

    for b in cases:
        row = validate_request(b["q"], {})
        checked += 1
        errs = _check(b, row)
        times.append(float((row.get("metrics") or {}).get("validation_ms") or 0))

        expect_exec = b.get("expect_execution")
        expect_states = b.get("expect_state_in") or []
        expects_pause = expect_exec is False or any(
            s in expect_states for s in ("CLARIFICATION_REQUIRED", "BLOCKED")
        ) and expect_exec is not True

        if expects_pause:
            should_block_or_clarify += 1
            # false ready: executed when should pause
            if row.get("execution_allowed") and row.get("readiness_state") in {"READY", "READY_WITH_WARNINGS"}:
                if expect_exec is False:
                    false_ready += 1
        if expect_exec is True:
            should_ready += 1
            if not row.get("execution_allowed") or row.get("readiness_state") in {"CLARIFICATION_REQUIRED", "BLOCKED"}:
                false_block += 1

        if b.get("expect_clarification_type") or (expect_exec is False and "CLARIFICATION_REQUIRED" in expect_states):
            clarification_total += 1
            types = {c.get("type") for c in (row.get("clarifications") or [])}
            if b.get("expect_clarification_type"):
                if b["expect_clarification_type"] in types:
                    clarification_ok += 1
            elif row.get("readiness_state") == "CLARIFICATION_REQUIRED" or row.get("clarifications"):
                clarification_ok += 1

        if not errs:
            validation_ok += 1
        elif len(failures) < 25:
            failures.append({"q": b["q"], "errs": errs, "state": row.get("readiness_state")})

    n = max(checked, 1)
    avg_ms = sum(times) / n
    criteria = constitution_dict()["success_criteria"]
    validation_acc = validation_ok / n
    clarification_acc = (clarification_ok / clarification_total) if clarification_total else 1.0
    false_ready_rate = (false_ready / should_block_or_clarify) if should_block_or_clarify else 0.0
    false_block_rate = (false_block / should_ready) if should_ready else 0.0

    passed = (
        checked >= int(criteria["benchmark_minimum"])
        and validation_acc >= float(criteria["validation_accuracy"])
        and clarification_acc >= float(criteria["clarification_accuracy"])
        and false_ready_rate <= float(criteria["false_ready_rate"])
        and false_block_rate <= float(criteria["false_block_rate"])
        and avg_ms < float(criteria["average_runtime_ms"])
    )
    return {
        "ok": passed,
        "checked": checked,
        "validation_accuracy": round(validation_acc, 4),
        "clarification_accuracy": round(clarification_acc, 4),
        "false_ready_rate": round(false_ready_rate, 4),
        "false_block_rate": round(false_block_rate, 4),
        "average_runtime_ms": round(avg_ms, 4),
        "benchmark_minimum": criteria["benchmark_minimum"],
        "targets": criteria,
        "failures_sample": failures,
        "ivce_version": IVCE_VERSION,
        "sprint": SPRINT,
    }
