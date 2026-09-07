"""Governance Spec v1.0 rule catalogue + evaluators over Evaluation Lab JSON.

These rules are constitutional policy. The Evaluation Lab runner produces JSON;
Phase 6 executes every result against these rule IDs.
"""

from __future__ import annotations

from typing import Any, Callable

from governance_spec.schema import GOVERNANCE_SPEC_VERSION, FROZEN, rule

EvalFn = Callable[[dict[str, Any]], dict[str, Any]]


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _decision_l(row: dict[str, Any]) -> str:
    return str(row.get("decision") or row.get("action") or "").strip().lower()


def _is_high_conviction(row: dict[str, Any]) -> bool:
    d = _decision_l(row)
    band = str(row.get("readiness_band") or "").lower()
    return (
        d in {"high conviction", "high_conviction"}
        or "high conviction" in d
        or band == "high_conviction_allowed"
    )


def _thesis(row: dict[str, Any]) -> str:
    return str(row.get("investment_thesis_status") or "").upper()


def _failure_reason(row: dict[str, Any]) -> str:
    fail = row.get("failure") if isinstance(row.get("failure"), dict) else {}
    return str(fail.get("reason") or "").upper()


def _missing_signals(row: dict[str, Any]) -> str:
    bits = [
        _failure_reason(row),
        str(row.get("evidence_class") or ""),
        " ".join(str(x) for x in (row.get("errors") or [])),
    ]
    qa = row.get("qa") if isinstance(row.get("qa"), dict) else {}
    for v in qa.get("violations") or []:
        if isinstance(v, dict):
            bits.append(str(v.get("rule") or ""))
            bits.append(str(v.get("detail") or ""))
    return " ".join(bits).lower()


def _result(rule_id: str, *, passed: bool, detail: str, skipped: bool = False) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "passed": bool(passed) if not skipped else None,
        "skipped": skipped,
        "status": "SKIP" if skipped else ("PASS" if passed else "FAIL"),
        "detail": detail,
        "spec_version": GOVERNANCE_SPEC_VERSION,
    }


def eval_gov_001(row: dict[str, Any]) -> dict[str, Any]:
    """Readiness < 80% ⇒ High Conviction prohibited."""
    readiness = _f(row.get("recommendation_readiness"))
    if readiness is None:
        return _result("GOV-001", passed=True, skipped=True, detail="No readiness score — not applicable")
    if readiness >= 80:
        return _result("GOV-001", passed=True, skipped=True, detail=f"Readiness {readiness}% ≥ 80% — rule idle")
    if _is_high_conviction(row):
        return _result(
            "GOV-001",
            passed=False,
            detail=f"Readiness {readiness}% < 80% but decision/band is High Conviction",
        )
    return _result("GOV-001", passed=True, detail=f"Readiness {readiness}% < 80% and High Conviction prohibited")


def eval_gov_002(row: dict[str, Any]) -> dict[str, Any]:
    """Missing live price ⇒ Valuation marked stale / current unavailable."""
    price_ok = bool(row.get("price_available") or row.get("live_price"))
    if price_ok and not row.get("price_stale"):
        return _result("GOV-002", passed=True, skipped=True, detail="Live price available — rule idle")
    # Price missing or stale — valuation must not be treated as current
    val = row.get("valuation")
    decision = _decision_l(row)
    thesis = _thesis(row)
    stale_ok = (
        val is None
        or bool(row.get("price_stale"))
        or _failure_reason(row) in {"LIVE_PRICE_UNAVAILABLE", "PRICE_AND_PACK_MISSING", "VALUATION_MISSING"}
        or thesis == "INCONCLUSIVE"
        or decision in {"deferred", "inconclusive", "watchlist"}
        or str(row.get("gate") or "").upper() == "FAIL"
    )
    if not stale_ok and _is_high_conviction(row):
        return _result(
            "GOV-002",
            passed=False,
            detail="Live price missing/stale but valuation-linked High Conviction issued",
        )
    if not stale_ok and decision in {"constructive"} and val is not None and float(val) > 0:
        return _result(
            "GOV-002",
            passed=False,
            detail="Live price missing/stale but Constructive decision still carries a current valuation score",
        )
    return _result(
        "GOV-002",
        passed=True,
        detail="Missing/stale live price — valuation treated as not current / recommendation restrained",
    )


