"""Phase 1 — Evidence-First Execution Governance.

Pipeline (no engine replaced, nothing bypassed):

    Question → Classification → Entity Resolution → Evidence Contract
      → Framework Selection → Evidence Validation → Framework Execution
      → Committee → Editorial → Telemetry

Editorial is never allowed before framework execution.
Architecture v1.0.1 LOCKED — soft helper under institutional_reasoning.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from institutional_reasoning.evidence_contracts import (
    CONTRACTS_VERSION,
    EDUCATION_TYPES,
    classify_question,
    clarification_required,
    contract_for,
    forbidden_claim_hits,
    resolve_entities,
)
from institutional_reasoning.evidence_validation import VALIDATION_VERSION, validate_contract

GOVERNANCE_VERSION = "execution-governance-v1.0.0"


def _attach_justification(record: dict[str, Any]) -> dict[str, Any]:
    """Every governed answer carries its own reasoning graph (for AGIB itself)."""
    try:
        from institutional_reasoning.justification_graph import build_justification_graph

        record["justification_graph"] = build_justification_graph(record)
    except Exception:
        record["justification_graph"] = {}
    return record

# Framework requirement → contract evidence field (single source of truth).
FRAMEWORK_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "rel_val_damodaran": {
        "name": "Damodaran Relative Valuation",
        "author": "Damodaran",
        "version": "1.0.0",
        "requires": ("current_pe", "peer_pe"),
        "produces": ("premium_discount", "confidence"),
        "invalid_for_entity_types": (),
    },
    "hist_multiples": {
        "name": "Historical Multiples Percentile",
        "author": "Institutional",
        "version": "1.0.0",
        "requires": ("current_pe", "historical_pe", "historical_percentile"),
        "produces": ("historical_percentile", "confidence"),
        "invalid_for_entity_types": (),
    },
    "margin_of_safety": {
        "name": "Graham Margin of Safety",
        "author": "Graham",
        "version": "1.0.0",
        "requires": ("current_pe", "historical_pe"),
        "produces": ("mos_pct", "confidence"),
        "invalid_for_entity_types": (),
    },
    "dcf_applicability": {
        "name": "DCF Applicability Test",
        "author": "Damodaran",
        "version": "1.0.0",
        "requires": (),
        "produces": ("applicable", "reason"),
        "invalid_for_entity_types": ("Index",),
        "invalid_for_sectors": ("bank", "insurance", "nbfc"),
    },
    "peer_comparison": {
        "name": "Peer Comparison",
        "author": "Institutional",
        "version": "1.0.0",
        "requires": ("peer_set", "comparable_metrics"),
        "produces": ("peer_rank", "confidence"),
    },
    "business_quality_roic": {
        "name": "ROIC Quality Assessment",
        "author": "Institutional",
        "version": "1.0.0",
        "requires": ("roic", "margins"),
        "produces": ("quality_grade", "confidence"),
    },
    "accounting_quality_screen": {
        "name": "Accounting Quality Screen",
        "author": "Institutional",
        "version": "1.0.0",
        "requires": ("cash_conversion", "leverage", "earnings_quality"),
        "produces": ("accounting_flags", "confidence"),
    },
}

FRAMEWORKS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "valuation": ("rel_val_damodaran", "hist_multiples", "margin_of_safety", "dcf_applicability"),
    "investment_decision": (
        "rel_val_damodaran",
        "hist_multiples",
        "margin_of_safety",
        "business_quality_roic",
    ),
    "comparison": ("peer_comparison", "rel_val_damodaran"),
    "business_quality": ("business_quality_roic",),
    "financial_quality": ("accounting_quality_screen",),
    "portfolio": (),
    "macro": (),
    "sector": (),
    "risk": (),
    "forecast": (),
    "education": (),
}


def select_frameworks_for(question_type: str) -> list[dict[str, Any]]:
    """Legacy fixed map — retained for compatibility; prefer IKI planner."""
    ids = FRAMEWORKS_BY_TYPE.get(str(question_type or "").lower(), ())
    out: list[dict[str, Any]] = []
    for fid in ids:
        spec = FRAMEWORK_REQUIREMENTS.get(fid)
        if not spec:
            continue
        out.append({"framework_id": fid, **spec})
    return out


def _sector_of(entity: dict[str, Any] | None) -> str | None:
    try:
        from institutional_reasoning.iki.applicability import infer_sector

        ent = entity or {}
        return infer_sector(ent.get("entity_id"), ent.get("entity_type"))
    except Exception:
        return None


def _execute_framework(
    spec: dict[str, Any],
    *,
    validation: dict[str, Any],
    entity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Structured framework result — never prose."""
    fid = spec["framework_id"]
    observed = set(validation.get("observed") or [])
    rejected = validation.get("rejected") or {}
    entity_type = str((entity or {}).get("entity_type") or "")
    sector = _sector_of(entity)

    # Phase 3 pre-rejection from applicability engine
    if spec.get("pre_rejected"):
        return {
            "framework_id": fid,
            "name": spec.get("name"),
            "author": spec.get("author"),
            "framework_version": spec.get("version"),
            "status": "not_applicable",
            "outputs": {
                "applicable": False,
                "reason": "; ".join(spec.get("pre_reject_reasons") or ["applicability rejected"]),
                "alternatives": spec.get("alternatives") or spec.get("alternative_frameworks") or [],
                "applicability_score": spec.get("applicability_score"),
            },
            "required_evidence": list(spec.get("requires") or ()),
            "missing_evidence": [],
            "confidence": None,
        }

    # Applicability first — a rejected method must not be forced.
    invalid_types = tuple(spec.get("invalid_for_entity_types") or ())
    if entity_type and entity_type in invalid_types:
        return {
            "framework_id": fid,
            "name": spec.get("name"),
            "author": spec.get("author"),
            "framework_version": spec.get("version"),
            "status": "not_applicable",
            "outputs": {"applicable": False, "reason": f"{spec.get('name')} invalid for {entity_type}"},
            "required_evidence": list(spec.get("requires") or ()),
            "missing_evidence": [],
            "confidence": None,
        }

    invalid_sectors = tuple(spec.get("invalid_for_sectors") or ())
    if sector and sector in invalid_sectors:
        alts = list(spec.get("alternative_frameworks") or [])
        reason = f"{spec.get('name')} invalid for sector '{sector}'"
        if fid in {"dcf_applicability", "dcf_fcff"} and sector in {"bank", "insurance", "nbfc"}:
            reason = "Financial institution — DCF is the wrong primary model"
            if "residual_income" not in alts:
                alts = ["residual_income"] + alts
        return {
            "framework_id": fid,
            "name": spec.get("name"),
            "author": spec.get("author"),
            "framework_version": spec.get("version"),
            "status": "not_applicable",
            "outputs": {"applicable": False, "reason": reason, "alternatives": alts},
            "required_evidence": list(spec.get("requires") or ()),
            "missing_evidence": [],
            "confidence": None,
        }

    required = tuple(spec.get("requires") or ())
    missing = [r for r in required if r not in observed]
    if missing:
        return {
            "framework_id": fid,
            "name": spec.get("name"),
            "author": spec.get("author"),
            "framework_version": spec.get("version"),
            "status": "insufficient_evidence",
            "outputs": {
                "applicability_score": spec.get("applicability_score"),
                "confidence_band": (spec.get("confidence") or {}).get("band"),
            },
            "required_evidence": list(required),
            "missing_evidence": missing,
            "rejection_reasons": {m: rejected.get(m, "not_found") for m in missing},
            "confidence": None,
        }

    verdict_map = {v["field"]: v for v in validation.get("field_verdicts") or []}
    outputs: dict[str, Any] = {}
    confidence = 0.6 + 0.1 * min(len(required), 3)
    cal = spec.get("confidence") or {}
    if cal.get("weight_multiplier"):
        confidence = min(0.95, confidence * float(cal["weight_multiplier"]) / 0.9)

    def num(field_name: str) -> float | None:
        v = (verdict_map.get(field_name) or {}).get("value")
        try:
            return float(v)
        except Exception:
            return None

    if fid == "rel_val_damodaran":
        cur, peer = num("current_pe"), num("peer_pe")
        if cur is not None and peer:
            outputs["premium_discount_pct"] = round((cur / peer - 1) * 100, 2)
            outputs["current_pe"] = cur
            outputs["peer_pe"] = peer
    elif fid == "hist_multiples":
        cur, hist, pct = num("current_pe"), num("historical_pe"), num("historical_percentile")
        if cur is not None and hist:
            outputs["vs_history_pct"] = round((cur / hist - 1) * 100, 2)
        if pct is not None:
            outputs["historical_percentile"] = pct
        outputs["current_pe"] = cur
        outputs["historical_pe"] = hist
    elif fid == "margin_of_safety":
        cur, hist = num("current_pe"), num("historical_pe")
        if cur and hist:
            outputs["implied_mos_pct"] = round((hist / cur - 1) * 100, 2)
    elif fid == "dcf_applicability":
        outputs["applicable"] = True
        outputs["reason"] = "cash-flow forecastable entity"
    elif fid == "dcf_fcff":
        outputs["status"] = "ready_or_insufficient"
        outputs["note"] = "Full DCF requires complete FCF/WACC pack"
        outputs["confidence_band"] = cal.get("band") or "Medium"
    elif fid == "residual_income":
        outputs["preferred_for"] = sector or "financials"
        outputs["roe"] = num("roe")
        outputs["note"] = "Residual income path for financial institutions"
    elif fid == "peer_comparison":
        outputs["peer_set_present"] = True
    elif fid == "business_quality_roic":
        outputs["roic"] = num("roic")
        outputs["margins"] = num("margins")
    elif fid == "buffett_quality":
        outputs["roic"] = num("roic")
        outputs["margins"] = num("margins")
        outputs["stance"] = "supports" if (num("roic") or 0) > 20 else "conditional"
    elif fid == "graham_net_net":
        outputs["signal"] = "asset_floor_check"
    elif fid == "accounting_quality_screen":
        outputs["cash_conversion"] = num("cash_conversion")
        outputs["leverage"] = num("leverage")
        outputs["earnings_quality"] = num("earnings_quality")

    outputs["applicability_score"] = spec.get("applicability_score")
    outputs["confidence_band"] = cal.get("band")

    return {
        "framework_id": fid,
        "name": spec.get("name"),
        "author": spec.get("author"),
        "framework_version": spec.get("version"),
        "status": "executed",
        "outputs": outputs,
        "required_evidence": list(required),
        "missing_evidence": [],
        "confidence": round(min(confidence, 0.95), 2),
        "provenance": validation.get("provenance") or [],
    }


