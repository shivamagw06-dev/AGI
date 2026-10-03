"""MPC-01 Mandate Engine — portfolio → mandate → policy profile → risk/committee workflow.

Mandates are local workflow bindings. PCE-01 remains system of record for policy evaluation.
"""

from __future__ import annotations

from typing import Any

from institutional_multi_portfolio.schema import MANDATE_PROFILES, MANDATE_TO_POLICY


def resolve_mandate(mandate_id: str) -> dict[str, Any]:
    key = str(mandate_id or "balanced").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "fo": "family_office",
        "family": "family_office",
        "pms": "institutional",
        "default": "balanced",
    }
    key = aliases.get(key, key)
    if key not in MANDATE_PROFILES:
        key = "balanced"
    policy = MANDATE_TO_POLICY.get(key, "family_office")
    # Soft-validate against PCE profiles when available
    try:
        from institutional_policy.mandates import get_mandate, list_profiles

        profiles = {p["profile_id"] for p in list_profiles()}
        if policy not in profiles:
            policy = "family_office"
        pce = get_mandate(policy)
        return {
            "mandate_id": key,
            "policy_profile": policy,
            "pce_profile_id": getattr(pce, "profile_id", policy),
            "pce_label": getattr(pce, "label", policy),
            "owns_policy_evaluation": False,
            "policy_system_of_record": "PCE-01",
            "workflow": ("mandate", "policy_profile", "risk_limits", "committee_workflow"),
        }
    except Exception:
        return {
            "mandate_id": key,
            "policy_profile": policy,
            "owns_policy_evaluation": False,
            "policy_system_of_record": "PCE-01",
            "workflow": ("mandate", "policy_profile", "risk_limits", "committee_workflow"),
        }


def list_mandates() -> list[dict[str, Any]]:
    return [resolve_mandate(m) for m in MANDATE_PROFILES]


def assign_mandate(portfolio_id: str, mandate_id: str) -> dict[str, Any]:
    from institutional_multi_portfolio import portfolio_registry as preg

    m = resolve_mandate(mandate_id)
    existing = preg.get_portfolio(portfolio_id)
    if not existing:
        rec = preg.register_portfolio(portfolio_id, name=portfolio_id, mandate_id=m["mandate_id"])
    else:
        rec = preg.register_portfolio(
            portfolio_id,
            name=existing.name,
            mandate_id=m["mandate_id"],
            members=existing.members,
            client_ids=existing.client_ids,
        )
    return {
        "ok": True,
        "portfolio_id": portfolio_id,
        "mandate": m,
        "portfolio": rec.to_dict(),
        "intelligence_unchanged": True,
    }
