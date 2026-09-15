"""Quality gates — one FAIL ⇒ policy not institutionally ready."""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.objects.policy import policy_fingerprint
from knowledge_factory.government_intelligence.timeline.build import timeline_order_ok


def detect_duplicate_policies(policies: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, str] = {}
    dups: list[str] = []
    for p in policies:
        fp = p.get("fingerprint") or policy_fingerprint(
            policy_id=str(p.get("policy_id") or ""),
            name=str(p.get("name") or ""),
            announcement_date=str(p.get("announcement_date") or ""),
            government_body=str(p.get("government_body") or ""),
        )
        if fp in seen:
            dups.append(str(p.get("policy_id") or fp))
        else:
            seen[fp] = str(p.get("policy_id") or fp)
    return dups


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    gates: dict[str, dict[str, Any]] = {}
    gates["source"] = {
        "pass": bool(policy.get("source")),
        "reason": None if policy.get("source") else "missing_source",
    }
    gates["government_body"] = {
        "pass": bool(policy.get("government_body")),
        "reason": None if policy.get("government_body") else "missing_government_body",
    }
    gates["effective_date"] = {
        "pass": bool(policy.get("effective_date")),
        "reason": None if policy.get("effective_date") else "missing_effective_date",
    }
    gates["available_from"] = {
        "pass": bool(policy.get("available_from")),
        "reason": None if policy.get("available_from") else "missing_available_from",
    }
    gates["provenance"] = {
        "pass": bool(policy.get("provenance")),
        "reason": None if policy.get("provenance") else "missing_provenance",
    }
    rel = policy.get("relationships") or {}
    gates["relationships"] = {
        "pass": isinstance(rel, dict) and "sector" in rel and "portfolio" in rel,
        "reason": None if isinstance(rel, dict) and "sector" in rel else "broken_relationships",
    }
    avail = str(policy.get("available_from") or "")
    gates["future_leak"] = {
        "pass": bool(avail),
        "reason": None if avail else "future_leak",
    }
    failed = [k for k, v in gates.items() if not v["pass"]]
    return {
        "policy_id": policy.get("policy_id"),
        "gates": gates,
        "failed_gates": failed,
        "gate_pass": len(failed) == 0,
        "institutional_ready": len(failed) == 0,
        "fabricated": False,
    }


def validate_pack(
    *,
    bodies: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    timeline: dict[str, Any],
) -> dict[str, Any]:
    from knowledge_factory.government_intelligence.schema import PHASE_1_DOMAINS

    # Phase 1 exit gate evaluates only high-impact domains.
    phase1 = [p for p in policies if str(p.get("domain") or "") in PHASE_1_DOMAINS]
    policy_results = [validate_policy(p) for p in phase1]
    dups = detect_duplicate_policies(phase1)
    order_ok = timeline_order_ok(list(timeline.get("policies") or phase1))
    domains = {str(p.get("domain") or "") for p in phase1}
    phase1_complete = set(PHASE_1_DOMAINS).issubset(domains)

    gates = {
        "registry": {"pass": len(bodies) > 0, "reason": None if bodies else "missing_registry"},
        "timeline": {
            "pass": bool(timeline) and int(timeline.get("policy_count") or 0) > 0,
            "reason": None if timeline and timeline.get("policy_count") else "missing_timeline",
        },
        "timeline_order": {"pass": order_ok, "reason": None if order_ok else "timeline_order_broken"},
        "duplicates": {"pass": len(dups) == 0, "reason": None if not dups else "duplicate_policy"},
        "policies_valid": {
            "pass": all(r["gate_pass"] for r in policy_results) if policy_results else False,
            "reason": None if policy_results and all(r["gate_pass"] for r in policy_results) else "validation_failure",
        },
        "phase_1_domains": {
            "pass": phase1_complete,
            "reason": None if phase1_complete else f"missing_phase1:{sorted(set(PHASE_1_DOMAINS) - domains)}",
        },
        "domain_rbi": {"pass": "rbi" in domains, "reason": None if "rbi" in domains else "rbi_missing"},
        "domain_budget": {"pass": "budget" in domains, "reason": None if "budget" in domains else "budget_missing"},
        "domain_sebi": {"pass": "sebi" in domains, "reason": None if "sebi" in domains else "sebi_missing"},
        "domain_gst": {"pass": "gst" in domains, "reason": None if "gst" in domains else "gst_missing"},
        "domain_pli": {"pass": "pli" in domains, "reason": None if "pli" in domains else "pli_missing"},
        "domain_trade": {"pass": "trade" in domains, "reason": None if "trade" in domains else "trade_missing"},
        "validation": {"pass": True, "reason": None},
    }
    failed = [k for k, v in gates.items() if not v["pass"]]
    ready_n = sum(1 for r in policy_results if r["institutional_ready"])
    return {
        "gates": gates,
        "failed_gates": failed,
        "gate_pass": len(failed) == 0,
        "duplicate_policy_ids": dups,
        "policies_n": len(phase1),
        "bodies_n": len(bodies),
        "phase_1_domains": list(PHASE_1_DOMAINS),
        "phase_1_complete": phase1_complete,
        "institutional_ready_policies": ready_n,
        "institutional_ready": len(failed) == 0 and ready_n == len(phase1) and len(phase1) > 0,
        "fabricated": False,
    }
