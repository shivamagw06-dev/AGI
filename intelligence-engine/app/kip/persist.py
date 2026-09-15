"""Durable KIP snapshot — closes the control-plane / data-plane split.

Without this, KipStore is process-local RAM: Render Free cold starts wipe documents
while CMS still shows learn_status=learned (orphaned metadata → 404 on retrieval).

Persistence tiers (soft, Architecture v1.0.1 LOCKED):
1. Local JSON snapshot under KIP_DATA_DIR (or intelligence-engine/data/kip/)
2. Optional Supabase object row when SUPABASE_* credentials are present

Attach a Render persistent disk to KIP_DATA_DIR for true durability across deploys.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.kip.models import (
    GraphEdge,
    GraphNode,
    KipChunk,
    KipDocument,
    PredictionRecord,
    TimelineEvent,
)
from app.kip.store import KipStore

SNAPSHOT_VERSION = 1

# Render Free / git deploy paths are wiped on full rebuild. Durable mounts live under /var/data.
_EPHEMERAL_PATH_MARKERS = (
    "/opt/render/project/",
    "/tmp/",
)


def kip_data_dir() -> Path:
    raw = (os.environ.get("KIP_DATA_DIR") or "").strip()
    if raw:
        return Path(raw)
    # Default: beside the intelligence-engine package root (ephemeral on Render)
    return Path(__file__).resolve().parents[2] / "data" / "kip"


def snapshot_path() -> Path:
    override = (os.environ.get("KIP_SNAPSHOT_PATH") or "").strip()
    if override:
        return Path(override)
    return kip_data_dir() / "kip_snapshot.json"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _is_likely_mount(path: Path) -> bool | None:
    """Return True/False if /proc/mounts is readable; None if unknown."""
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8")
    except Exception:
        return None
    targets = {str(path), str(path.resolve()) if path.exists() else str(path)}
    for line in mounts.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] in targets:
            return True
    return False


def persistence_config() -> dict[str, Any]:
    """Report whether KIP snapshots will survive infrastructure restarts."""
    configured = bool((os.environ.get("KIP_DATA_DIR") or "").strip())
    data_dir = kip_data_dir()
    path_s = str(data_dir)
    try:
        resolved = str(data_dir.resolve())
    except Exception:
        resolved = path_s
    default_dir = Path(__file__).resolve().parents[2] / "data" / "kip"
    try:
        same_as_default = data_dir.resolve() == default_dir.resolve()
    except Exception:
        same_as_default = path_s == str(default_dir)

    looks_ephemeral = (
        (not configured)
        or same_as_default
        or any(m in path_s for m in _EPHEMERAL_PATH_MARKERS)
        or any(m in resolved for m in _EPHEMERAL_PATH_MARKERS)
    )
    mount_status = _is_likely_mount(data_dir) if configured else None
    supabase_url = bool((os.environ.get("SUPABASE_URL") or "").strip())
    supabase_key = bool((os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip())
    supabase_mirror = supabase_url and supabase_key
    durable = configured and not looks_ephemeral
    warning = None
    if not durable:
        warning = (
            "WARNING: Persistent KIP storage is disabled. "
            "Institutional memory may be lost after restart. "
            "Attach a Render disk at /var/data/kip and set KIP_DATA_DIR=/var/data/kip."
        )
    elif mount_status is False:
        warning = (
            "WARNING: KIP_DATA_DIR is set but does not appear to be a mounted volume. "
            "Confirm the Render persistent disk is attached at this path, or institutional "
            "memory may still be lost after a full rebuild."
        )
    return {
        "configured": configured,
        "durable": durable,
        "looks_ephemeral": looks_ephemeral,
        "disk_mounted": mount_status,
        "kip_data_dir": path_s,
        "snapshot_path": str(snapshot_path()),
        "supabase_mirror": supabase_mirror,
        "allow_ephemeral": _env_flag("KIP_ALLOW_EPHEMERAL"),
        "warning": warning,
        "hint": (
            "Attach a Render persistent disk mounted at /var/data/kip, set "
            "KIP_DATA_DIR=/var/data/kip, and set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY "
            "for an optional remote mirror."
        ),
    }


def enforce_persistent_kip_or_raise(*, app_env: str | None = None) -> dict[str, Any]:
    """Warn (and optionally refuse) when KIP is not on durable storage.

    Default: loud warning only — so Render Free→Starter upgrades can succeed
    before a paid disk is attached (disk cannot attach on Free; plan change
    only applies after a successful deploy).

    Strict mode: set KIP_REQUIRE_PERSISTENT=1 after the disk is mounted to
    refuse boot when KIP_DATA_DIR is unset / ephemeral.
    Escape hatch: KIP_ALLOW_EPHEMERAL=1.
    """
    cfg = persistence_config()
    env = (app_env or os.environ.get("APP_ENV") or os.environ.get("ENV") or "development").strip().lower()
    production = env in {"production", "prod", "staging"}
    require = _env_flag("KIP_REQUIRE_PERSISTENT")
    if (
        production
        and require
        and not cfg["durable"]
        and not cfg["allow_ephemeral"]
    ):
        raise RuntimeError(
            "KIP_REQUIRE_PERSISTENT=1 but durable KIP storage is not configured. "
            "Attach a Render persistent disk (mount /var/data/kip), set "
            "KIP_DATA_DIR=/var/data/kip, or set KIP_ALLOW_EPHEMERAL=1 to bypass "
            "(institutional memory will not survive restarts)."
        )
    return cfg


def export_store(store: KipStore) -> dict[str, Any]:
    with store._lock:
        docs = [d.model_dump(mode="json") for d in store.documents.values()]
        chunks = [c.model_dump(mode="json") for c in store.chunks]
        nodes = [n.model_dump(mode="json") for n in store.nodes.values()]
        edges = [e.model_dump(mode="json") for e in store.edges]
        predictions = [p.model_dump(mode="json") for p in store.predictions.values()]
        timeline: dict[str, list[dict[str, Any]]] = {}
        for ticker, events in store.timeline.items():
            timeline[ticker] = [ev.model_dump(mode="json") for ev in events]
        lineages = {k: list(v) for k, v in store.lineages.items()}
        themes = {k: sorted(v) for k, v in store.themes.items()}
        company_docs = {k: sorted(v) for k, v in store.company_docs.items()}
        article_index = dict(store.article_index)
        stats = {
            "documents": len(docs),
            "chunks": len(chunks),
            "graph_nodes": len(nodes),
            "graph_edges": len(edges),
            "predictions": len(predictions),
            "articles": len(article_index),
        }
    return {
        "version": SNAPSHOT_VERSION,
        "platform": "KIP",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "documents": docs,
        "chunks": chunks,
        "nodes": nodes,
        "edges": edges,
        "predictions": predictions,
        "timeline": timeline,
        "lineages": lineages,
        "themes": themes,
        "company_docs": company_docs,
        "article_index": article_index,
        "stats": stats,
    }


def _legacy_default_snapshot_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "kip" / "kip_snapshot.json"


def save_store(store: KipStore, path: Path | None = None) -> dict[str, Any]:
    target = path or snapshot_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # Common during Free→Starter upgrade: KIP_DATA_DIR points at /var/data/kip
        # before the paid disk is attached / writable.
        legacy = _legacy_default_snapshot_path()
        if path is None and target.resolve() != legacy.resolve():
            legacy.parent.mkdir(parents=True, exist_ok=True)
            fallback = save_store(store, path=legacy)
            fallback["ok"] = True
            fallback["writable"] = False
            fallback["fallback_reason"] = f"primary_unwritable: {exc}"
            fallback["requested_path"] = str(target)
            return fallback
        raise
    payload = export_store(store)
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(target)
    except OSError as exc:
        legacy = _legacy_default_snapshot_path()
        if path is None and target.resolve() != legacy.resolve():
            fallback = save_store(store, path=legacy)
            fallback["ok"] = True
            fallback["writable"] = False
            fallback["fallback_reason"] = f"primary_write_failed: {exc}"
            fallback["requested_path"] = str(target)
            return fallback
        raise
    result = {
        "ok": True,
        "path": str(target),
        "bytes": target.stat().st_size,
        "writable": True,
        **payload["stats"],
        "saved_at": payload["saved_at"],
    }
    # Soft optional remote mirror (never fails local save).
    remote = _save_supabase_mirror(payload)
    if remote:
        result["supabase"] = remote
    return result


def load_store(store: KipStore, path: Path | None = None) -> dict[str, Any]:
    target = path or snapshot_path()
    payload: dict[str, Any] | None = None
    source = "none"
    migrated_from: str | None = None
    if target.exists():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            source = "disk"
        except Exception as exc:
            return {"ok": False, "error": f"disk_load_failed: {exc}", "path": str(target)}
    if payload is None:
        # One-time migrate: durable mount empty, but prior ephemeral snapshot still present.
        legacy = _legacy_default_snapshot_path()
        if legacy.exists() and legacy.resolve() != target.resolve():
            try:
                payload = json.loads(legacy.read_text(encoding="utf-8"))
                source = "disk_legacy_migrate"
                migrated_from = str(legacy)
            except Exception:
                payload = None
    if payload is None:
        remote = _load_supabase_mirror()
        if remote.get("ok") and remote.get("payload"):
            payload = remote["payload"]
            source = "supabase"
        else:
            return {
                "ok": True,
                "loaded": False,
                "reason": "no_snapshot",
                "path": str(target),
                "supabase": remote,
            }

    docs = [KipDocument.model_validate(d) for d in payload.get("documents") or []]
    chunks = [KipChunk.model_validate(c) for c in payload.get("chunks") or []]
    nodes = {
        n["node_id"]: GraphNode.model_validate(n) for n in (payload.get("nodes") or []) if n.get("node_id")
    }
    edges = [GraphEdge.model_validate(e) for e in payload.get("edges") or []]
    predictions = {
        p["prediction_id"]: PredictionRecord.model_validate(p)
        for p in (payload.get("predictions") or [])
        if p.get("prediction_id")
    }
    timeline: dict[str, list[TimelineEvent]] = defaultdict(list)
    for ticker, events in (payload.get("timeline") or {}).items():
        timeline[str(ticker).upper()] = [TimelineEvent.model_validate(ev) for ev in events]

    with store._lock:
        store.documents = {d.document_id: d for d in docs}
        store.chunks = chunks
        store.nodes = nodes
        store.edges = edges
        store.predictions = predictions
        store.timeline = timeline
        store.lineages = defaultdict(list, {k: list(v) for k, v in (payload.get("lineages") or {}).items()})
        store.themes = defaultdict(
            set, {k: set(v) for k, v in (payload.get("themes") or {}).items()}
        )
        store.company_docs = defaultdict(
            set, {k: set(v) for k, v in (payload.get("company_docs") or {}).items()}
        )
        store.article_index = dict(payload.get("article_index") or {})
        # Rebuild indexes if snapshot omitted them
        if not store.article_index:
            for d in docs:
                if d.article_id:
                    store.article_index[d.article_id] = d.document_id
        if not store.company_docs:
            for d in docs:
                for t in d.investment.tickers:
                    store.company_docs[t.upper()].add(d.document_id)
        if not store.themes:
            for d in docs:
                for theme in d.investment.themes:
                    store.themes[theme.lower()].add(d.document_id)

    result = {
        "ok": True,
        "loaded": True,
        "source": source,
        "path": str(target),
        "saved_at": payload.get("saved_at"),
        **store.stats(),
    }
    if migrated_from:
        result["migrated_from"] = migrated_from
        try:
            saved = save_store(store, path=target)
            result["migrated_to"] = saved.get("path")
            result["migrate_saved"] = bool(saved.get("ok"))
        except Exception as exc:
            result["migrate_saved"] = False
            result["migrate_error"] = str(exc)[:160]
    return result


def integrity_report(
    store: KipStore,
    *,
    sample_limit: int = 25,
    expected_document_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Detect control-plane vs data-plane split (orphans / missing docs / empty vectors)."""
    with store._lock:
        docs = list(store.documents.values())
        chunks = list(store.chunks)
        chunk_by_doc: dict[str, list[KipChunk]] = defaultdict(list)
        for c in chunks:
            chunk_by_doc[c.document_id].append(c)

        missing_chunks: list[str] = []
        missing_embeddings: list[str] = []
        for d in docs:
            dc = chunk_by_doc.get(d.document_id) or []
            if not dc:
                missing_chunks.append(d.document_id)
                continue
            if not any(c.embedding for c in dc):
                missing_embeddings.append(d.document_id)

        orphan_chunks = [c.chunk_id for c in chunks if c.document_id not in store.documents]
        vector_chunks = sum(1 for c in chunks if c.embedding)

        expected = expected_document_ids or []
        missing_expected = [i for i in expected if i not in store.documents]

        sample = []
        for d in docs[:sample_limit]:
            dc = chunk_by_doc.get(d.document_id) or []
            sample.append(
                {
                    "document_id": d.document_id,
                    "title": (d.document.title if d.document else "")[:120],
                    "chunks": len(dc),
                    "has_embeddings": any(bool(c.embedding) for c in dc),
                    "article_id": d.article_id,
                }
            )

        stats = store.stats()

    healthy = (
        stats["documents"] > 0
        and len(missing_chunks) == 0
        and len(missing_embeddings) == 0
        and len(orphan_chunks) == 0
        and len(missing_expected) == 0
        and vector_chunks > 0
    )
    persist_cfg = persistence_config()
    return {
        "ok": True,
        "healthy": healthy,
        "persistence": {
            **persist_cfg,
            "snapshot_exists": snapshot_path().exists(),
        },
        "stats": {
            **stats,
            "vector_chunks": vector_chunks,
            "docs_missing_chunks": len(missing_chunks),
            "docs_missing_embeddings": len(missing_embeddings),
            "orphan_chunks": len(orphan_chunks),
            "expected_missing": len(missing_expected),
        },
        "missing_chunks": missing_chunks[:50],
        "missing_embeddings": missing_embeddings[:50],
        "orphan_chunk_ids": orphan_chunks[:50],
        "expected_missing_ids": missing_expected[:50],
        "sample": sample,
        "split_brain_risk": (not healthy) or stats["documents"] < 3 or (not persist_cfg.get("durable")),
    }


