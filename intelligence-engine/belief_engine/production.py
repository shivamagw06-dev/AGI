"""Bayesian Belief & Confidence Engine (BBCE) V1 — RQ2 Sprint 6.

Soft-wired AFTER Institutional Falsification Engine and BEFORE
Business / Financial / Valuation opinions.
Not a top-level intelligence layer.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from belief_engine.belief_registry import (
    extract_falsification_map,
    extract_tested_hypotheses,
    register_beliefs,
)
from belief_engine.calibration_memory import (
    historical_calibration_for_type,
    memory_stats,
    remember_belief,
)
from belief_engine.confidence_calibration import calibrate_confidence
from belief_engine.diagnostics import diagnose
from belief_engine.drift_detector import detect_drift, package_drift_summary
from belief_engine.evidence_update import collect_log_likelihoods
from belief_engine.flags import flags_dict, is_enabled
from belief_engine.posterior_engine import belief_state_from_posterior, update_posterior
from belief_engine.prior_engine import build_prior
from belief_engine.probability_history import build_history
from belief_engine.schema import (
    ARCHITECTURE_STATUS,
    BBCE_VERSION,
    BELIEF_STATES,
    BENCHMARK_MIN_BELIEFS,
    CONFIDENCE_THRESHOLD,
    MAX_UPDATE_MS_TARGET,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)
from belief_engine.uncertainty_engine import build_uncertainty


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _try_ihte(question: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from hypothesis_testing.production import generate_for_question as ihte_gen  # type: ignore

        row = ihte_gen(question, payload)
        return extract_tested_hypotheses({"hypothesis_testing": {"tested_hypotheses": row.get("tested_hypotheses")}})
    except Exception:
        return []


def _try_falsification(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from falsification_engine.production import soft_slice_for_ask_agi as ife_soft  # type: ignore

        return ife_soft(question, payload) or {}
    except Exception:
        try:
            from falsification.production import soft_slice_for_ask_agi as ife_soft  # type: ignore

            return ife_soft(question, payload) or {}
        except Exception:
            return {}


def _fallback_tested(question: str) -> list[dict[str, Any]]:
    q = question.lower()
    if "versus history" in q or ("expensive" in q and "history" in q):
        seeds = [
            ("H1", "Valuation", "The sector trades above its historical valuation range.", 0.78, 84, 60),
            ("H2", "Industry", "Current premium reflects AI optimism only partially supported by order books.", 0.64, 72, 58),
        ]
    else:
        seeds = [
            ("H1", "Business", "HDFC possesses a durable funding advantage versus peers.", 0.82, 86, 68),
            ("H2", "Valuation", "Current valuation already reflects that franchise quality.", 0.63, 80, 55),
            ("H3", "Financial", "Credit costs remain structurally benign relative to peers.", 0.71, 82, 62),
        ]
    out = []
    for hid, typ, stmt, conf, support, contra in seeds:
        out.append(
            {
                "id": hid,
                "hypothesis": stmt,
                "type": typ,
                "initial_confidence": conf,
                "updated_probability": conf,
                "support_score": support,
                "contradiction_score": contra,
                "supporting_evidence": [
                    {"id": f"{hid}-S{i}", "text": f"Supporting evidence {i} for {hid}", "effect": "Supports", "support_score": support}
                    for i in range(1, 6)
                ],
                "contradicting_evidence": [
                    {"id": f"{hid}-C{i}", "text": f"Contradicting evidence {i} for {hid}", "effect": "Contradicts", "contradiction_score": contra}
                    for i in range(1, 3)
                ],
                "missing_evidence": [f"Pending verification item for {hid}"],
                "evidence_effects": [
                    {"id": f"{hid}-S1", "text": "Strong peer/historical confirmation", "effect": "Confirms"},
                    {"id": f"{hid}-S2", "text": "Supporting fundamental trend", "effect": "Supports"},
                    {"id": f"{hid}-S3", "text": "Secondary support", "effect": "Weakly Supports"},
                    {"id": f"{hid}-C1", "text": "Material challenge", "effect": "Contradicts"},
                    {"id": f"{hid}-C2", "text": "Raises doubt", "effect": "Questions"},
                ],
                "uncertainty": {"conflict_intensity": 0.4, "known_unknowns": ["Path of competitive response"], "missing_evidence": [f"Pending verification item for {hid}"]},
            }
        )
    return out


def update_belief(
    tested: dict[str, Any],
    *,
    falsification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run full Bayesian belief update for one tested hypothesis."""
    prior_pack = build_prior(tested)
    prior = float(prior_pack["prior_belief"])
    evidence_pack = collect_log_likelihoods(tested, falsification)
    posterior_pack = update_posterior(prior, float(evidence_pack["log_likelihood_total"]))
    posterior = float(posterior_pack["posterior_belief"])
    state = str(posterior_pack["belief_state"])

    support_count = len(evidence_pack.get("supporting_evidence") or [])
    contradiction_count = len(evidence_pack.get("contradicting_evidence") or [])
    missing_count = len(tested.get("missing_evidence") or [])

    hist_cal = historical_calibration_for_type(str(tested.get("type") or "Business"))
    calibration = calibrate_confidence(
        prior=prior,
        posterior=posterior,
        support_count=support_count,
        contradiction_count=contradiction_count,
        missing_count=missing_count,
        contribution_count=len(evidence_pack.get("contributions") or []),
        historical_calibration=hist_cal,
    )
    uncertainty = build_uncertainty(
        prior=prior,
        posterior=posterior,
        support_count=support_count,
        contradiction_count=contradiction_count,
        missing_count=missing_count,
        tested_uncertainty=_safe_dict(tested.get("uncertainty")),
    )
    drift = detect_drift(prior, posterior)
    history = build_history(
        hypothesis_id=str(tested.get("id")),
        prior=prior,
        contributions=list(evidence_pack.get("contributions") or []),
        posterior=posterior,
        belief_state=state,
    )

    return {
        "hypothesis_id": tested.get("id"),
        "hypothesis": tested.get("hypothesis"),
        "type": tested.get("type"),
        "prior_belief": prior,
        "prior_belief_pct": round(prior * 100),
        "stated_confidence": prior_pack.get("stated_confidence"),
        "supporting_evidence": evidence_pack.get("supporting_evidence"),
        "contradicting_evidence": evidence_pack.get("contradicting_evidence"),
        "evidence_contributions": evidence_pack.get("contributions"),
        "log_likelihood_total": evidence_pack.get("log_likelihood_total"),
        "posterior_belief": posterior,
        "posterior_belief_pct": posterior_pack.get("posterior_belief_pct"),
        "delta": posterior_pack.get("delta"),
        "belief_state": state,
        "confidence": calibration.get("confidence"),
        "confidence_pct": calibration.get("confidence_pct"),
        "calibration": calibration,
        "uncertainty": uncertainty,
        "drift": drift,
        "history": history,
        "falsification_applied": bool(falsification),
        "update_rule": posterior_pack.get("update_rule"),
        "ihte_status": tested.get("status"),
        "decision_hint": (
            "Treat as base-case institutional belief"
            if state in ("Strongly Supported", "Supported")
            else "Use as contested working hypothesis"
            if state in ("Leaning Positive", "Neutral", "Leaning Negative")
            else "Do not use as base-case — belief challenged or rejected"
        ),
    }