def _committee(results: list[dict[str, Any]], *, question_type: str, debate: dict[str, Any] | None = None) -> dict[str, Any]:
    """Committee consumes only framework outputs; cannot invent or override."""
    executed = [r for r in results if r["status"] == "executed"]
    insufficient = [r for r in results if r["status"] == "insufficient_evidence"]
    not_applicable = [r for r in results if r["status"] == "not_applicable"]

    findings: list[str] = []
    disagreements: list[str] = []

    hist = next((r for r in executed if r["framework_id"] == "hist_multiples"), None)
    rel = next((r for r in executed if r["framework_id"] == "rel_val_damodaran"), None)

    if hist:
        pctile = hist["outputs"].get("historical_percentile")
        vs_hist = hist["outputs"].get("vs_history_pct")
        if pctile is not None:
            findings.append(
                f"Historical multiples: {pctile:.0f}th percentile versus own history."
            )
        elif vs_hist is not None:
            findings.append(f"Historical multiples: {vs_hist:+.1f}% versus historical average.")
    if rel:
        prem = rel["outputs"].get("premium_discount_pct")
        if prem is not None:
            findings.append(
                f"Relative valuation: {prem:+.1f}% versus peer multiple "
                f"({rel['outputs'].get('current_pe')} vs {rel['outputs'].get('peer_pe')})."
            )

    # Explicit disagreement handling (Test 5)
    if hist and rel:
        h_rich = (hist["outputs"].get("historical_percentile") or 0) >= 70 or (
            hist["outputs"].get("vs_history_pct") or 0
        ) > 10
        r_cheap = (rel["outputs"].get("premium_discount_pct") or 0) < -5
        h_cheap = (hist["outputs"].get("historical_percentile") or 100) <= 30 or (
            hist["outputs"].get("vs_history_pct") or 0
        ) < -10
        r_rich = (rel["outputs"].get("premium_discount_pct") or 0) > 5
        if (h_rich and r_cheap) or (h_cheap and r_rich):
            disagreements.append(
                "Frameworks disagree: own-history and peer-relative valuation point in "
                "opposite directions. Both readings are reported; neither is suppressed."
            )

    for r in insufficient:
        findings.append(
            f"{r['name']}: insufficient evidence (missing {', '.join(r['missing_evidence'][:4])})."
        )
    for r in not_applicable:
        findings.append(f"{r['name']}: not applicable — {r['outputs'].get('reason')}.")

    # Phase 3 debate / decision-policy resolution
    if debate:
        for c in debate.get("conflicts") or []:
            disagreements.append(str(c.get("explanation") or ""))
        if debate.get("resolution"):
            findings.append(str(debate["resolution"]))

    contract = contract_for(question_type)
    can_conclude = bool(executed) and not insufficient
    partial = bool(executed) and bool(insufficient)

    if not executed:
        conclusion = (
            "Insufficient evidence: no required framework could execute. "
            "No valuation, quality or decision conclusion is issued."
        )
        stance = "Insufficient evidence"
        # Applicability-only conclusions reserved for explicit applicability questions
        # (e.g. "Should DCF be used for banks?") — never for ordinary valuation asks.
        applicability_question = bool(debate and debate.get("resolution")) and any(
            f["framework_id"] in {"dcf_applicability", "dcf_fcff", "residual_income"}
            and f["status"] == "not_applicable"
            for f in not_applicable
        )
        # Only elevate stance when committee was asked about method choice via debate resolution
        # AND at least one method reject is explanatory (handled by caller via question type hints).
        if applicability_question and debate.get("resolution") and "residual" in str(
            debate.get("resolution") or ""
        ).lower():
            # Soft signal — caller still gates narrative on question intent
            findings.append(str(debate["resolution"]))
            conclusion = " ".join(findings)
            stance = "Applicability-resolved"
    elif partial:
        missing_names = sorted({m for r in insufficient for m in r["missing_evidence"]})
        conclusion = (
            "Partial evidence only. "
            + " ".join(findings)
            + f" Missing: {', '.join(missing_names[:6])}. "
            "A full conclusion is withheld."
        )
        stance = "Partial evidence"
    else:
        conclusion = " ".join(findings) or "Frameworks executed."
        stance = "Evidence-supported"

    if disagreements:
        conclusion = conclusion + " " + " ".join(disagreements)

    return {
        "stance": stance,
        "conclusion": conclusion,
        "findings": findings,
        "disagreements": disagreements,
        "executed_count": len(executed),
        "insufficient_count": len(insufficient),
        "not_applicable_count": len(not_applicable),
        "can_conclude": can_conclude,
        "forbidden_claims": list(contract.forbidden_claims),
        "dominant_framework": (debate or {}).get("dominant_framework"),
        "decision_policy": (debate or {}).get("policy"),
    }


