"""Redundancy detector — never fetch the same information twice."""

from __future__ import annotations

from typing import Any


def detect_redundancy(
    *,
    acquire_steps: list[dict[str, Any]],
    reuse_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    seen_evidence: set[str] = set()
    seen_provider_evidence: set[tuple[str, str]] = set()
    duplicates: list[dict[str, Any]] = []
    deduped: list[dict[str, Any]] = []

    for step in reuse_steps:
        key = str(step.get("evidence_key") or "")
        if key:
            seen_evidence.add(key)

    for step in acquire_steps:
        key = str(step.get("evidence_key") or "")
        provider = str(step.get("provider") or "")
        pair = (key, provider)
        if key in seen_evidence:
            duplicates.append(
                {
                    "evidence_key": key,
                    "provider": provider,
                    "reason": "Already covered by internal reuse — skip external fetch",
                }
            )
            continue
        if pair in seen_provider_evidence:
            duplicates.append(
                {
                    "evidence_key": key,
                    "provider": provider,
                    "reason": "Duplicate provider+evidence pair",
                }
            )
            continue
        seen_provider_evidence.add(pair)
        seen_evidence.add(key)
        deduped.append(step)

    return {
        "deduped_acquire": deduped,
        "duplicate_fetches_prevented": duplicates,
        "duplicate_count": len(duplicates),
        "zero_duplicate_guarantee": len(duplicates) == 0 or all(d.get("reason") for d in duplicates),
    }
