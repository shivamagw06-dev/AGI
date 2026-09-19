"""Grade one IES case against gold expectations."""

from __future__ import annotations

import re
from typing import Any

from institutional_reasoning.evidence_contracts import contract_for, forbidden_claim_hits
from institutional_reasoning.execution_governance import (
    enforce_editorial,
    govern_answer,
    governed_executive,
)
from institutional_reasoning.ies.schema import Case

_GUESS_PATTERNS = (
    re.compile(r"\bbest guess\b", re.I),
    re.compile(r"\broughly speaking\b", re.I),
    re.compile(r"\bassuming\b", re.I),
    re.compile(r"\bprobably\b", re.I),
    re.compile(r"\bI (would )?estimate\b", re.I),
)

_UNSUPPORTED_VAL = (
    "expensive",
    "cheap",
    "overvalued",
    "undervalued",
    "fair",
    "rich",
    "bargain",
)


def _fw_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f["framework_id"]: f for f in (record.get("frameworks") or []) if f.get("framework_id")}


def grade_case(case: Case) -> dict[str, Any]:
    """Run governance on a case and return structured grade."""
    import time

    t0 = time.time()
    record = govern_answer(
        case.question,
        ticker_hint=case.ticker_hint,
        packs=case.packs or {},
        build_institutional_evidence=case.build_institutional_evidence,
    )
    elapsed_ms = int((time.time() - t0) * 1000)
    gold = case.gold
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def ok(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})
        if not passed:
            failures.append(f"{name}: {detail}")

    # Question type
    if gold.question_types:
        ok(
            "question_type",
            record.get("question_type") in gold.question_types,
            f"got {record.get('question_type')}",
        )
    elif gold.question_type:
        ok(
            "question_type",
            record.get("question_type") == gold.question_type,
            f"got {record.get('question_type')}",
        )

    # Path
    if gold.paths:
        ok("path", record.get("path") in gold.paths, f"got {record.get('path')}")
    elif gold.path:
        ok("path", record.get("path") == gold.path, f"got {record.get('path')}")

    # Suite-specific soft passes for transparent insufficient (accounting / BQ without data)
    if case.suite in {"accounting", "business_quality"} and not gold.require_executed:
        fw_list = record.get("frameworks") or []
        executed_any = any(f.get("status") == "executed" for f in fw_list)
        insuff_any = any(f.get("status") == "insufficient_evidence" for f in fw_list)
        transparent = executed_any or insuff_any or record.get("path") == "clarification"
        ok("evidence_or_transparent", transparent, f"exec={executed_any} insuff={insuff_any}")
        if not executed_any:
            ok(
                "no_unsupported_when_insufficient",
                record.get("narrative_allowed") is not True
                or "insufficient" in str((record.get("committee") or {}).get("stance") or "").lower()
                or "partial" in str((record.get("committee") or {}).get("stance") or "").lower(),
                f"narrative={record.get('narrative_allowed')}",
            )

    # Entity
    ent = record.get("entity") or {}
    if gold.entity_id and record.get("path") not in {"clarification", "education"}:
        ok(
            "entity_id",
            (ent.get("entity_id") or "").upper() == gold.entity_id.upper(),
            f"got {ent.get('entity_id')}",
        )
    if gold.entity_type and ent.get("entity_type"):
        ok(
            "entity_type",
            ent.get("entity_type") == gold.entity_type,
            f"got {ent.get('entity_type')}",
        )

    # Education bypass
    if gold.education_bypass:
        ok("education_bypass", record.get("path") == "education", f"path={record.get('path')}")
        ok("no_validation", record.get("validation") is None, "validation present")
        ok("no_frameworks", not (record.get("frameworks") or []), "frameworks ran")

    fw = _fw_map(record)
    for fid in gold.require_executed:
        status = (fw.get(fid) or {}).get("status")
        ok(f"exec:{fid}", status == "executed", f"status={status}")
    for fid in gold.require_insufficient:
        status = (fw.get(fid) or {}).get("status")
        ok(f"insuff:{fid}", status == "insufficient_evidence", f"status={status}")
    for fid in gold.require_not_applicable:
        status = (fw.get(fid) or {}).get("status")
        ok(f"na:{fid}", status == "not_applicable", f"status={status}")
    for fid, status in (gold.framework_status or {}).items():
        got = (fw.get(fid) or {}).get("status")
        ok(f"status:{fid}", got == status, f"got={got}")

    if gold.narrative_allowed is not None:
        ok(
            "narrative_allowed",
            bool(record.get("narrative_allowed")) == bool(gold.narrative_allowed),
            f"got {record.get('narrative_allowed')}",
        )

    executive = governed_executive(record)
    committee = record.get("committee") or {}
    stance = str(committee.get("stance") or "")
    conclusion = str(committee.get("conclusion") or executive or "")

    # Insufficient transparency
    if gold.must_report_insufficient:
        transparent = (
            record.get("path") == "clarification"
            or "insufficient" in stance.lower()
            or "partial" in stance.lower()
            or "clarification" in stance.lower()
            or bool(record.get("missing_evidence"))
            or any(
                f.get("status") == "insufficient_evidence" for f in (record.get("frameworks") or [])
            )
        )
        ok("insufficient_transparency", transparent, f"stance={stance}")
        if gold.forbid_guessing:
            guessed = any(p.search(conclusion) for p in _GUESS_PATTERNS)
            ok("no_guessing", not guessed, conclusion[:120])
        if gold.must_list_missing and record.get("path") != "clarification":
            missing = record.get("missing_evidence") or []
            fw_missing = [
                m
                for f in (record.get("frameworks") or [])
                for m in (f.get("missing_evidence") or [])
            ]
            ok(
                "lists_missing",
                bool(missing or fw_missing) or "missing" in conclusion.lower() or "insufficient" in conclusion.lower(),
                f"missing={missing[:4]}",
            )
        ok(
            "no_full_narrative",
            record.get("narrative_allowed") is not True
            or record.get("path") == "clarification"
            or "insufficient" in stance.lower()
            or "partial" in stance.lower(),
            f"narrative={record.get('narrative_allowed')} stance={stance}",
        )

    # Unsupported claims / editorial
    unsupported = 0
    editorial_violations = 0
    if gold.unsupported_claims_forbidden and record.get("path") not in {"education"}:
        qtype = str(record.get("question_type") or gold.question_type or "")
        forbid = list(contract_for(qtype).forbidden_claims)
        if not record.get("narrative_allowed") and forbid:
            # Probe with a claim that is forbidden for THIS question type
            probe_claim = forbid[0]
            injected = enforce_editorial(
                text=f"Analysis conclusion: {probe_claim}.",
                record=record,
            )
            if injected.get("blocked"):
                ok("editorial_block", True)
            else:
                leaked = probe_claim.lower() in (injected.get("text") or "").lower()
                editorial_violations = 1 if leaked else 0
                ok("editorial_block", not leaked, f"probe={probe_claim}")
            if not (record.get("validation") or {}).get("complete"):
                hits = forbidden_claim_hits(conclusion, qtype)
                bad = [
                    h
                    for h in hits
                    if not re.search(
                        rf"(cannot|insufficient|withheld|missing|not).{{0,40}}{re.escape(h)}|{re.escape(h)}.{{0,40}}(cannot|insufficient|withheld)",
                        conclusion.lower(),
                    )
                ]
                unsupported = len(bad)
                ok("no_unsupported_conclusion", unsupported == 0, f"hits={bad}")
        else:
            ok("editorial_ok_when_allowed", True)

    # Provenance / evidence score
    ie = record.get("institutional_evidence") or {}
    pack = ie.get("institutional_evidence") or ie
    if gold.require_provenance and pack:
        validated = pack.get("validated") or ie.get("validated") or {}
        if validated:
            all_prov = all(
                bool(v.get("provider") or v.get("winning_provider"))
                and bool(v.get("as_of") or v.get("verified_at"))
                for v in validated.values()
                if isinstance(v, dict)
            )
            ok("provenance", all_prov, f"n={len(validated)}")
        else:
            # Fall back: observed fields from validation provenance list
            prov = (record.get("validation") or {}).get("provenance") or []
            ok("provenance", bool(prov), f"prov={prov}")

    if gold.min_evidence_score is not None:
        score = pack.get("evidence_score")
        if score is None:
            score = ie.get("evidence_score")
        ok(
            "evidence_score",
            score is not None and float(score) >= gold.min_evidence_score,
            f"score={score}",
        )

    passed = all(c["passed"] for c in checks) if checks else False
    executed = [f for f in (record.get("frameworks") or []) if f.get("status") == "executed"]
    selected = [f.get("framework_id") for f in (record.get("frameworks") or [])]

    # Every governed answer must carry a valid Decision Justification Graph.
    djg = record.get("justification_graph") or {}
    djg_integrity = (djg.get("integrity") or {}) if djg else {}
    ok("justification_graph", bool(djg) and djg_integrity.get("valid") is True, str(djg_integrity.get("problems"))[:120])
    passed = all(c["passed"] for c in checks) if checks else False
    executed = [f for f in (record.get("frameworks") or []) if f.get("status") == "executed"]
    selected = [f.get("framework_id") for f in (record.get("frameworks") or [])]

    # Wrong entity execution signal
    wrong_entity = False
    if gold.entity_id and executed:
        rejected = (record.get("validation") or {}).get("rejected") or {}
        if any(str(v).startswith("entity_mismatch") for v in rejected.values()) and not (
            record.get("institutional_evidence")
        ):
            # executed despite only mismatched evidence
            wrong_entity = True

    return {
        "case_id": case.case_id,
        "suite": case.suite,
        "question": case.question,
        "passed": passed,
        "failures": failures,
        "checks": checks,
        "elapsed_ms": elapsed_ms,
        "question_type": record.get("question_type"),
        "path": record.get("path"),
        "entity_id": ent.get("entity_id"),
        "frameworks_selected": selected,
        "frameworks_executed": [f.get("framework_id") for f in executed],
        "execution_rate": (
            len(executed) / max(1, len([f for f in (record.get("frameworks") or []) if f.get("status") != "not_applicable"]))
            if record.get("frameworks")
            else None
        ),
        "missing_evidence": record.get("missing_evidence") or [],
        "narrative_allowed": record.get("narrative_allowed"),
        "committee_stance": stance,
        "unsupported_conclusions": unsupported,
        "editorial_violations": editorial_violations,
        "wrong_entity_execution": wrong_entity,
        "evidence_score": pack.get("evidence_score") or ie.get("evidence_score"),
        "coverage": pack.get("coverage") or ie.get("coverage"),
        "evidence_provenance_ok": any(c["check"] == "provenance" and c["passed"] for c in checks)
        if gold.require_provenance
        else None,
        "justification_graph_valid": bool(djg) and djg_integrity.get("valid") is True,
        "justification_graph_nodes": (djg.get("counts") or {}).get("nodes"),
    }