def verify_document_retrievable(store: KipStore, document_id: str) -> dict[str, Any]:
    doc = store.get_document(document_id)
    if doc is None:
        return {
            "ok": False,
            "retrievable": False,
            "document_id": document_id,
            "error": "document_missing",
        }
    with store._lock:
        chunks = [c for c in store.chunks if c.document_id == document_id]
    if not chunks:
        return {
            "ok": False,
            "retrievable": False,
            "document_id": document_id,
            "error": "chunks_missing",
        }
    if not any(c.embedding for c in chunks):
        return {
            "ok": False,
            "retrievable": False,
            "document_id": document_id,
            "error": "embeddings_missing",
            "chunks": len(chunks),
        }
    return {
        "ok": True,
        "retrievable": True,
        "document_id": document_id,
        "chunks": len(chunks),
        "title": doc.document.title if doc.document else "",
    }


def _supabase_client():
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client  # type: ignore

        return create_client(url, key)
    except Exception:
        return None


def _save_supabase_mirror(payload: dict[str, Any]) -> dict[str, Any] | None:
    client = _supabase_client()
    if client is None:
        return None
    try:
        row = {
            "id": "kip_snapshot_v1",
            "saved_at": payload.get("saved_at"),
            "stats": payload.get("stats") or {},
            "payload": payload,
        }
        client.table("kip_snapshots").upsert(row).execute()
        return {"ok": True, "table": "kip_snapshots", "id": "kip_snapshot_v1"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _load_supabase_mirror() -> dict[str, Any]:
    client = _supabase_client()
    if client is None:
        return {"ok": False, "skipped": True, "reason": "no_supabase"}
    try:
        res = (
            client.table("kip_snapshots")
            .select("payload,saved_at")
            .eq("id", "kip_snapshot_v1")
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return {"ok": False, "reason": "empty"}
        return {"ok": True, "payload": rows[0].get("payload"), "saved_at": rows[0].get("saved_at")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
