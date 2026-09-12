"""Disk persistence for KIL company state, snapshots, and events.

Shares durable root with Continuous Gather → Learn when CGL_STORE_ROOT / KIP_DATA_DIR
is set, so the HTTP process can see integrations performed by the gather sidecar.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()


def store_root() -> Path:
    raw = (
        os.getenv("KIL_STORE_ROOT")
        or (os.getenv("CGL_STORE_ROOT") and str(Path(os.getenv("CGL_STORE_ROOT")) / "kil"))
        or (os.getenv("KIP_DATA_DIR") and str(Path(os.getenv("KIP_DATA_DIR")) / "kil"))
        or ""
    ).strip()
    if raw:
        root = Path(raw)
    else:
        root = Path(__file__).resolve().parents[2] / "data" / "kil"
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("companies", "snapshots", "events", "metrics"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    try:
        from institutional_data.persistence.atomic import atomic_write_json, file_lock

        with file_lock(path):
            atomic_write_json(path, payload)
        return
    except Exception:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _company_key(ticker: str) -> str:
    t = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(ticker or "").upper())[:80]
    return t or "UNKNOWN"


def put_company(ticker: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a slim integration record (avoid huge packs on disk)."""
    t = str(ticker or "").upper().strip()
    slim = {
        "ok": bool(payload.get("ok")),
        "ticker": t,
        "entity_id": payload.get("entity_id"),
        "knowledge_version": payload.get("knowledge_version"),
        "financials_published": payload.get("financials_published"),
        "period_count": payload.get("period_count"),
        "transformed": payload.get("transformed"),
        "published": payload.get("published"),
        "company_memory": payload.get("company_memory"),
        "knowledge_graph_refreshed": payload.get("knowledge_graph_refreshed"),
        "knowledge_confidence": payload.get("knowledge_confidence"),
        "coverage_state": payload.get("coverage_state"),
        "institutional_coverage": payload.get("institutional_coverage"),
        "research_ready": payload.get("research_ready"),
        "claim_safe": payload.get("claim_safe"),
        "decision_eligibility": payload.get("decision_eligibility"),
        "pack_summary": payload.get("pack_summary"),
        "repaired": payload.get("repaired"),
        "updated_at": _now(),
        "schema": "KilCompanyState.v1",
    }
    with _LOCK:
        _write_json(store_root() / "companies" / f"{_company_key(t)}.json", slim)
        _refresh_index_locked()
    return slim


