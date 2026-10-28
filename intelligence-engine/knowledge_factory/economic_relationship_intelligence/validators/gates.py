"""IERI quality gates — one FAIL ⇒ not institutionally ready."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence.schema import (
    DIRECTIONS,
    ECONOMIC_SEMANTICS,
    RELATIONSHIP_TYPES,
    UNKNOWN,
)


def validate_relationship(obj: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    gates: dict[str, str] = {}

    prov = obj.get("provenance") or {}
    if not prov or not prov.get("source") or prov.get("source") == UNKNOWN:
        failures.append("missing_provenance")
        gates["provenance"] = "FAIL"
    else:
        gates["provenance"] = "PASS"

    if not obj.get("source") or obj.get("source") == UNKNOWN:
        failures.append("missing_source")
        gates["source"] = "FAIL"
    else:
        gates["source"] = "PASS"

    direc = str(obj.get("direction") or "")
    if not direc or direc == "unknown" or direc not in DIRECTIONS:
        failures.append("unknown_direction")
        gates["direction"] = "FAIL"
    else:
        gates["direction"] = "PASS"

    rtype = str(obj.get("relationship_type") or "")
    if rtype not in RELATIONSHIP_TYPES:
        failures.append("invalid_relationship")
        gates["relationship_type"] = "FAIL"
    else:
        gates["relationship_type"] = "PASS"

    sem = str(obj.get("semantics") or "")
    if sem not in ECONOMIC_SEMANTICS:
        failures.append("invalid_semantics")
        gates["semantics"] = "FAIL"
    else:
        gates["semantics"] = "PASS"

    if not obj.get("source_entity") or not obj.get("target_entity"):
        failures.append("broken_path")
        gates["path_integrity"] = "FAIL"
    else:
        gates["path_integrity"] = "PASS"

    if not obj.get("available_from"):
        failures.append("historical_replay_failure")
        gates["historical_replay"] = "FAIL"
    else:
        gates["historical_replay"] = "PASS"

    if obj.get("fabricated") is True:
        failures.append("validation_failure")
        gates["validation"] = "FAIL"
    else:
        gates["validation"] = "PASS"

    passed = len(failures) == 0
    return {
        "relationship_id": obj.get("relationship_id"),
        "gate_pass": passed,
        "institutional_ready": passed,
        "failures": failures,
        "gates": gates,
    }


def validate_corpus(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    dupes: list[str] = []
    results = []
    fail_count = 0
    for r in rows:
        rid = r.get("relationship_id")
        if rid in seen:
            dupes.append(str(rid))
            fail_count += 1
            results.append(
                {
                    "relationship_id": rid,
                    "gate_pass": False,
                    "failures": ["duplicate_relationship"],
                }
            )
            continue
        if rid:
            seen.add(str(rid))
        vr = validate_relationship(r)
        results.append(vr)
        if not vr["gate_pass"]:
            fail_count += 1
    return {
        "n": len(rows),
        "fail_count": fail_count + len(dupes),
        "duplicate_count": len(dupes),
        "pass_count": len(rows) - fail_count,
        "institutional_ready": fail_count == 0 and len(dupes) == 0 and len(rows) > 0,
        "results": results,
    }
