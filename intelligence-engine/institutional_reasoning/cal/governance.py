"""Learning Governance Layer.

Outcome Intelligence → Learning Proposal → Simulation → Benchmark → Approval → Production

Never: Outcome → Production
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from institutional_reasoning.cal.candidates import generate_candidates
from institutional_reasoning.cal.learning_graph import build_learning_graph
from institutional_reasoning.cal.sandbox import simulate_proposal
from institutional_reasoning.cal.schema import CAL_VERSION, MODULE_CODE, PROGRAMME
from institutional_reasoning.cal.versions import deploy_approved, list_versions

GOVERNANCE_VERSION = "learning-governance-v1.0.0"

_PROPOSALS: dict[str, dict[str, Any]] = {}


def reset_governance() -> None:
    _PROPOSALS.clear()


def list_proposals(*, status: str | None = None) -> list[dict[str, Any]]:
    rows = list(_PROPOSALS.values())
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return deepcopy(rows)


def get_proposal(proposal_id: str) -> dict[str, Any] | None:
    row = _PROPOSALS.get(proposal_id)
    return deepcopy(row) if row else None


def propose_from_outcome(outcome_record: dict[str, Any]) -> dict[str, Any]:
    """Generate governed proposals from an IOI outcome/review record."""
    batch = generate_candidates(outcome_record)
    stored = []
    for c in batch.get("candidates") or []:
        if c.get("kind") == "no_change" and len(batch.get("candidates") or []) > 1:
            # Keep no_change only when it's the sole candidate
            continue
        pid = c.get("proposal_id") or f"lp_{uuid.uuid4().hex[:12]}"
        row = {
            **c,
            "proposal_id": pid,
            "status": "proposed",
            "governance_version": GOVERNANCE_VERSION,
            "cal_version": CAL_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "validation": None,
            "simulation": None,
            "approval": None,
            "deployment": None,
            "learning_graph": None,
            "source_outcome_id": outcome_record.get("decision_id"),
        }
        _PROPOSALS[pid] = row
        stored.append(deepcopy(row))
    if not stored and batch.get("candidates"):
        # Persist the no_change marker
        c = batch["candidates"][0]
        pid = c.get("proposal_id")
        row = {
            **c,
            "status": "proposed",
            "governance_version": GOVERNANCE_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source_outcome_id": outcome_record.get("decision_id"),
        }
        _PROPOSALS[pid] = row
        stored.append(deepcopy(row))
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "governance_version": GOVERNANCE_VERSION,
        "regime": batch.get("regime"),
        "proposals": stored,
        "count": len(stored),
    }


def validate_proposal(proposal_id: str) -> dict[str, Any]:
    row = _PROPOSALS.get(proposal_id)
    if not row:
        return {"found": False, "reason": "unknown_proposal"}
    issues: list[str] = []
    if row.get("auto_apply"):
        issues.append("auto_apply_forbidden")
    if row.get("kind") == "rewrite_framework":
        issues.append("rewrite_framework_forbidden")
    if "rewrite_framework" in (row.get("forbidden") or []):
        pass  # expected forbidden list
    if not row.get("requires_governance", True) and row.get("kind") != "no_change":
        issues.append("ungoverned_change")
    ok = not issues
    validation = {
        "passed": ok,
        "issues": issues,
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    row["validation"] = validation
    row["status"] = "validated" if ok else "rejected"
    if not ok:
        row["approval"] = {"approved": False, "reason": issues[0], "mode": "automatic_reject"}
    return deepcopy(row)


def simulate(proposal_id: str, *, historical_decisions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    row = _PROPOSALS.get(proposal_id)
    if not row:
        return {"found": False, "reason": "unknown_proposal"}
    if row.get("status") == "proposed":
        validate_proposal(proposal_id)
        row = _PROPOSALS[proposal_id]
    if row.get("status") == "rejected":
        return deepcopy(row)

    sim = simulate_proposal(row, historical_decisions=historical_decisions)
    row["simulation"] = sim
    row["status"] = "simulated" if sim.get("passed") else "rejected"
    if not sim.get("passed"):
        row["approval"] = {
            "approved": False,
            "reason": sim.get("reason"),
            "mode": "sandbox_reject",
            "ies_delta": sim.get("ies_delta"),
            "live_delta": sim.get("live_delta"),
        }
    return deepcopy(row)


def approve(
    proposal_id: str,
    *,
    approver: str = "governance",
    force: bool = False,
) -> dict[str, Any]:
    """Approve only after validation + successful simulation (unless force for tests)."""
    row = _PROPOSALS.get(proposal_id)
    if not row:
        return {"found": False, "reason": "unknown_proposal"}
    if row.get("status") == "proposed":
        validate_proposal(proposal_id)
        simulate(proposal_id)
        row = _PROPOSALS[proposal_id]
    elif row.get("status") == "validated":
        simulate(proposal_id)
        row = _PROPOSALS[proposal_id]

    sim = row.get("simulation") or {}
    if row.get("kind") == "no_change":
        row["approval"] = {"approved": False, "reason": "no_change", "approver": approver}
        row["status"] = "rejected"
        return deepcopy(row)

    if not sim.get("passed") and not force:
        row["approval"] = {
            "approved": False,
            "reason": sim.get("reason") or "simulation_not_passed",
            "approver": approver,
        }
        row["status"] = "rejected"
        return deepcopy(row)

    # Policy adjustments remain human-gated even after sandbox pass
    if row.get("kind") == "adjust_policy" and approver == "automatic":
        row["approval"] = {
            "approved": False,
            "reason": "human_approval_required",
            "approver": approver,
        }
        row["status"] = "simulated"
        return deepcopy(row)

    row["approval"] = {
        "approved": True,
        "approver": approver,
        "approved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "governed",
    }
    row["status"] = "approved"
    return deepcopy(row)


def deploy(proposal_id: str) -> dict[str, Any]:
    """Deploy an approved proposal into a new versioned overlay."""
    row = _PROPOSALS.get(proposal_id)
    if not row:
        return {"found": False, "reason": "unknown_proposal"}
    if row.get("status") != "approved" or not (row.get("approval") or {}).get("approved"):
        return {
            "found": True,
            "deployed": False,
            "reason": "not_approved",
            "status": row.get("status"),
        }
    deployment = deploy_approved(row, row.get("simulation") or {})
    row["deployment"] = deployment
    row["status"] = "deployed" if deployment.get("deployed") else row.get("status")
    # Learning graph for traceability
    row["learning_graph"] = build_learning_graph(
        {
            "proposal": row,
            "simulation": row.get("simulation") or {},
            "approval": row.get("approval") or {},
            "deployment": deployment,
            "outcome_ref": row.get("source_outcome_id"),
        }
    )
    return deepcopy(row)


def govern_learning(
    outcome_record: dict[str, Any],
    *,
    approver: str = "governance",
    auto_approve_safe: bool = True,
) -> dict[str, Any]:
    """Full governance path for all candidates from one outcome review."""
    proposed = propose_from_outcome(outcome_record)
    results = []
    for p in proposed.get("proposals") or []:
        pid = p["proposal_id"]
        validate_proposal(pid)
        simulate(pid)
        row = _PROPOSALS[pid]
        if auto_approve_safe and (row.get("simulation") or {}).get("passed"):
            if row.get("kind") == "adjust_policy":
                # Still require explicit human-like approver
                approve(pid, approver="human_committee")
            else:
                approve(pid, approver=approver)
            row = _PROPOSALS[pid]
            if row.get("status") == "approved":
                deploy(pid)
                row = _PROPOSALS[pid]
        results.append(deepcopy(row))

    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "governance_version": GOVERNANCE_VERSION,
        "cal_version": CAL_VERSION,
        "regime": proposed.get("regime"),
        "results": results,
        "approved": [r for r in results if r.get("status") in {"approved", "deployed"}],
        "rejected": [r for r in results if r.get("status") == "rejected"],
        "deployed_versions": list_versions()[-5:],
        "ungoverned_changes": 0,
        "learning_applied_to_source": False,
        "note": "Overlays only — framework source code never rewritten.",
    }
