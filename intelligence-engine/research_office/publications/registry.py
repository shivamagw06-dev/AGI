"""Publication Registry — versioned, reproducible research outputs."""

from __future__ import annotations

import uuid
from typing import Any

from research_office import store
from research_office.schema import RO_VERSION


def register_publication(
    *,
    title: str,
    publication_type: str,
    body: dict[str, Any],
    knowledge_version: str,
    evidence_version: str,
    evidence_pack_versions: dict[str, Any] | None = None,
    covered_entities: list[str] | None = None,
    coverage: dict[str, Any] | None = None,
    sources: list[dict[str, Any]] | None = None,
    validation: dict[str, Any] | None = None,
    scheduler_run_id: str | None = None,
    framework_used: list[str] | None = None,
    framework_confidence: dict[str, Any] | None = None,
    framework_version: str | None = None,
    framework_explanation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pub_id = f"pub_{uuid.uuid4().hex[:14]}"
    created = store.utc_now()
    replay_id = f"ro_replay_{uuid.uuid4().hex[:12]}"
    obj = {
        "id": pub_id,
        "title": title,
        "publication_type": publication_type,
        "created": created,
        "knowledge_version": knowledge_version,
        "evidence_version": evidence_version,
        "evidence_pack_versions": evidence_pack_versions or {},
        "covered_entities": list(covered_entities or []),
        "coverage": coverage or {},
        "sources": sources or [],
        "generated_by": "research_office",
        "generator_version": RO_VERSION,
        "validation": validation or {"ok": False, "reason": "ungated"},
        "status": "draft",
        # AGIB v3.4 Track C — IFSE metadata on every publication
        "framework_used": list(framework_used or []),
        "framework_confidence": framework_confidence or {},
        "framework_version": framework_version,
        "framework_explanation": framework_explanation,
        "historical_replay": {
            "replay_id": replay_id,
            "point_in_time": True,
            "as_of": created,
            "scheduler_run_id": scheduler_run_id,
            "reproducible": True,
        },
        "body": body,
        "recommendation": None,
        "knowledge_only": True,
        "fabricated": False,
    }
    # Institutionally ready only when validation passed
    if (validation or {}).get("ok") and (validation or {}).get("institutionally_ready"):
        obj["status"] = "institutionally_ready"
    elif (validation or {}).get("ok"):
        obj["status"] = "validated"
    else:
        obj["status"] = "not_institutionally_ready"

    store.put_publication(pub_id, obj)
    return obj


def get_replay(replay_id: str) -> dict[str, Any] | None:
    for pub in store.list_publications(limit=500):
        hr = pub.get("historical_replay") or {}
        if hr.get("replay_id") == replay_id:
            return {
                "found": True,
                "replay_id": replay_id,
                "publication_id": pub.get("id"),
                "as_of": hr.get("as_of"),
                "knowledge_version": pub.get("knowledge_version"),
                "evidence_version": pub.get("evidence_version"),
                "evidence_pack_versions": pub.get("evidence_pack_versions"),
                "covered_entities": pub.get("covered_entities"),
                "validation": pub.get("validation"),
                "body": pub.get("body"),
                "point_in_time": True,
                "fabricated": False,
            }
    return None
