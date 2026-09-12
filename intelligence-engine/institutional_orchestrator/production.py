"""UAG-01 production façades — ask / stream / query / Orchestration Center."""

from __future__ import annotations

import hashlib
import time
from dataclasses import replace
from typing import Any, Iterator, Optional

from institutional_orchestrator.diagnostics import build_diagnostics
from institutional_orchestrator.flags import flags_dict, is_enabled
from institutional_orchestrator import history as query_history
from institutional_orchestrator.intent_classifier import classify_intent, extract_entities
from institutional_orchestrator.object_registry import catalog, reset_registry_for_tests
from institutional_orchestrator.planner import plan_query
from institutional_orchestrator.response_builder import build_response
from institutional_orchestrator.retrieval import execute_plan
from institutional_orchestrator.router import route_plan
from institutional_orchestrator.schema import (
    ORCHESTRATOR_VERSION,
    UAG_PRODUCT,
    UAG_ROLE,
    UAG_SPEC,
    UAG_VERSION,
    UAG_WORKSTREAM_ID,
    VALIDATOR_VERSION,
)
from institutional_orchestrator.validator import validate_response

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    query_history.reset_for_tests()
    reset_registry_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": UAG_WORKSTREAM_ID,
        "product": UAG_PRODUCT,
        "version": UAG_VERSION,
        "role": UAG_ROLE,
        "llm": False,
        "generates_recommendations": False,
        "owns_business_state": False,
        "stateless": True,
        "orchestration_only": True,
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "registered_objects": catalog(),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": UAG_SPEC,
        "brand": "AGI",
        "phase": 5,
        "history": query_history.metrics(),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    m = query_history.metrics()
    recent = query_history.recent(8)
    regs = catalog()
    return {
        "status": h.get("status"),
        "workstream_id": UAG_WORKSTREAM_ID,
        "product": UAG_PRODUCT,
        "version": UAG_VERSION,
        "llm": False,
        "orchestration_center": True,
        "active_queries": m.get("active_cached") or 0,
        "planner_performance": {
            "query_count": m.get("query_count") or 0,
            "average_latency_ms": m.get("average_latency_ms") or 0,
        },
        "routing_accuracy": None,  # filled after labeled evals; soft null
        "object_coverage": len([r for r in regs if r.get("has_provider")]),
        "registered_object_count": len(regs),
        "average_latency": m.get("average_latency_ms") or 0,
        "failed_plans": m.get("failed_plans") or 0,
        "missing_registrations": [r["object_type"] for r in regs if not r.get("has_provider")],
        "recent_queries": recent,
    }


def _query_id(question: str) -> str:
    raw = f"{question}|{now_iso()}|{ORCHESTRATOR_VERSION}"
    return f"uag-{hashlib.sha256(raw.encode()).hexdigest()[:14]}"