def generate_for_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(payload or {})
    question = str(question or payload.get("question") or payload.get("q") or "").strip()

    if not is_enabled():
        return {"ok": False, "enabled": False, "bbce_version": BBCE_VERSION, "update_ms": _ms(started)}
    if not question:
        return {"ok": False, "error": "question is required", "bbce_version": BBCE_VERSION, "update_ms": _ms(started)}

    tested = extract_tested_hypotheses(payload)
    ihte_imported = False
    if not tested:
        tested = _try_ihte(question, payload)
        ihte_imported = bool(tested)
    if not tested:
        tested = _fallback_tested(question)

    fals_map = extract_falsification_map(payload)
    ife_slice = {}
    if not fals_map:
        ife_slice = _try_falsification(
            question,
            {**payload, "hypothesis_testing": {"tested_hypotheses": tested}},
        )
        if ife_slice:
            payload = {**payload, **ife_slice}
            fals_map = extract_falsification_map(payload)

    beliefs = []
    for h in tested:
        fals = fals_map.get(str(h.get("id"))) or fals_map.get("*")
        beliefs.append(update_belief(h, falsification=fals))

    registry = register_beliefs(beliefs)
    drift_summary = package_drift_summary(beliefs)
    update_ms = _ms(started)

    mean_post = round(sum(float(b.get("posterior_belief") or 0) for b in beliefs) / max(len(beliefs), 1), 4)
    mean_conf = round(sum(float(b.get("confidence") or 0) for b in beliefs) / max(len(beliefs), 1), 4)

    row = {
        "ok": True,
        "enabled": True,
        "engine": "belief_engine",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": BBCE_VERSION,
        "bbce_version": BBCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Institutional Falsification Engine",
        "executes_before": "Business / Financial / Valuation opinions",
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        "beliefs": beliefs,
        "belief_count": len(beliefs),
        "institutional_belief_package": {
            "beliefs": beliefs,
            "registry": registry,
            "drift_summary": drift_summary,
            "mean_posterior_belief": mean_post,
            "mean_confidence": mean_conf,
        },
        "registry": registry,
        "drift_summary": drift_summary,
        "belief_states": list(BELIEF_STATES),
        "ihte_soft_imported": ihte_imported,
        "falsification_soft_imported": bool(fals_map or ife_slice),
        "update_ms": update_ms,
        "metrics": {
            "update_ms": update_ms,
            "belief_count": len(beliefs),
            "mean_posterior": mean_post,
            "mean_confidence": mean_conf,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "gate": "Analysts receive calibrated institutional beliefs — not fixed binary support labels.",
        "learning_hook": {"feed_into": "ILM", "stage": "institutional_belief_update"},
    }
    remember_belief(row)
    return row


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": BBCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_update_ms_target": MAX_UPDATE_MS_TARGET,
        "belief_states": list(BELIEF_STATES),
        "memory": memory_stats(),
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Institutional Falsification Engine",
        "executes_before": "Business / Financial / Valuation opinions",
        "law": PRIMARY_QUESTION,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "flags": flags_dict()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "bbce_version": BBCE_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    return generate_for_question(question, body)


def dashboard() -> dict[str, Any]:
    demos = [
        "Should I buy HDFC Bank?",
        "Is Nifty IT expensive versus history?",
        "Compare TCS vs Infosys",
    ]
    samples = []
    for q in demos:
        row = generate_for_question(q, {})
        samples.append(
            {
                "question": q,
                "belief_count": row.get("belief_count"),
                "drift_summary": row.get("drift_summary"),
                "beliefs": [
                    {
                        "hypothesis_id": b.get("hypothesis_id"),
                        "hypothesis": b.get("hypothesis"),
                        "prior_belief": b.get("prior_belief"),
                        "posterior_belief": b.get("posterior_belief"),
                        "belief_state": b.get("belief_state"),
                        "confidence": b.get("confidence"),
                        "uncertainty": (b.get("uncertainty") or {}).get("overall_uncertainty"),
                        "drift": b.get("drift"),
                        "history": (b.get("history") or [])[:5],
                    }
                    for b in _safe_list(row.get("beliefs"))
                ],
                "update_ms": row.get("update_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "bbce_version": BBCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": PRIMARY_QUESTION,
        "belief_states": list(BELIEF_STATES),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/belief-engine"],
        "api_prefix": "/v1/belief-engine",
        "display": {
            "question": "↓",
            "hypothesis": "↓",
            "prior_belief": "↓",
            "posterior_belief": "↓",
            "belief_state": "↓",
            "confidence": "↓",
            "uncertainty": "↓",
            "history": "↓",
        },
        "law": "Confidence evolves as evidence accumulates.",
        "not_a_top_level_intelligence_layer": True,
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


# --- Quality gates ---

_TYPES = ["Business", "Financial", "Valuation", "Macro", "Risk", "Portfolio", "Competitive", "Forecast", "Industry"]
_NAMES = [
    "HDFC Bank",
    "Infosys",
    "TCS",
    "Reliance",
    "SBI",
    "ICICI Bank",
    "Wipro",
    "Titan",
    "ITC",
    "Axis Bank",
]


def _expanded_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    i = 0
    templates = [
        ("{name} possesses a durable franchise advantage versus peers.", "Business", 0.8, 88, 60),
        ("Current valuation of {name} already reflects quality.", "Valuation", 0.6, 78, 55),
        ("Credit costs at {name} remain structurally benign.", "Financial", 0.7, 82, 64),
        ("Macro easing transmits to {name} via NIM and volumes.", "Macro", 0.55, 70, 50),
        ("Regulatory risk could invalidate the thesis for {name}.", "Risk", 0.45, 65, 70),
        ("Adding {name} concentrates existing portfolio factor exposure.", "Portfolio", 0.5, 68, 58),
    ]
    while len(cases) < BENCHMARK_MIN_BELIEFS + 20:
        tmpl, typ, conf, support, contra = templates[i % len(templates)]
        typ = _TYPES[i % len(_TYPES)]
        name = _NAMES[i % len(_NAMES)]
        # Vary evidence mix to exercise belief states
        effects = [
            {"id": f"E{i}-1", "effect": "Confirms" if i % 5 else "Supports", "text": "confirming metric"},
            {"id": f"E{i}-2", "effect": "Supports", "text": "supporting trend"},
            {"id": f"E{i}-3", "effect": "Weakly Supports", "text": "weak support"},
            {"id": f"E{i}-4", "effect": "Contradicts" if i % 4 else "Questions", "text": "challenge"},
            {"id": f"E{i}-5", "effect": "Questions", "text": "doubt"},
        ]
        if i % 7 == 0:
            effects.append({"id": f"E{i}-6", "effect": "Refutes", "text": "refuting observation"})
        cases.append(
            {
                "id": f"BH-{i+1:05d}",
                "type": typ,
                "hypothesis": tmpl.format(name=name),
                "initial_confidence": conf,
                "support_score": support,
                "contradiction_score": contra,
                "supporting_evidence": [{"id": f"S{j}"} for j in range(5)],
                "contradicting_evidence": [{"id": f"C{j}"} for j in range(2)],
                "missing_evidence": ["gap"] if i % 3 == 0 else [],
                "evidence_effects": effects,
                "uncertainty": {"conflict_intensity": 0.35, "known_unknowns": ["x"], "missing_evidence": []},
                "falsification": {"severity": ["survived", "stressed", "weakened", "inconclusive"][i % 4]},
            }
        )
        i += 1
    return cases


def quality_gates() -> dict[str, Any]:
    cases = _expanded_cases()[:BENCHMARK_MIN_BELIEFS]
    passed = 0
    prior_ok = state_ok = cal_ok = hist_ok = drift_ok = 0
    timed: list[float] = []
    state_counts: dict[str, int] = {}
    failures: list[dict[str, Any]] = []

    for c in cases:
        t0 = time.perf_counter()
        fals = c.pop("falsification", None)
        belief = update_belief(c, falsification=fals)
        # restore for safety (c mutated) — not needed further
        elapsed = _ms(t0)
        timed.append(elapsed)

        errs: list[str] = []
        if belief.get("prior_belief") is None or belief.get("posterior_belief") is None:
            errs.append("prior_posterior")
        else:
            prior_ok += 1
        state = belief.get("belief_state")
        if state not in BELIEF_STATES:
            errs.append("state")
        else:
            state_ok += 1
            state_counts[state] = state_counts.get(state, 0) + 1
        if not belief.get("calibration") or belief.get("confidence") is None:
            errs.append("calibration")
        else:
            cal_ok += 1
        if not belief.get("history") or len(belief.get("history") or []) < 2:
            errs.append("history")
        else:
            hist_ok += 1
        if not belief.get("drift") or "drift_level" not in (belief.get("drift") or {}):
            errs.append("drift")
        else:
            drift_ok += 1
        # Consistency: state matches posterior band
        if state != belief_state_from_posterior(float(belief.get("posterior_belief") or 0.5)):
            errs.append("state_consistency")

        if not errs:
            passed += 1
        elif len(failures) < 20:
            failures.append({"id": c.get("id"), "errors": errs, "state": state})

    total = len(cases)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    return {
        "ok": (
            prior_ok / total >= 1.0
            and state_ok / total >= 1.0
            and cal_ok / total >= 1.0
            and hist_ok / total >= 1.0
            and drift_ok / total >= 1.0
            and passed / total >= 0.99
            and total >= BENCHMARK_MIN_BELIEFS
            and avg_ms <= MAX_UPDATE_MS_TARGET
            and len(state_counts) >= 3
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "prior_posterior_consistency": round(prior_ok / total, 4) if total else 0.0,
        "belief_state_coverage": round(state_ok / total, 4) if total else 0.0,
        "calibration_reporting": round(cal_ok / total, 4) if total else 0.0,
        "history_tracking": round(hist_ok / total, 4) if total else 0.0,
        "drift_detection": round(drift_ok / total, 4) if total else 0.0,
        "beliefs_updated": total,
        "state_counts": state_counts,
        "avg_update_ms": avg_ms,
        "p95_update_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_update_ms": MAX_UPDATE_MS_TARGET,
        "failures_sample": failures,
        "rule": "Institutional confidence evolves — beliefs are calibrated posteriors, not binary labels.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    try:
        row = generate_for_question(question or "", dict(payload or {}))
        beliefs = []
        for b in _safe_list(row.get("beliefs"))[:8]:
            beliefs.append(
                {
                    "hypothesis_id": b.get("hypothesis_id"),
                    "hypothesis": b.get("hypothesis"),
                    "type": b.get("type"),
                    "prior_belief": b.get("prior_belief"),
                    "posterior_belief": b.get("posterior_belief"),
                    "posterior_belief_pct": b.get("posterior_belief_pct"),
                    "belief_state": b.get("belief_state"),
                    "confidence": b.get("confidence"),
                    "confidence_pct": b.get("confidence_pct"),
                    "uncertainty": {
                        "overall_uncertainty": (b.get("uncertainty") or {}).get("overall_uncertainty"),
                        "band": (b.get("uncertainty") or {}).get("band"),
                    },
                    "drift": b.get("drift"),
                    "delta": b.get("delta"),
                    "decision_hint": b.get("decision_hint"),
                    "history": (b.get("history") or [])[:6],
                }
            )
        return {
            "belief_engine": {
                "enabled": True,
                "version": BBCE_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "executes_after": "Institutional Falsification Engine",
                "executes_before": "Business / Financial / Valuation opinions",
                "primary_question": PRIMARY_QUESTION,
                "question": row.get("question"),
                "belief_count": row.get("belief_count"),
                "beliefs": beliefs,
                "drift_summary": row.get("drift_summary"),
                "registry": row.get("registry"),
                "update_ms": row.get("update_ms"),
                "belief_states": list(BELIEF_STATES),
                "gate": row.get("gate"),
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "belief_engine": {
                "enabled": True,
                "version": BBCE_VERSION,
                "error": str(exc)[:240],
            }
        }