def govern_answer(
    question: str,
    *,
    ticker_hint: str | None = None,
    entity_resolution_pack: dict[str, Any] | None = None,
    packs: dict[str, dict[str, Any]] | None = None,
    academy: dict[str, Any] | None = None,
    build_institutional_evidence: bool = True,
    build_portfolio_intelligence: bool = True,
    build_outcome_intelligence: bool = True,
    question_type_override: str | None = None,
) -> dict[str, Any]:
    """Run the full governed pipeline; returns structured governance record.

    Soft-wire: `question_type_override` lets Ask Pipeline 2.0 Intent Resolution
    select education / non-valuation paths without rewriting contract tables.
    """
    started = time.time()
    run_id = f"fer_{uuid.uuid4().hex[:16]}"
    classification = classify_question(question)
    if question_type_override:
        classification = {
            **classification,
            "question_type": str(question_type_override).lower(),
            "confidence": max(float(classification.get("confidence") or 0), 0.95),
            "reason": "ask_pipeline_intent_resolution_override",
            "overridden": True,
            "legacy_question_type": classification.get("question_type"),
        }
    qtype = classification["question_type"]
    contract = contract_for(qtype)

    # Education path bypasses evidence contract + frameworks + committee.
    if qtype in EDUCATION_TYPES:
        return _attach_justification(
            {
                "run_id": run_id,
                "governance_version": GOVERNANCE_VERSION,
                "question": str(question or "")[:500],
                "question_type": qtype,
                "classification": classification,
                "path": "education",
                "entity": None,
                "contract": contract.to_dict(),
                "validation": None,
                "frameworks": [],
                "committee": None,
                "narrative_allowed": True,
                "editorial_mode": "explain_academy",
                "academy_available": bool(academy),
                "execution_ms": int((time.time() - started) * 1000),
            }
        )

    entities = resolve_entities(
        question,
        ticker_hint=ticker_hint,
        entity_resolution_pack=entity_resolution_pack,
    )
    clarify = clarification_required(classification, entities)
    if clarify.get("required"):
        return _attach_justification(
            {
                "run_id": run_id,
                "governance_version": GOVERNANCE_VERSION,
                "question": str(question or "")[:500],
                "question_type": qtype,
                "classification": classification,
                "path": "clarification",
                "entity": entities.get("primary"),
                "entity_resolution": entities,
                "contract": contract.to_dict(),
                "validation": None,
                "frameworks": [],
                "committee": {
                    "stance": "Clarification required",
                    "conclusion": clarify.get("message"),
                    "can_conclude": False,
                },
                "narrative_allowed": False,
                "editorial_mode": "clarify_only",
                "clarification": clarify,
                "execution_ms": int((time.time() - started) * 1000),
            }
        )

    primary = entities.get("primary") or {}
    entity_id = primary.get("entity_id")

    # Phase 2 — Institutional Evidence Pack binding.
    # Frameworks consume validated packs; they never fetch.
    packs = dict(packs or {})
    if build_institutional_evidence:
        try:
            from institutional_reasoning.institutional_evidence.production import (
                package_for_governance,
            )

            ie_pkg = package_for_governance(
                entity_id,
                entity_name=primary.get("entity_name"),
                entity_type=primary.get("entity_type"),
                existing_packs=packs,
            )
            if ie_pkg.get("found"):
                packs["institutional_evidence"] = ie_pkg
        except Exception:
            pass

    # Phase 5 — Institutional Portfolio Intelligence pack binding.
    # Fills exposure / risk_contribution / downside_case / expected_return
    # so portfolio & investment_decision contracts can execute without redesign.
    if build_portfolio_intelligence and entity_id:
        try:
            from institutional_reasoning.ipi.production import (
                package_for_governance as ipi_package_for_governance,
            )

            ipi_pkg = ipi_package_for_governance(
                entity_id,
                entity_name=primary.get("entity_name"),
                existing_packs=packs,
            )
            if ipi_pkg.get("found"):
                packs["institutional_portfolio"] = ipi_pkg
        except Exception:
            pass

    validation = validate_contract(
        question_type=qtype,
        entity_id=entity_id,
        packs=packs,
    )

    # Phase 3 — Institutional Knowledge Intelligence planner.
    # Applicability scoring → execution order → debate (not fixed type maps).
    iki_plan: dict[str, Any] = {}
    evidence_for_iki = packs.get("institutional_evidence") or {}
    try:
        from institutional_reasoning.iki.planner import finalize_with_debate, plan as iki_plan_fn

        iki_plan = iki_plan_fn(
            question=question,
            question_type=qtype,
            entity=primary,
            evidence=evidence_for_iki,
        )
        specs = list(iki_plan.get("execution_order") or [])
    except Exception:
        specs = select_frameworks_for(qtype)

    results = [
        _execute_framework(spec, validation=validation, entity=primary) for spec in specs
    ]
    if iki_plan:
        try:
            from institutional_reasoning.iki.planner import finalize_with_debate

            iki_plan = finalize_with_debate(
                iki_plan, framework_results=results, evidence=evidence_for_iki
            )
        except Exception:
            pass
    committee = _committee(
        results, question_type=qtype, debate=(iki_plan or {}).get("debate")
    )

    executed_any = any(r["status"] == "executed" for r in results)
    # Contract completeness governs narrative permission for gated types.
    narrative_allowed = bool(executed_any and validation.get("complete"))
    if not specs:
        # Types without executable frameworks: keep research narrative gated.
        # Phase 5 portfolio decisions are issued via IPI/PDG, not an ungated DJG.
        narrative_allowed = False
    # Applicability-only answers (e.g. DCF rejected for banks) may narrate the rejection
    # only when the question is about method applicability — not ordinary valuation asks.
    q_l = str(question or "").lower()
    applicability_intent = any(
        k in q_l
        for k in (
            "should dcf",
            "dcf be used",
            "dcf applicable",
            "is dcf",
            "dcf wrong",
            "invalidates dcf",
            "which framework",
            "framework dominate",
        )
    )
    if (committee or {}).get("stance") == "Applicability-resolved" and applicability_intent:
        narrative_allowed = True
    elif (committee or {}).get("stance") == "Applicability-resolved" and not applicability_intent:
        # Downgrade — do not leak narrative on wrong-entity / placeholder valuation asks
        committee["stance"] = "Insufficient evidence"
        narrative_allowed = False

    record = {
        "run_id": run_id,
        "governance_version": GOVERNANCE_VERSION,
        "question": str(question or "")[:500],
        "question_type": qtype,
        "classification": classification,
        "path": "research",
        "entity": primary or None,
        "entity_resolution": entities,
        "contract": contract.to_dict(),
        "contract_version": CONTRACTS_VERSION,
        "validation_version": VALIDATION_VERSION,
        "validation": validation,
        "frameworks": results,
        "committee": committee,
        "narrative_allowed": narrative_allowed,
        "editorial_mode": "explain_only" if narrative_allowed else "report_insufficient",
        "missing_evidence": validation.get("missing") or [],
        "institutional_evidence": (packs.get("institutional_evidence") or {}),
        "institutional_portfolio": (packs.get("institutional_portfolio") or {}),
        "iki": iki_plan,
        "execution_ms": int((time.time() - started) * 1000),
    }
    record = _attach_justification(record)

    # Phase 5 — Portfolio decision (research package → IPI → PDG).
    # Soft-wire: portfolio / investment_decision / risk questions, or when
    # the question explicitly asks about weights / investable amounts.
    q_l2 = str(question or "").lower()
    wants_portfolio = qtype in {"portfolio", "investment_decision", "risk"} or any(
        k in q_l2
        for k in (
            "invest £",
            "invest $",
            "invest ₹",
            "position siz",
            "portfolio",
            "weight",
            "exposure impact",
            "should we invest",
            "should i invest",
        )
    )
    if build_portfolio_intelligence and entity_id and wants_portfolio:
        try:
            from institutional_reasoning.ipi.decision import decide_portfolio

            ipi_decision = decide_portfolio(
                entity_id=entity_id,
                entity_name=primary.get("entity_name"),
                research_record=record,
                existing_packs=packs,
                persist_memory=True,
                track_outcome=build_outcome_intelligence,
            )
            record["ipi"] = ipi_decision
            record["portfolio_decision_graph"] = ipi_decision.get("portfolio_decision_graph") or {}
            # Phase 6 — surface outcome lifecycle handle (evaluation is explicit later).
            if build_outcome_intelligence and (ipi_decision.get("ioi") or {}).get("decision_id"):
                record["ioi"] = ipi_decision.get("ioi")
            # Portfolio narrative: never Buy/Sell; surface committee conclusion.
            rec = ipi_decision.get("recommendation") or {}
            if rec.get("conclusion"):
                record["portfolio_recommendation"] = rec
                if qtype in {"portfolio", "investment_decision"}:
                    # Prefer portfolio committee language over research Buy/Sell leakage
                    if record.get("committee") and not record["committee"].get("can_conclude"):
                        record["committee"] = {
                            **record["committee"],
                            "stance": rec.get("action") or "Withhold",
                            "conclusion": rec.get("conclusion"),
                            "can_conclude": bool((ipi_decision.get("committee") or {}).get("can_recommend")),
                        }
        except Exception:
            record.setdefault("ipi", {})
            record.setdefault("portfolio_decision_graph", {})

    try:
        from institutional_reasoning.observability import record as obs_record

        obs_record(
            "govern_answer_total",
            latency_ms=float(record.get("execution_ms") or 0),
        )
        if not record.get("narrative_allowed"):
            obs_record("govern_answer_withheld")
        else:
            obs_record("govern_answer_narrative")
        if record.get("institutional_evidence"):
            obs_record("evidence_packs_built")
        if (record.get("institutional_evidence") or {}).get("risk_drivers") or (
            (record.get("institutional_evidence") or {}).get("institutional_evidence") or {}
        ).get("risk_drivers"):
            obs_record("derived_risk_hits")
        if record.get("ipi"):
            obs_record("portfolio_decisions")
            if (record.get("ipi") or {}).get("withheld"):
                obs_record("portfolio_withheld")
        if not (record.get("validation") or {}).get("complete", True):
            obs_record("contract_incomplete")
    except Exception:
        pass

    return record