def get_company(ticker: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        row = _read_json(store_root() / "companies" / f"{_company_key(ticker)}.json")
    return dict(row) if isinstance(row, dict) and row else None


def list_companies(*, limit: int = 200) -> List[Dict[str, Any]]:
    with _LOCK:
        index = _read_json(store_root() / "metrics" / "company_index.json", {"tickers": []}) or {}
        tickers = list(index.get("tickers") or [])
        if not tickers:
            tickers = sorted(
                p.stem.upper()
                for p in (store_root() / "companies").glob("*.json")
                if p.is_file()
            )
        out: List[Dict[str, Any]] = []
        for t in tickers[: max(1, min(limit, 500))]:
            row = _read_json(store_root() / "companies" / f"{_company_key(t)}.json")
            if isinstance(row, dict) and row:
                out.append(row)
        return out


def company_count() -> int:
    with _LOCK:
        index = _read_json(store_root() / "metrics" / "company_index.json", {"tickers": []}) or {}
        tickers = list(index.get("tickers") or [])
        if tickers:
            return len(tickers)
        return len([p for p in (store_root() / "companies").glob("*.json") if p.is_file()])


def _refresh_index_locked() -> None:
    tickers = sorted(
        p.stem.upper() for p in (store_root() / "companies").glob("*.json") if p.is_file()
    )
    _write_json(
        store_root() / "metrics" / "company_index.json",
        {"tickers": tickers, "count": len(tickers), "updated_at": _now()},
    )


def append_snapshot(snap: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        body = {**snap, "persisted_at": _now()}
        sid = str(body.get("snapshot_id") or f"ks_{int(time.time())}")
        _write_json(store_root() / "snapshots" / f"{sid}.json", body)
        _write_json(store_root() / "metrics" / "latest_snapshot.json", body)
        index_path = store_root() / "metrics" / "snapshot_index.json"
        index = _read_json(index_path, {"ids": []}) or {"ids": []}
        ids = list(index.get("ids") or [])
        if sid not in ids:
            ids.append(sid)
        _write_json(index_path, {"ids": ids[-500:], "count": len(ids[-500:]), "updated_at": _now()})
        return body


def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    with _LOCK:
        row = _read_json(store_root() / "metrics" / "latest_snapshot.json")
    return dict(row) if isinstance(row, dict) and row else None


def list_snapshots(*, limit: int = 50) -> List[Dict[str, Any]]:
    with _LOCK:
        index = _read_json(store_root() / "metrics" / "snapshot_index.json", {"ids": []}) or {}
        ids = list(index.get("ids") or [])[-max(1, min(limit, 200)) :]
        out: List[Dict[str, Any]] = []
        for sid in ids:
            row = _read_json(store_root() / "snapshots" / f"{sid}.json")
            if isinstance(row, dict) and row:
                out.append(row)
        if not out:
            latest = _read_json(store_root() / "metrics" / "latest_snapshot.json")
            if isinstance(latest, dict) and latest:
                out = [latest]
        return out


def append_events(events: List[Dict[str, Any]]) -> int:
    if not events:
        return 0
    with _LOCK:
        n = 0
        index_path = store_root() / "metrics" / "event_index.json"
        index = _read_json(index_path, {"ids": []}) or {"ids": []}
        ids = list(index.get("ids") or [])
        for ev in events:
            if not isinstance(ev, dict):
                continue
            eid = str(ev.get("event_id") or f"evt_{int(time.time() * 1000)}_{n}")
            body = {**ev, "event_id": eid, "persisted_at": _now()}
            _write_json(store_root() / "events" / f"{eid}.json", body)
            if eid not in ids:
                ids.append(eid)
            n += 1
        _write_json(index_path, {"ids": ids[-2000:], "count": len(ids[-2000:]), "updated_at": _now()})
        return n


def list_events(*, limit: int = 100, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        index = _read_json(store_root() / "metrics" / "event_index.json", {"ids": []}) or {}
        ids = list(index.get("ids") or [])[-max(1, min(limit, 500)) :]
        out: List[Dict[str, Any]] = []
        for eid in ids:
            row = _read_json(store_root() / "events" / f"{eid}.json")
            if not isinstance(row, dict) or not row:
                continue
            if event_type and row.get("event_type") != event_type:
                continue
            out.append(row)
        return out


def write_integration_heartbeat(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    with _LOCK:
        body = {
            "role": os.getenv("AGI_ROLE") or "unknown",
            "pid": os.getpid(),
            "beat_at": _now(),
            "unix_ts": time.time(),
            **(payload or {}),
        }
        _write_json(store_root() / "metrics" / "kil_heartbeat.json", body)
        return body


def read_integration_heartbeat(*, max_age_sec: float = 900.0) -> Dict[str, Any]:
    with _LOCK:
        row = _read_json(store_root() / "metrics" / "kil_heartbeat.json", {}) or {}
    if not isinstance(row, dict) or not row:
        return {"fresh": False, "present": False}
    try:
        ts = float(row.get("unix_ts") or 0)
    except (TypeError, ValueError):
        ts = 0.0
    age = (time.time() - ts) if ts else None
    fresh = bool(age is not None and age >= 0 and age <= float(max_age_sec))
    return {
        **row,
        "present": True,
        "fresh": fresh,
        "age_sec": round(age, 1) if age is not None else None,
        "max_age_sec": float(max_age_sec),
    }
