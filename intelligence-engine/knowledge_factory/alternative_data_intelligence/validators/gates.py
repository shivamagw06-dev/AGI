"""IADI quality gates — one FAIL ⇒ not institutionally ready."""

from __future__ import annotations

from typing import Any

from knowledge_factory.alternative_data_intelligence.schema import UNKNOWN


def validate_observation(obj: dict[str, Any]) -> dict[str, Any]:
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

    af = str(obj.get("available_from") or "")
    dt = str(obj.get("date") or "")
    if af and dt and af < dt:
        failures.append("future_leakage")
        gates["future_leakage"] = "FAIL"
    else:
        gates["future_leakage"] = "PASS"

    if obj.get("fabricated") is True:
        failures.append("validation_failure")
        gates["validation"] = "FAIL"
    else:
        gates["validation"] = "PASS"

    obs = obj.get("observation") or {}
    if obs.get("value") is None:
        failures.append("validation_failure")
        gates["observation"] = "FAIL"
    else:
        gates["observation"] = "PASS"

    passed = len(failures) == 0
    return {
        "observation_id": obj.get("observation_id"),
        "gate_pass": passed,
        "institutional_ready": passed,
        "failures": failures,
        "gates": gates,
    }


def validate_dataset(obj: dict[str, Any], *, observations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    failures: list[str] = []
    gates: dict[str, str] = {}

    if not obj.get("provider") or not (obj.get("provenance") or {}).get("source"):
        failures.append("missing_provenance")
        gates["provenance"] = "FAIL"
    else:
        gates["provenance"] = "PASS"

    obs = observations or []
    if len(obs) < 3:
        failures.append("validation_failure")
        gates["historical_series"] = "FAIL"
    else:
        gates["historical_series"] = "PASS"

    # Replay integrity: all obs available_from >= date
    leak = [o for o in obs if str(o.get("available_from") or "") < str(o.get("date") or "")]
    if leak:
        failures.append("broken_replay")
        gates["replay"] = "FAIL"
    else:
        gates["replay"] = "PASS"

    trends = obj.get("trends") or {}
    if trends and trends.get("derived_from_observations_only") is False:
        failures.append("unsupported_derived_metric")
        gates["derived_metrics"] = "FAIL"
    elif trends.get("status") == "ok" or trends.get("status") == "insufficient_observations":
        gates["derived_metrics"] = "PASS"
    else:
        gates["derived_metrics"] = "PASS"

    if not obj.get("company_links"):
        # Phase-1 datasets must have company links
        failures.append("validation_failure")
        gates["company_links"] = "FAIL"
    else:
        gates["company_links"] = "PASS"

    if not obj.get("industry_links"):
        failures.append("validation_failure")
        gates["industry_links"] = "FAIL"
    else:
        gates["industry_links"] = "PASS"

    passed = len(failures) == 0
    return {
        "dataset_id": obj.get("dataset_id"),
        "gate_pass": passed,
        "institutional_ready": passed,
        "failures": failures,
        "gates": gates,
    }


def validate_corpus(observations: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    dupes = 0
    fail = 0
    for o in observations:
        oid = o.get("observation_id")
        if oid in seen:
            dupes += 1
            fail += 1
            continue
        if oid:
            seen.add(str(oid))
        vr = validate_observation(o)
        if not vr["gate_pass"]:
            fail += 1
    return {
        "n": len(observations),
        "fail_count": fail,
        "duplicate_count": dupes,
        "institutional_ready": fail == 0 and len(observations) > 0,
    }