def governed_executive(record: dict[str, Any]) -> str:
    """Executive text derived only from framework/committee outputs."""
    committee = record.get("committee") or {}
    if record.get("path") == "clarification":
        return str(committee.get("conclusion") or "Clarification required.")
    if record.get("path") == "education":
        return ""
    return str(committee.get("conclusion") or "Insufficient evidence.")


def enforce_editorial(
    *,
    text: str | None,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Editorial may explain, never invent. Strip unsupported forbidden claims."""
    if record.get("path") == "education":
        return {"text": text, "blocked": False, "violations": []}
    qtype = str(record.get("question_type") or "")
    allowed = bool(record.get("narrative_allowed"))
    violations = forbidden_claim_hits(text or "", qtype)
    if allowed or not violations:
        return {"text": text, "blocked": False, "violations": violations}
    return {
        "text": governed_executive(record),
        "blocked": True,
        "violations": violations,
        "reason": "forbidden_claim_without_executed_framework",
    }


def telemetry_rows(record: dict[str, Any], *, answer_id: str | None = None) -> list[dict[str, Any]]:
    """One immutable row per framework attempt (never updated)."""
    rows: list[dict[str, Any]] = []
    validation = record.get("validation") or {}
    entity = record.get("entity") or {}
    committee = record.get("committee") or {}
    frameworks = record.get("frameworks") or []
    base = {
        "run_id": record.get("run_id"),
        "question": record.get("question"),
        "question_type": record.get("question_type"),
        "question_confidence": (record.get("classification") or {}).get("confidence"),
        "entity_id": entity.get("entity_id"),
        "entity_name": entity.get("entity_name"),
        "entity_type": entity.get("entity_type"),
        "entity_confidence": entity.get("confidence"),
        "evidence_contract_version": record.get("contract_version"),
        "validation_version": record.get("validation_version"),
        "evidence_provenance": validation.get("provenance") or [],
        "committee_stance": committee.get("stance"),
        "committee_conclusion": (committee.get("conclusion") or "")[:2000],
        "narrative_allowed": record.get("narrative_allowed"),
        "answer_id": answer_id,
        "execution_ms": record.get("execution_ms"),
        "governance_version": record.get("governance_version"),
        "path": record.get("path"),
    }
    djg = record.get("justification_graph") or {}
    if djg:
        try:
            from institutional_reasoning.justification_graph import graph_telemetry_row

            base["justification_graph"] = graph_telemetry_row(djg, run_id=record.get("run_id"))
        except Exception:
            pass
    if not frameworks:
        rows.append(
            {
                **base,
                "framework_id": None,
                "framework_name": None,
                "framework_version": None,
                "required_evidence": validation.get("required") or [],
                "observed_evidence": validation.get("observed") or [],
                "missing_evidence": validation.get("missing") or [],
                "validation_result": validation or {},
                "execution_status": record.get("path") or "no_frameworks",
                "failure_reason": (record.get("clarification") or {}).get("reason"),
                "confidence": None,
                "outputs": {},
            }
        )
        return rows
    for fw in frameworks:
        rows.append(
            {
                **base,
                "framework_id": fw.get("framework_id"),
                "framework_name": fw.get("name"),
                "framework_version": fw.get("framework_version"),
                "required_evidence": fw.get("required_evidence") or [],
                "observed_evidence": validation.get("observed") or [],
                "missing_evidence": fw.get("missing_evidence") or [],
                "validation_result": {
                    "coverage": validation.get("coverage"),
                    "complete": validation.get("complete"),
                    "rejected": validation.get("rejected") or {},
                    "field_verdicts": validation.get("field_verdicts") or [],
                },
                "execution_status": fw.get("status"),
                "failure_reason": (
                    ", ".join(f"{k}:{v}" for k, v in (fw.get("rejection_reasons") or {}).items())
                    or (fw.get("outputs") or {}).get("reason")
                ),
                "confidence": fw.get("confidence"),
                "outputs": fw.get("outputs") or {},
            }
        )
    return rows
