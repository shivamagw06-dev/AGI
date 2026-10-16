"""Append-only assertion versioning."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from institutional_knowledge_runtime.assertions import assertion_to_claim, claim_to_assertion
from institutional_knowledge_runtime.schema import APPROVED_WRITERS


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _writer_allowed(writer: str) -> bool:
    w = (writer or "").lower().replace(" ", "_")
    if w == "llm":
        return False
    return w in APPROVED_WRITERS


def version_assertion(
    assertion: dict[str, Any],
    *,
    reason: str,
    source: str,
    evidence_added: list[str] | None = None,
    evidence_removed: list[str] | None = None,
) -> dict[str, Any]:
    """Append version entry without overwriting history."""
    prev = int(assertion.get("version") or 1)
    entry = {
        "assertion_id": assertion.get("assertion_id"),
        "previous_version": prev,
        "current_version": prev + 1,
        "evidence_added": list(evidence_added or []),
        "evidence_removed": list(evidence_removed or []),
        "reason": reason,
        "timestamp": _now_iso(),
        "source": source,
        "status": assertion.get("status"),
    }
    history = list(assertion.get("history") or [])
    history.append(entry)

    updated = dict(assertion)
    updated["version"] = prev + 1
    updated["timestamp"] = entry["timestamp"]
    updated["history"] = history
    return updated


def update_assertion(
    iko: dict[str, Any],
    assertion_id: str,
    updates: dict[str, Any],
    *,
    writer: str,
    reason: str,
) -> dict[str, Any]:
    """Update assertion via approved writer only; append-only."""
    if not _writer_allowed(writer):
        raise PermissionError(f"Writer not approved: {writer}")

    claims = list(iko.get("claims") or [])
    idx = next((i for i, c in enumerate(claims) if c.get("claim_id") == assertion_id), None)
    if idx is None:
        raise KeyError(f"Assertion not found: {assertion_id}")

    assertion = claim_to_assertion(claims[idx])
    for key in ("status", "confidence", "evidence_refs", "monitoring", "statement", "dependencies", "contradictions"):
        if key in updates:
            assertion[key] = updates[key]

    evidence_added = updates.get("evidence_added")
    evidence_removed = updates.get("evidence_removed")
    assertion = version_assertion(
        assertion,
        reason=reason,
        source=writer,
        evidence_added=evidence_added if isinstance(evidence_added, list) else None,
        evidence_removed=evidence_removed if isinstance(evidence_removed, list) else None,
    )
    assertion["author"] = writer

    claims[idx] = assertion_to_claim(assertion)
    iko = dict(iko)
    iko["claims"] = claims
    iko["unknowns"] = [c["claim_id"] for c in claims if str(c.get("state")) == "UNKNOWN"]
    return iko