def ask(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": UAG_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["UAG-01 disabled"],
        }

    t0 = time.perf_counter()
    body = dict(payload or {})
    # PRP-03: Observability middleware — observe only; never changes behavior
    try:
        from institutional_observability.production import maybe_begin, maybe_end

        maybe_begin(body, name="uag.ask")
    except Exception:
        pass

    # PRP-02: Security Gateway — authorize before orchestration (engines stay unaware)
    try:
        from institutional_security.production import finalize_with_security, maybe_gate_ask

        denied = maybe_gate_ask(body)
        if denied is not None:
            try:
                from institutional_observability.production import maybe_end

                return maybe_end(body, denied, component="uag.ask")
            except Exception:
                return denied
    except Exception:
        pass

    question = str(body.get("question") or body.get("query") or body.get("q") or "").strip()
    if not question:
        early = {
            "ok": False,
            "rejected": True,
            "workstream_id": UAG_WORKSTREAM_ID,
            "validation_errors": ["question required"],
        }
        try:
            from institutional_observability.production import maybe_end

            return maybe_end(body, early, component="uag.ask")
        except Exception:
            return early

    portfolio_id = str(body.get("portfolio_id") or body.get("portfolio") or "agi-core-equity")
    policy = str(body.get("policy") or "family_office")
    # MPC-01: explicit execution context scopes retrieval — does not change company truth
    execution_context = body.get("execution_context") or body.get("context")
    if isinstance(execution_context, dict):
        portfolio_id = str(
            execution_context.get("portfolio_id") or portfolio_id
        )
        if execution_context.get("policy_profile"):
            policy = str(execution_context.get("policy_profile"))
    entities_override = body.get("entities")

    # PRP-01: query cache (Ask AGI < 2s cached)
    skip_cache = bool(body.get("bypass_cache") or body.get("no_cache"))
    cache_parts = (
        question.lower(),
        portfolio_id,
        policy,
        json_safe_entities(entities_override),
    )
    if not skip_cache:
        try:
            from institutional_performance.production import (
                maybe_get_query_cache,
                record_op_latency,
            )

            cached = maybe_get_query_cache(*cache_parts)
            if isinstance(cached, dict) and cached.get("ok"):
                elapsed = time.perf_counter() - t0
                record_op_latency("ask_cached", elapsed, cached=True)
                out = dict(cached)
                out["cached"] = True
                out["cache_layer"] = "PRP-01"
                out["latency_ms"] = round(elapsed * 1000.0, 2)
                try:
                    from institutional_observability.production import maybe_end

                    return maybe_end(body, out, component="uag.ask")
                except Exception:
                    return out
        except Exception:
            pass

    intent_info = classify_intent(question)
    intent = str(intent_info.get("intent") or "Search")
    entities = (
        tuple(str(e).upper() for e in entities_override)
        if entities_override
        else extract_entities(question)
    )

    qid = _query_id(question)
    generated_at = now_iso()
    query = plan_query(
        query_id=qid,
        question=question,
        intent=intent,
        entities=entities,
        generated_at=generated_at,
    )
    routed = route_plan(query)
    steps, payloads = execute_plan(query, portfolio_id=portfolio_id, policy=policy)
    query = replace(query, execution_plan=steps)

    response = build_response(
        query,
        steps=steps,
        payloads=payloads,
        generated_at=generated_at,
    )
    latency = (time.perf_counter() - t0) * 1000.0
    prelim = build_diagnostics(query, response, latency_ms=latency, routed=routed)
    response = replace(response, diagnostics=prelim)

    validation = validate_response(query, response)
    diag = build_diagnostics(
        query,
        response,
        validation=validation.to_dict(),
        latency_ms=(time.perf_counter() - t0) * 1000.0,
        routed=routed,
    )
    response = replace(response, diagnostics=diag)
    query = replace(query, diagnostics={"intent": intent_info, **(query.diagnostics or {})})

    ok = validation.ok
    query_history.record(query, response, ok=ok, latency_ms=diag["latency_ms"])

    # Soft deep-link into RW-01 Research Workspace (Ask answers where; workspace shows everything).
    workspace_link: dict[str, Any] = {}
    try:
        from institutional_workspace.navigation import (
            workspace_deep_link,
            workspace_focus_for_intent,
        )

        focus = workspace_focus_for_intent(intent)
        ticker = entities[0] if entities else ""
        workspace_link = {
            "focus": focus,
            "href": workspace_deep_link(
                ticker=ticker,
                portfolio_id=portfolio_id if not ticker else "",
                focus=focus,
                context="portfolio" if not ticker else "company",
            ),
            "lineage_hint": [
                "Decision",
                "Timeline",
                "Observation",
                "Evidence",
            ],
            "engine": "RW-01",
        }
    except Exception:
        workspace_link = {}

    ctx_out = execution_context if isinstance(execution_context, dict) else None

    if not ok:
        try:
            from institutional_performance.production import record_op_latency

            record_op_latency("ask", time.perf_counter() - t0, cached=False)
        except Exception:
            pass
        rejected = {
            "ok": False,
            "rejected": True,
            "workstream_id": UAG_WORKSTREAM_ID,
            "validation_errors": list(validation.errors),
            "gates": validation.gates,
            "query": query.to_dict(),
            "response": response.to_dict(),
            "workspace": workspace_link,
            "execution_context": ctx_out,
            "diagnostics": diag,
            "llm": False,
            "generates_recommendations": False,
            "owns_business_state": False,
        }
        try:
            from institutional_security.production import finalize_with_security

            rejected = finalize_with_security(rejected, body)
        except Exception:
            pass
        try:
            from institutional_observability.production import maybe_end

            return maybe_end(body, rejected, component="uag.ask")
        except Exception:
            return rejected

    result = {
        "ok": True,
        "rejected": False,
        "workstream_id": UAG_WORKSTREAM_ID,
        "product": UAG_PRODUCT,
        "version": UAG_VERSION,
        "query": query.to_dict(),
        "response": response.to_dict(),
        "workspace": workspace_link,
        "execution_context": ctx_out,
        "diagnostics": diag,
        "llm": False,
        "generates_recommendations": False,
        "owns_business_state": False,
        "stateless": True,
        "cached": False,
    }
    try:
        from institutional_performance.production import (
            maybe_set_query_cache,
            record_op_latency,
        )

        elapsed = time.perf_counter() - t0
        record_op_latency("ask", elapsed, cached=False)
        if not skip_cache:
            maybe_set_query_cache(*cache_parts, value=result)
    except Exception:
        pass
    try:
        from institutional_security.production import finalize_with_security

        result = finalize_with_security(result, body)
    except Exception:
        pass
    try:
        from institutional_observability.production import maybe_end

        result = maybe_end(body, result, component="uag.ask")
    except Exception:
        pass
    # L-01: usage journey — observe only
    try:
        from institutional_launch.production import maybe_track_ask

        maybe_track_ask(body, result)
    except Exception:
        pass
    return result


def json_safe_entities(entities_override: Any) -> str:
    if not entities_override:
        return ""
    try:
        return ",".join(sorted(str(e).upper() for e in entities_override))
    except Exception:
        return str(entities_override)


def ask_stream(payload: Optional[dict[str, Any]] = None) -> Iterator[dict[str, Any]]:
    """
    Streaming façade — yields plan, then steps, then final response.

    Not token-LLM streaming; structured orchestration events.
    """
    body = dict(payload or {})
    question = str(body.get("question") or body.get("query") or "").strip()
    yield {"event": "start", "question": question, "workstream_id": UAG_WORKSTREAM_ID}

    # Build plan first for progressive disclosure
    intent_info = classify_intent(question)
    entities = extract_entities(question)
    qid = _query_id(question or "empty")
    query = plan_query(
        query_id=qid,
        question=question,
        intent=str(intent_info.get("intent") or "Search"),
        entities=entities,
        generated_at=now_iso(),
    )
    yield {"event": "plan", "query": query.to_dict()}

    result = ask(payload)
    yield {"event": "step", "execution_plan": (result.get("response") or {}).get("execution_plan")}
    yield {"event": "final", "result": result}


def get_query(query_id: str) -> dict[str, Any]:
    row = query_history.get_query(query_id)
    if row is None:
        return {
            "ok": False,
            "workstream_id": UAG_WORKSTREAM_ID,
            "error": "query_not_found",
            "query_id": query_id,
        }
    return {
        "ok": True,
        "workstream_id": UAG_WORKSTREAM_ID,
        "query_id": query_id,
        **row,
        "owns_business_state": False,
        "llm": False,
    }
