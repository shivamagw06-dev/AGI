"""Hallucination audit — unsupported claims, leakage, invented metrics."""

from __future__ import annotations

import re
from typing import Any

from academy.regression.schema import HallucinationFinding

_PROVIDER_LEAK = ("yahoo finance", "bloomberg terminal", "refinitiv", "provider_id", "api_key")
_ENGINE_LEAK = ("intelligence-engine", "cae engine", "irp engine", "fle engine", "package path")
_ARCH_LEAK = ("v1.0.1 locked internals", "soft-wire flag", "academy.books.v3.store")
_CITATION_FAKE = ("according to page", "see chapter", ".pdf p.", "doi:")


def audit_text(question_id: str, text: str, *, structure: dict[str, Any] | None = None) -> list[HallucinationFinding]:
    blob = f"{text}\n{structure or {}}".lower()
    findings: list[HallucinationFinding] = []
    n = 0

    def add(severity: str, category: str, detail: str) -> None:
        nonlocal n
        n += 1
        findings.append(
            HallucinationFinding(
                finding_id=f"hall_{question_id}_{n}",
                severity=severity,
                category=category,
                detail=detail,
                question_id=question_id,
            )
        )

    for p in _PROVIDER_LEAK:
        if p in blob:
            add("critical", "provider_leakage", f"Provider leakage: {p}")
    for e in _ENGINE_LEAK:
        if e in blob:
            add("critical", "engine_leakage", f"Engine leakage: {e}")
    for a in _ARCH_LEAK:
        if a in blob:
            add("high", "architecture_leakage", f"Architecture leakage: {a}")
    for c in _CITATION_FAKE:
        if c in blob:
            add("high", "invented_citations", f"Suspicious citation style: {c}")

    # Invented precise metrics without hedge
    if re.search(r"\bpe\s*=\s*\d+(\.\d+)?\b", blob) and "assumption" not in blob:
        add("medium", "invented_valuation", "Bare PE equality without assumption context")
    if re.search(r"\broic\s*=\s*\d{2,}(\.\d+)?%\b", blob) and "illustrative" not in blob and "about" not in blob:
        add("medium", "invented_metrics", "Precise ROIC percent without evidence qualifier")

    if "guaranteed return" in blob or "cannot lose" in blob:
        add("critical", "recommendation_policy", "Absolute return guarantee language")

    if "buy now" in blob and "committee" not in blob and "conditional" not in blob:
        add("high", "recommendation_policy", "Actionable buy without institutional chain")

    # Contradictions soft check
    if "high roic" in blob and "value destroying" in blob and "however" not in blob:
        add("low", "contradictions", "Potential unresolved contradiction on ROIC")

    return findings


def summarize(findings: list[HallucinationFinding]) -> dict[str, Any]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return {
        "total": len(findings),
        "by_severity": counts,
        "findings": [f.to_dict() for f in findings],
        "critical_count": counts["critical"],
        "high_count": counts["high"],
    }