def eval_gov_003(row: dict[str, Any]) -> dict[str, Any]:
    """Missing mandatory financials ⇒ Thesis = INCONCLUSIVE."""
    blob = _missing_signals(row)
    financial_missing = (
        "financials_or_filing_missing" in blob
        or "financial" in blob
        and ("missing" in blob or "fail" in blob)
        or _failure_reason(row) == "FINANCIALS_OR_FILING_MISSING"
        or (
            str(row.get("evidence_class") or "") == "Insufficient"
            and (_f(row.get("financial_quality")) or 0) <= 3.5
            and str(row.get("gate") or "").upper() == "FAIL"
        )
    )
    if not financial_missing:
        # Heuristic: thin financial quality with gate fail
        fq = _f(row.get("financial_quality"))
        if str(row.get("gate") or "").upper() == "FAIL" and fq is not None and fq <= 3.0:
            financial_missing = True
        else:
            return _result("GOV-003", passed=True, skipped=True, detail="Mandatory financials not flagged missing")
    if _thesis(row) == "INCONCLUSIVE" or _decision_l(row) in {"deferred", "inconclusive"}:
        return _result("GOV-003", passed=True, detail="Missing financials → thesis INCONCLUSIVE / deferred")
    return _result(
        "GOV-003",
        passed=False,
        detail=f"Mandatory financials missing but thesis={_thesis(row)!r} decision={row.get('decision')!r}",
    )


def eval_gov_004(row: dict[str, Any]) -> dict[str, Any]:
    """Missing current ownership ⇒ Readiness reduced."""
    blob = _missing_signals(row)
    ownership_missing = (
        _failure_reason(row) == "SHAREHOLDING_MISSING"
        or "shareholding" in blob
        or "ownership" in blob
    )
    if not ownership_missing:
        return _result("GOV-004", passed=True, skipped=True, detail="Ownership not flagged missing")
    readiness = _f(row.get("recommendation_readiness"))
    inst = _f(row.get("institutional_readiness"))
    reduced = False
    if readiness is not None and readiness < 80:
        reduced = True
    if readiness is not None and inst is not None and readiness <= inst:
        # recommendation readiness at/below institutional coverage implies penalty applied or equal thinness
        reduced = True
    if str(row.get("gate") or "").upper() == "FAIL":
        reduced = True
    if reduced:
        return _result("GOV-004", passed=True, detail="Ownership missing and readiness reduced / gate failed")
    return _result(
        "GOV-004",
        passed=False,
        detail=f"Ownership missing but readiness still elevated ({readiness})",
    )


def eval_gov_005(row: dict[str, Any]) -> dict[str, Any]:
    """Material filing pending ingestion ⇒ Recommendation withheld."""
    blob = _missing_signals(row)
    filing_pending = (
        _failure_reason(row) == "FINANCIALS_OR_FILING_MISSING"
        or "filing" in blob
        or (
            str(row.get("evidence_class") or "") == "Insufficient"
            and str(row.get("gate") or "").upper() == "FAIL"
        )
    )
    if not filing_pending:
        return _result("GOV-005", passed=True, skipped=True, detail="No material filing-pending signal")
    withheld = (
        _thesis(row) == "INCONCLUSIVE"
        or _decision_l(row) in {"deferred", "inconclusive", "watchlist"}
        or str(row.get("gate") or "").upper() == "FAIL"
        or not _is_high_conviction(row)
    )
    if withheld and not _is_high_conviction(row):
        return _result("GOV-005", passed=True, detail="Filing pending — recommendation withheld")
    return _result(
        "GOV-005",
        passed=False,
        detail="Material filing pending but High Conviction / formed recommendation issued",
    )


