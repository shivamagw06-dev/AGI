"""Five hypothesis quality rules — reject generic theses."""

from __future__ import annotations

import re
from typing import Any

from hypothesis_engine.schema import QUALITY_RULES

_GENERIC_PATTERNS = (
    r"\bis a good company\b",
    r"\bis a bad company\b",
    r"\bis strong\b",
    r"\bis weak\b",
    r"\blooks attractive\b",
    r"\bis overvalued\b$",
    r"\bis undervalued\b$",
    r"\bhas potential\b",
    r"\bwill do well\b",
    r"\bis interesting\b",
)

_CAUSAL_MARKERS = (
    "because",
    "due to",
    "driven by",
    "reflects",
    "allows",
    "despite",
    "as a result",
    "implies",
    "already prices",
    "priced in",
    "already priced",
    "may slow",
    "remain",
    "narrowing",
    "supports",
    "undermines",
    "depends on whether",
    "only if",
    "rather than",
    "offset by",
    "transmit",
    "justify",
    "creates a",
    "reduce",
    "compress",
)

_COMPARATIVE_MARKERS = (
    "versus",
    " vs ",
    "above",
    "below",
    "relative",
    "historical",
    "peer",
    "differential",
    "gap",
    "premium",
    "discount",
    "superior",
    "weaker",
    "stronger",
    "between the compared",
)

_FALSIFY_MARKERS = (
    "if",
    "unless",
    "would be false",
    "disproven when",
    "fails when",
    "contradicted by",
    "above",
    "below",
    "slower",
    "faster",
    "higher",
    "lower",
    "narrowing",
    "expanding",
    "already",
    "not",
    "only if",
    "rather than",
    "limited",
    "compress",
    "slow",
    "benign",
    "invalid",
    "offset",
    "before",
    "after",
    "exceed",
    "fall",
    "rise",
)


def evaluate_quality_rules(
    statement: str,
    *,
    required_evidence: list[str] | None = None,
    falsification_test: str | None = None,
) -> dict[str, Any]:
    text = (statement or "").strip()
    lower = text.lower()
    falsify_text = f"{lower} {(falsification_test or '').lower()}"
    evidence = list(required_evidence or [])

    specific = len(text) >= 60 and not any(re.search(p, lower) for p in _GENERIC_PATTERNS)
    # Specific also needs a mechanism or comparative anchor
    specific = specific and (
        any(m in lower for m in _CAUSAL_MARKERS) or any(x in lower for x in _COMPARATIVE_MARKERS)
    )

    testable = bool(evidence) or any(
        x in lower
        for x in (
            "margin",
            "roe",
            "roic",
            "pe",
            "multiple",
            "deposit",
            "growth",
            "credit cost",
            "valuation",
            "percentile",
            "nim",
            "cash",
            "capex",
            "share",
            "earnings",
            "revision",
            "correlation",
            "drawdown",
            "factor",
            "portfolio",
            "risk",
        )
    )

    falsifiable = any(m in falsify_text for m in _FALSIFY_MARKERS) or bool(
        re.search(
            r"\b(above|below|slower|faster|higher|lower|narrow|expand|already|not|only if|rather than)\b",
            falsify_text,
        )
    )

    evidence_required = len(evidence) >= 1
    decision_relevant = any(
        x in lower
        for x in (
            "valuation",
            "advantage",
            "priced",
            "growth",
            "risk",
            "cost",
            "competition",
            "portfolio",
            "margin",
            "quality",
            "demand",
            "premium",
            "expansion",
            "funding",
            "credit",
            "moat",
            "return",
            "thesis",
            "multiple",
            "earnings",
            "position sizing",
            "investment",
            "buy case",
            "value",
        )
    )

    checks = {
        "specific": specific,
        "testable": testable,
        "falsifiable": falsifiable,
        "evidence_required": evidence_required,
        "decision_relevant": decision_relevant,
    }
    passed = all(checks[r] for r in QUALITY_RULES)
    return {
        "rules": checks,
        "passed": passed,
        "failed_rules": [r for r in QUALITY_RULES if not checks[r]],
        "generic_rejected": any(re.search(p, lower) for p in _GENERIC_PATTERNS),
    }


def evaluate_hypothesis_quality(hypothesis: dict[str, Any]) -> dict[str, Any]:
    """Compatibility helper used by production quality-gate probes."""
    return evaluate_quality_rules(
        str(hypothesis.get("statement") or hypothesis.get("hypothesis") or ""),
        required_evidence=list(hypothesis.get("required_evidence") or []),
        falsification_test=str(hypothesis.get("falsification_test") or hypothesis.get("falsification") or ""),
    )


def enforce_quality(hypothesis: dict[str, Any]) -> dict[str, Any]:
    """Attach quality_rules evaluation; mark invalid generics."""
    eval_ = evaluate_quality_rules(
        str(hypothesis.get("statement") or ""),
        required_evidence=list(hypothesis.get("required_evidence") or []),
        falsification_test=str(hypothesis.get("falsification_test") or hypothesis.get("falsification") or ""),
    )
    out = dict(hypothesis)
    out["quality_rules"] = eval_
    out["quality_compliant"] = bool(eval_["passed"])
    if eval_.get("generic_rejected") or not eval_["passed"]:
        out["status"] = "rejected_generic" if eval_.get("generic_rejected") else out.get("status", "proposed")
    return out
