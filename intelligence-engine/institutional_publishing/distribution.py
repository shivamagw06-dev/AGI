"""PUB-01 distribution — destinations decoupled from builders."""

from __future__ import annotations

from typing import Any, Optional

from institutional_publishing.schema import DISTRIBUTION_TARGETS

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_HISTORY: list[dict[str, Any]] = []


def reset_for_tests() -> None:
    _HISTORY.clear()


def distribute(
    publication: dict[str, Any],
    *,
    target: str = "workspace",
    renderer: str = "markdown",
    artifact: Any = None,
) -> dict[str, Any]:
    dest = str(target or "workspace").lower().strip()
    if dest not in DISTRIBUTION_TARGETS:
        return {
            "ok": False,
            "error": f"unsupported distribution target: {dest}",
            "supported": list(DISTRIBUTION_TARGETS),
        }

    record = {
        "ok": True,
        "target": dest,
        "renderer": renderer,
        "publication_id": publication.get("publication_id"),
        "publication_type": publication.get("publication_type"),
        "distributed_at": now_iso(),
        "status": "delivered" if dest in {"workspace", "api", "archive", "export"} else "queued",
        "artifact_present": artifact is not None,
        "manifest_lineage_hash": (publication.get("manifest") or {}).get("lineage_hash"),
        "decoupled_from_builder": True,
    }
    if dest == "email":
        record["status"] = "queued"
        record["note"] = "Email distribution queued — transport configured externally"
    if dest == "export":
        record["export_ready"] = True
    if dest == "archive":
        record["archived"] = True
    if dest == "workspace":
        record["workspace_tab"] = "Publications"
    _HISTORY.append(record)
    return record


def distribution_history(limit: int = 20) -> list[dict[str, Any]]:
    return list(reversed(_HISTORY[-limit:]))


def metrics() -> dict[str, Any]:
    by_target: dict[str, int] = {}
    failed = 0
    for row in _HISTORY:
        by_target[row.get("target") or "unknown"] = by_target.get(row.get("target") or "unknown", 0) + 1
        if not row.get("ok"):
            failed += 1
    return {
        "distributed_count": len(_HISTORY),
        "by_target": by_target,
        "failed": failed,
        "targets": list(DISTRIBUTION_TARGETS),
    }