def eval_gov_006(row: dict[str, Any]) -> dict[str, Any]:
    """Company Quality must not be reduced because evidence is missing."""
    evidence_thin = (
        str(row.get("gate") or "").upper() == "FAIL"
        or str(row.get("evidence_class") or "") in {"Insufficient", "Partial"}
        or _thesis(row) == "INCONCLUSIVE"
        or (_f(row.get("recommendation_readiness")) or 100) < 80
    )
    if not evidence_thin:
        return _result("GOV-006", passed=True, skipped=True, detail="Evidence not thin — rule idle")
    # Pass if system documents separation OR company quality remains non-punitive
    if row.get("not_a_negative_view") is True:
        return _result("GOV-006", passed=True, detail="not_a_negative_view set — evidence ≠ company quality")
    cq = _f(row.get("company_quality"))
    overall = _f(row.get("overall_score"))
    if cq is not None and cq >= 7.0 and overall is not None and overall <= 3.5:
        # Quality high, overall crushed without deferral documentation → fail unless deferred
        if _decision_l(row) not in {"deferred", "inconclusive", "watchlist"} and _thesis(row) != "INCONCLUSIVE":
            return _result(
                "GOV-006",
                passed=False,
                detail=f"Company quality {cq} intact but overall {overall} crushed without INCONCLUSIVE deferral",
            )
    if cq is not None and cq < 4.0 and evidence_thin and row.get("not_a_negative_view") is not True:
        # Suspicious: company quality itself collapsed with thin evidence and no separation flag
        return _result(
            "GOV-006",
            passed=False,
            detail=f"Company quality {cq} appears penalised under thin evidence without not_a_negative_view",
        )
    return _result(
        "GOV-006",
        passed=True,
        detail="No evidence that company quality was reduced solely due to missing data",
    )


def eval_gov_007(row: dict[str, Any]) -> dict[str, Any]:
    """Editorial layer cannot override an INCONCLUSIVE gate."""
    gate_fail = str(row.get("gate") or "").upper() == "FAIL"
    inconclusive = _thesis(row) == "INCONCLUSIVE"
    if not (gate_fail or inconclusive):
        return _result("GOV-007", passed=True, skipped=True, detail="Gate not INCONCLUSIVE — rule idle")
    # Editorial override would look like High Conviction / Constructive despite inconclusive gate
    if _is_high_conviction(row) or (
        _decision_l(row) in {"constructive"} and inconclusive
    ):
        return _result(
            "GOV-007",
            passed=False,
            detail=f"INCONCLUSIVE/FAILED gate overridden by decision={row.get('decision')!r}",
        )
    return _result(
        "GOV-007",
        passed=True,
        detail="INCONCLUSIVE gate respected — no editorial override to conviction",
    )


def eval_gov_008(row: dict[str, Any]) -> dict[str, Any]:
    """Recommendation must include evidence lineage (or provenance proxy)."""
    # Full lineage board may arrive via governance package; accept Evaluation Lab provenance fields
    lineage = row.get("evidence_lineage") or row.get("lineage")
    versions = row.get("versions") if isinstance(row.get("versions"), dict) else {}
    has_lineage = bool(lineage)
    has_provenance = bool(
        row.get("knowledge_snapshot")
        or row.get("market_snapshot")
        or row.get("price_source")
        or versions.get("decision_engine_version")
        or row.get("replay_inputs")
        or row.get("pack_present") is not None
    )
    # Only require when a conviction recommendation is issued
    if not _is_high_conviction(row) and _decision_l(row) not in {"constructive"}:
        if has_provenance or has_lineage:
            return _result("GOV-008", passed=True, detail="Provenance present on deferred/watch result")
        return _result(
            "GOV-008",
            passed=True,
            skipped=True,
            detail="No conviction recommendation — lineage check soft-skipped",
        )
    if has_lineage or has_provenance:
        return _result("GOV-008", passed=True, detail="Evidence lineage / provenance fields present")
    return _result(
        "GOV-008",
        passed=False,
        detail="Conviction recommendation without evidence lineage or provenance metadata",
    )


RULE_EVALUATORS: dict[str, EvalFn] = {
    "GOV-001": eval_gov_001,
    "GOV-002": eval_gov_002,
    "GOV-003": eval_gov_003,
    "GOV-004": eval_gov_004,
    "GOV-005": eval_gov_005,
    "GOV-006": eval_gov_006,
    "GOV-007": eval_gov_007,
    "GOV-008": eval_gov_008,
}

