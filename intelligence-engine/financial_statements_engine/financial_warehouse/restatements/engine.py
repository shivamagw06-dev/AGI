"""Restatement registry — originals preserved; replacements linked."""

from __future__ import annotations

import json
import uuid
from typing import Any

from financial_statements_engine.financial_warehouse.publisher.publish import publish_validated_pack
from financial_statements_engine.financial_warehouse.storage.roots import warehouse_root
from financial_statements_engine.util import now_iso, write_json_atomic


def record_restatement(
    *,
    validated_pack: dict[str, Any],
    draft: dict[str, Any] | None = None,
    restatement_reason: str,
    original_validation_id: str | None = None,
) -> dict[str, Any]:
    restatement_id = f"rst:{uuid.uuid4().hex[:16]}"
    meta = {
        "restatement_id": restatement_id,
        "restatement_reason": restatement_reason,
        "restatement_date": now_iso(),
        "original_validation_id": original_validation_id,
    }
    result = publish_validated_pack(
        validated_pack=validated_pack,
        draft=draft,
        reason_for_change=f"restatement:{restatement_reason}",
        is_restatement=True,
        restatement_meta=meta,
    )
    if result.get("published"):
        meta["replacement_validation_id"] = validated_pack.get("validation_id")
        meta["replacement_fact_ids"] = [f["fact_id"] for f in result.get("facts") or []]
        path = warehouse_root() / "restatements" / f"{restatement_id.replace(':', '_')}.json"
        write_json_atomic(path, {**meta, "ticker": result.get("ticker"), "company_id": result.get("company_id")})
        result["restatement"] = meta
        result["restatement_path"] = str(path)
        # FSE-07: restatement → impacted derived metric recalculation (new versions only)
        try:
            from financial_statements_engine.derived_metrics.restatement.recalc import (
                recalculate_for_changed_facts,
            )

            changed = sorted(
                {
                    str(f.get("metric") or f.get("canonical_metric"))
                    for f in (result.get("facts") or [])
                    if f.get("metric") or f.get("canonical_metric")
                }
            )
            if changed and result.get("ticker"):
                result["dme_recalculation"] = recalculate_for_changed_facts(
                    str(result["ticker"]),
                    changed,
                    facts=list(result.get("facts") or []),
                )
        except Exception as exc:  # noqa: BLE001 — restatement must not fail on DME side effects
            result["dme_recalculation"] = {"ok": False, "error": str(exc)}
    return result


def restatement_history(company_id: str | None = None) -> list[dict[str, Any]]:
    root = warehouse_root() / "restatements"
    if not root.exists():
        return []
    rows = []
    for p in sorted(root.glob("rst_*.json")):
        try:
            row = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if company_id and row.get("company_id") != company_id:
            continue
        rows.append(row)
    return rows
