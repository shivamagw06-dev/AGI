"""IMEI quality gates — one FAIL ⇒ not institutionally ready."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence.schema import UNKNOWN


def validate_expectation(obj: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    gates: dict[str, str] = {}

    if not obj.get("source") or obj.get("source") == UNKNOWN:
        failures.append("missing_source")
        gates["source"] = "FAIL"
    else:
        gates["source"] = "PASS"

    prov = obj.get("provenance") or {}
    if not prov or not prov.get("source") or prov.get("fabricated") is True:
        failures.append("missing_provenance")
        gates["provenance"] = "FAIL"
    else:
        gates["provenance"] = "PASS"

    if not obj.get("available_from"):
        failures.append("missing_available_from")
        gates["available_from"] = "FAIL"
    else:
        gates["available_from"] = "PASS"

    ann = str(obj.get("announcement_date") or "")
    af = str(obj.get("available_from") or "")
    if ann and af and af < ann:
        failures.append("future_leakage")
        gates["future_leakage"] = "FAIL"
    else:
        gates["future_leakage"] = "PASS"

    # Phase-2 UNKNOWN placeholders are valid as UNKNOWN records but not institutionally ready
    if obj.get("forecast_value") == UNKNOWN:
        failures.append("unknown_expectation")
        gates["validation"] = "FAIL"
    elif obj.get("fabricated") is True:
        failures.append("validation_failure")
        gates["validation"] = "FAIL"
    else:
        gates["validation"] = "PASS"

    # Revision consistency: if revision_of set, sequence must be > 0
    if obj.get("revision_of") and int(obj.get("revision_sequence") or 0) <= 0:
        failures.append("revision_inconsistency")
        gates["revision_consistency"] = "FAIL"
    else:
        gates["revision_consistency"] = "PASS"

    passed = len(failures) == 0
    return {
        "expectation_id": obj.get("expectation_id"),
        "gate_pass": passed,
        "institutional_ready": passed,
        "failures": failures,
        "gates": gates,
    }


def validate_corpus(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    dupes = 0
    fail = 0
    for r in rows:
        eid = r.get("expectation_id")
        if eid in seen:
            dupes += 1
            fail += 1
            continue
        if eid:
            seen.add(str(eid))
        vr = validate_expectation(r)
        if not vr["gate_pass"]:
            fail += 1
    return {
        "n": len(rows),
        "fail_count": fail,
        "duplicate_count": dupes,
        "institutional_ready": fail == 0 and len(rows) > 0,
    }