RULES: list[dict[str, Any]] = [
    {
        **rule(
            "GOV-001",
            assertion="Recommendation Readiness < 80% ⇒ High Conviction prohibited",
            severity="Critical",
            description="Never issue High Conviction when institutional recommendation readiness is below 80%.",
            applies_when="recommendation_readiness < 80",
        ),
        "evaluate": "eval_gov_001",
    },
    {
        **rule(
            "GOV-002",
            assertion="Missing live price ⇒ Valuation marked stale/current unavailable",
            severity="Critical",
            description="Without a current live price, valuation must not be treated as current.",
            applies_when="live_price missing or stale",
        ),
        "evaluate": "eval_gov_002",
    },
    {
        **rule(
            "GOV-003",
            assertion="Missing mandatory financials ⇒ Thesis = INCONCLUSIVE",
            severity="Critical",
            description="Mandatory financial evidence gaps force an INCONCLUSIVE thesis.",
            applies_when="mandatory financials missing",
        ),
        "evaluate": "eval_gov_003",
    },
    {
        **rule(
            "GOV-004",
            assertion="Missing current ownership ⇒ Readiness reduced",
            severity="High",
            description="Stale/missing shareholding must reduce recommendation readiness.",
            applies_when="ownership/shareholding missing",
        ),
        "evaluate": "eval_gov_004",
    },
    {
        **rule(
            "GOV-005",
            assertion="Material filing pending ingestion ⇒ Recommendation withheld",
            severity="Critical",
            description="Pending material filings block conviction recommendations.",
            applies_when="material filing pending",
        ),
        "evaluate": "eval_gov_005",
    },
    {
        **rule(
            "GOV-006",
            assertion="Company Quality must not be reduced because evidence is missing",
            severity="Critical",
            description="Evidence incompleteness is never company quality. Separation must hold.",
            applies_when="evidence thin or gate failed",
        ),
        "evaluate": "eval_gov_006",
    },
    {
        **rule(
            "GOV-007",
            assertion="Editorial layer cannot override an INCONCLUSIVE gate",
            severity="Critical",
            description="INCONCLUSIVE/FAILED institutional gates cannot be editorially upgraded to conviction.",
            applies_when="gate FAILED or thesis INCONCLUSIVE",
        ),
        "evaluate": "eval_gov_007",
    },
    {
        **rule(
            "GOV-008",
            assertion="Recommendation must include evidence lineage",
            severity="High",
            description="Conviction recommendations require lineage/provenance metadata for auditability.",
            applies_when="conviction recommendation issued",
        ),
        "evaluate": "eval_gov_008",
    },
]

RULES_BY_ID: dict[str, dict[str, Any]] = {r["rule_id"]: r for r in RULES}

# Freeze pin — changing the v1.0 rule set requires Governance Spec v1.1
FROZEN_RULE_IDS: tuple[str, ...] = tuple(r["rule_id"] for r in RULES)
assert FROZEN_RULE_IDS == (
    "GOV-001",
    "GOV-002",
    "GOV-003",
    "GOV-004",
    "GOV-005",
    "GOV-006",
    "GOV-007",
    "GOV-008",
)


def evaluate_rule(rule_id: str, row: dict[str, Any]) -> dict[str, Any]:
    fn = RULE_EVALUATORS.get(rule_id)
    if not fn:
        return _result(rule_id, passed=False, detail=f"Unknown rule_id {rule_id}")
    out = fn(row)
    meta = RULES_BY_ID.get(rule_id) or {}
    out["assertion"] = meta.get("assertion")
    out["severity"] = meta.get("severity")
    return out


def spec_board() -> dict[str, Any]:
    return {
        "spec_version": GOVERNANCE_SPEC_VERSION,
        "frozen": FROZEN,
        "n_rules": len(RULES),
        "rule_ids": list(FROZEN_RULE_IDS),
        "rules": [
            {
                "rule_id": r["rule_id"],
                "assertion": r["assertion"],
                "severity": r["severity"],
                "applies_when": r["applies_when"],
                "description": r["description"],
            }
            for r in RULES
        ],
        "architecture": [
            "Constitution",
            "Governance Specification",
            "Test Runner",
            "Evaluation Results",
        ],
        "note": (
            "Governance Spec v1.0 is frozen. Add rules via Governance Spec v1.1+. "
            "Historical releases remain reproducible against the spec active at evaluation time."
        ),
    }
