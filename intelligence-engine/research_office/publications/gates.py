"""Publication quality gates — institutionally ready or not."""

from __future__ import annotations

import json
from typing import Any

from research_office.schema import FORBIDDEN_CLAIMS


def _text_blob(obj: Any) -> str:
    try:
        return json.dumps(obj, default=str).lower()
    except Exception:
        return str(obj).lower()


def validate_publication(
    *,
    body: dict[str, Any],
    sources: list[dict[str, Any]],
    knowledge_version: str | None,
    evidence_version: str | None,
    coverage: dict[str, Any] | None,
    evidence_present: bool,
) -> dict[str, Any]:
    failures: list[str] = []

    if not evidence_present:
        failures.append("evidence_missing")

    if not sources:
        failures.append("unknown_source")
    else:
        for s in sources:
            if not (s.get("source") or s.get("collector") or s.get("name")):
                failures.append("unknown_source")
                break
            if s.get("provenance") is False:
                failures.append("publication_without_provenance")
                break
        # require at least one provenance-bearing source
        if not any((s.get("provenance") is not False) and (s.get("source") or s.get("name")) for s in sources):
            failures.append("publication_without_provenance")

    if not knowledge_version:
        failures.append("knowledge_version_mismatch")
    if not evidence_version:
        failures.append("knowledge_version_mismatch")

    # coverage mismatch: if declared keys exist they must not be fabricated
    if coverage and coverage.get("fabricated"):
        failures.append("coverage_mismatch")

    blob = _text_blob(body)
    for claim in FORBIDDEN_CLAIMS:
        # word-ish contains; avoid false positive on "buyback" for buy — check buy as token
        if claim == "buy":
            if " buy " in f" {blob} " or '"buy"' in blob:
                failures.append("forbidden_recommendation")
                break
        elif claim in blob:
            failures.append("forbidden_recommendation")
            break

    # reproducibility: body must carry snapshot refs
    if not (body.get("snapshot") or body.get("as_of") or body.get("sections")):
        failures.append("publication_not_reproducible")

    # historical replay failure if body explicitly marks it
    if body.get("historical_replay_failed"):
        failures.append("historical_replay_failure")

    failures = sorted(set(failures))
    ok = not failures
    return {
        "ok": ok,
        "institutionally_ready": ok,
        "failures": failures,
        "provenance_ok": "publication_without_provenance" not in failures
        and "unknown_source" not in failures,
        "knowledge_only": True,
        "fabricated": False,
    }
