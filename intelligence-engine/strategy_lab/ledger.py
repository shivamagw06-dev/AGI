"""Durable immutable ledgers for definitions, manifests and artifacts."""

from __future__ import annotations

import json
from typing import Any, Iterable

from institutional_warehouse import db, store
from strategy_lab.contracts import RunManifest, StrategyDefinition, canonical_json, content_hash, utc_now


SOURCE = "alpha_operating_system"


def _row(tab_id: str, where: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    db.init()
    rows = db.query(f"SELECT * FROM {db.physical_table(tab_id)} WHERE {where} LIMIT 1", params)
    return rows[0] if rows else None


def seal_definition(item: StrategyDefinition, *, actor: str = "system") -> dict[str, Any]:
    payload = item.to_dict()
    prior = _row("strategy_definitions", "strategy_id = ? AND version = ?", (item.strategy_id, item.version))
    if prior and prior.get("definition_hash") != item.definition_hash:
        raise ValueError(f"immutable_definition_conflict:{item.strategy_id}")
    result = store.upsert(
        "strategy_definitions",
        [{
            "strategy_id": item.strategy_id,
            "version": item.version,
            "definition_hash": item.definition_hash,
            "strategy_name": item.strategy_name,
            "owner": item.owner,
            "role": item.role,
            "declared_status": item.status,
            "definition_json": payload,
            "created_at": item.created_at,
            "approved_at": item.approved_at,
        }],
        source=SOURCE,
        actor=actor,
        reason="seal_immutable_strategy_definition",
    )
    return {**result, "definition_hash": item.definition_hash}


def seal_definitions(items: Iterable[StrategyDefinition], *, actor: str = "system") -> dict[str, Any]:
    results = [seal_definition(item, actor=actor) for item in items]
    return {"ok": True, "sealed": len(results), "definitions": results}


def start_run(manifest: RunManifest, *, actor: str = "system") -> dict[str, Any]:
    prior = _row("strategy_research_runs", "run_id = ?", (manifest.run_id,))
    manifest_json = manifest.to_dict()
    manifest_hash = content_hash(manifest_json)
    if prior and prior.get("manifest_hash") != manifest_hash:
        raise ValueError(f"immutable_run_conflict:{manifest.run_id}")
    result = store.upsert(
        "strategy_research_runs",
        [{
            "run_id": manifest.run_id,
            "strategy_id": manifest.strategy_id,
            "strategy_version": manifest.strategy_version,
            "definition_hash": manifest.definition_hash,
            "manifest_hash": manifest_hash,
            "manifest_json": manifest_json,
            "code_commit": manifest.code_commit,
            "dataset_hash": manifest.dataset_hash,
            "universe_hash": manifest.universe_hash,
            "feature_hash": manifest.feature_hash,
            "corporate_action_hash": manifest.corporate_action_hash,
            "cost_model_hash": manifest.cost_model_hash,
            "parameters_hash": manifest.parameters_hash,
            "start_date": manifest.start_date,
            "end_date": manifest.end_date,
            "information_cutoff": manifest.information_cutoff,
            "run_status": "STARTED",
            "started_at": manifest.created_at,
            "completed_at": None,
        }],
        source=SOURCE,
        actor=actor,
        reason="start_reproducible_research_run",
    )
    return {**result, "run_id": manifest.run_id, "manifest_hash": manifest_hash}


def append_artifact(
    run_id: str,
    kind: str,
    payload: Any,
    *,
    actor: str = "system",
    created_at: str | None = None,
) -> dict[str, Any]:
    payload_hash = content_hash(payload)
    artifact_id = f"artifact_{content_hash({'run_id': run_id, 'kind': kind, 'payload_hash': payload_hash})[:24]}"
    prior = _row("strategy_run_artifacts", "artifact_id = ?", (artifact_id,))
    if prior and prior.get("payload_hash") != payload_hash:
        raise ValueError(f"immutable_artifact_conflict:{artifact_id}")
    result = store.upsert(
        "strategy_run_artifacts",
        [{
            "artifact_id": artifact_id,
            "run_id": run_id,
            "artifact_kind": kind,
            "payload_hash": payload_hash,
            "payload_json": payload,
            "created_at": created_at or utc_now(),
        }],
        source=SOURCE,
        actor=actor,
        reason="append_immutable_research_artifact",
    )
    return {**result, "artifact_id": artifact_id, "payload_hash": payload_hash}


def complete_run(run_id: str, result: Any, *, actor: str = "system") -> dict[str, Any]:
    run = _row("strategy_research_runs", "run_id = ?", (run_id,))
    if not run:
        raise KeyError(f"unknown_run:{run_id}")
    artifact = append_artifact(run_id, "result", result, actor=actor)
    db.backend().execute(
        f"UPDATE {db.physical_table('strategy_research_runs')} SET run_status = ?, completed_at = ?, sys_updated_at = ? WHERE run_id = ?",
        ("COMPLETED", utc_now(), utc_now(), run_id),
    )
    return {"ok": True, "run_id": run_id, "status": "COMPLETED", "artifact": artifact}


def recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    db.init()
    bounded = max(1, min(int(limit), 100))
    return db.query(
        f"SELECT * FROM {db.physical_table('strategy_research_runs')} ORDER BY started_at DESC LIMIT ?",
        (bounded,),
    )
