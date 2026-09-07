"""Process-local Ask observability ring buffer for Mission Control KPIs."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from statistics import mean
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

_LOCK = Lock()
_TRACES: Deque[dict[str, Any]] = deque(maxlen=200)
_PARTIAL: Dict[str, dict[str, Any]] = {}
# Phase-1 full pipeline debug payloads keyed by request_id (ask_* / legacy ASK-*).
_PIPELINE: Dict[str, dict[str, Any]] = {}
_PIPELINE_ORDER: Deque[str] = deque(maxlen=200)


def record_partial_trace(row: dict[str, Any]) -> None:
    """In-flight checkpoint — survives hangs until final record_trace."""
    if not isinstance(row, dict) or not row:
        return
    tid = row.get("ask_trace_id") or row.get("request_id")
    if not tid:
        return
    slim = {
        "ask_trace_id": tid,
        "request_id": row.get("request_id") or tid,
        "ts": row.get("ts"),
        "partial": True,
        "completed": bool(row.get("completed")),
        "timeout": bool(row.get("timeout")),
        "last_completed_stage": row.get("last_completed_stage") or row.get("checkpoint_stage"),
        "elapsed_ms": row.get("elapsed_ms"),
        "fallback": bool(row.get("fallback") or row.get("fallback_used")),
        "engine_reached": bool(row.get("engine_reached", True)),
        "entity": row.get("entity") or {},
        "evidence": row.get("evidence") or row.get("funnel") or {},
        "latency": row.get("latency") or row.get("latency_ms") or {},
        "ikl": row.get("ikl") or {},
        "stage_warnings": row.get("stage_warnings") or [],
        "trace_summary": row.get("trace_summary"),
        "execution_trace": row.get("execution_trace"),
    }
    with _LOCK:
        for key in _pipeline_keys(str(tid)):
            _PARTIAL[key] = slim


def get_partial_trace(ask_trace_id: str) -> Optional[dict[str, Any]]:
    with _LOCK:
        for key in _pipeline_keys(str(ask_trace_id or "")):
            row = _PARTIAL.get(key)
            if row:
                return deepcopy(row)
        return None


def _pipeline_keys(request_id: str) -> List[str]:
    """Lookup variants so ask_* and legacy ASK-* resolve to the same bag."""
    rid = str(request_id or "").strip()
    keys = [rid]
    if rid.lower().startswith("ask_"):
        parts = rid.split("_")
        if len(parts) >= 3:
            keys.append(f"ASK-{parts[1]}-{''.join(parts[2:]).upper()}")
    if rid.upper().startswith("ASK-"):
        try:
            from app.ui.ask_pipeline_trace import normalize_request_id

            keys.append(normalize_request_id(rid))
        except Exception:
            pass
    # de-dupe preserve order
    out: List[str] = []
    for k in keys:
        if k and k not in out:
            out.append(k)
    return out


def record_pipeline_trace(row: dict[str, Any], *, final: bool = False) -> None:
    """Persist Phase-1 pipeline debug payload for GET /v1/debug/request/{id}."""
    if not isinstance(row, dict) or not row:
        return
    rid = str(row.get("request_id") or row.get("ask_trace_id") or "").strip()
    if not rid:
        return
    slim = deepcopy(row)
    slim.pop("_trace_obj", None)
    slim["partial"] = not final and slim.get("status") == "in_progress"
    slim["ts"] = slim.get("ts") or slim.get("timestamp")
    with _LOCK:
        for key in _pipeline_keys(rid):
            _PIPELINE[key] = slim
        if rid not in _PIPELINE_ORDER:
            _PIPELINE_ORDER.appendleft(rid)
        # Bound memory
        while len(_PIPELINE_ORDER) > 200:
            old = _PIPELINE_ORDER.pop()
            for key in _pipeline_keys(old):
                _PIPELINE.pop(key, None)


def get_pipeline_trace(request_id: str) -> Optional[dict[str, Any]]:
    with _LOCK:
        for key in _pipeline_keys(str(request_id or "")):
            row = _PIPELINE.get(key)
            if row:
                return deepcopy(row)
        return None


def get_request_debug(request_id: str) -> Optional[dict[str, Any]]:
    """Unified debug view: pipeline trace preferred, else partial/final orch trace."""
    pipe = get_pipeline_trace(request_id)
    if pipe:
        return pipe
    partial = get_partial_trace(request_id)
    if partial:
        return {
            "request_id": request_id,
            "ask_trace_id": partial.get("ask_trace_id") or request_id,
            "status": "partial" if partial.get("partial") else "unknown",
            "fallback_used": bool(partial.get("fallback")),
            "total_latency_ms": partial.get("elapsed_ms"),
            "entities": [partial.get("entity")] if partial.get("entity") else [],
            "evidence_count": (partial.get("evidence") or {}).get("retrieved"),
            "latency_breakdown": partial.get("latency") or {},
            "events": [],
            "note": "pipeline trace not found; returning partial orchestration checkpoint",
            "partial": True,
        }
    with _LOCK:
        for t in _TRACES:
            tid = str(t.get("ask_trace_id") or "")
            if tid == str(request_id or "") or tid in _pipeline_keys(str(request_id or "")):
                return {
                    "request_id": request_id,
                    "ask_trace_id": tid,
                    "status": "success" if t.get("completed") else "unknown",
                    "fallback_used": bool(t.get("fallback")),
                    "total_latency_ms": t.get("elapsed_ms"),
                    "entities": [t.get("entity")] if t.get("entity") else [],
                    "evidence_count": (t.get("evidence") or {}).get("retrieved"),
                    "latency_breakdown": t.get("latency") or {},
                    "events": [],
                    "note": "pipeline trace not found; returning completed orch summary",
                }
    return None


def record_trace(row: dict[str, Any]) -> None:
    if not isinstance(row, dict) or not row:
        return
    slim = {
        "ask_trace_id": row.get("ask_trace_id"),
        "ts": row.get("ts"),
        "partial": bool(row.get("partial")),
        "completed": row.get("completed"),
        "timeout": bool(row.get("timeout")),
        "last_completed_stage": row.get("last_completed_stage")
        or (row.get("latency") or {}).get("last_completed_stage"),
        "elapsed_ms": row.get("elapsed_ms"),
        "fallback": bool(row.get("fallback") or row.get("fallback_used")),
        "engine_reached": bool(row.get("engine_reached", True)),
        "entity": row.get("entity") or {},
        "evidence": row.get("evidence") or row.get("funnel") or {},
        "latency": row.get("latency") or row.get("latency_ms") or {},
        "executive_overwritten": bool(row.get("executive_overwritten")),
        "grounding": row.get("grounding"),
        "intent": row.get("intent"),
        "trace_summary": row.get("trace_summary"),
        "execution_trace": row.get("execution_trace"),
        "stage_warnings": row.get("stage_warnings")
        or (row.get("latency") or {}).get("warnings")
        or [],
        "rejected": (row.get("entity") or {}).get("rejected_candidates")
        or row.get("ticker_rejects")
        or [],
        "attribution_count": len(row.get("executive_attribution") or []),
        "attribution_grounded": sum(
            1 for a in (row.get("executive_attribution") or []) if isinstance(a, dict) and a.get("grounded")
        ),
    }
    with _LOCK:
        _TRACES.appendleft(slim)
        tid = str(row.get("ask_trace_id") or "")
        if tid and tid in _PARTIAL:
            del _PARTIAL[tid]


def recent_traces(*, limit: int = 25) -> List[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(t) for t in list(_TRACES)[: max(1, min(limit, 100))]]


def _pct(n: int, d: int) -> Optional[float]:
    if d <= 0:
        return None
    return round(n / d, 3)


def _avg(vals: List[float]) -> Optional[float]:
    return round(mean(vals), 3) if vals else None


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return float(s[0])
    idx = int(round((p / 100.0) * (len(s) - 1)))
    return float(s[max(0, min(idx, len(s) - 1))])


def kpi_dashboard() -> Dict[str, Any]:
    with _LOCK:
        rows = [deepcopy(t) for t in _TRACES]
    total = len(rows)
    if total == 0:
        return {
            "ok": True,
            "sample_size": 0,
            "note": "No Ask traces recorded in this process yet.",
            "entity": {},
            "funnel": {},
            "latency": {},
            "executive": {},
            "kpis": {},
            "recent": [],
        }

    entity_ok = 0
    confs: List[float] = []
    rejected_freq: Dict[str, int] = {}
    retrieved_vals: List[float] = []
    ranked_vals: List[float] = []
    passed_vals: List[float] = []
    referenced_vals: List[float] = []
    util_vals: List[float] = []
    eff_vals: List[float] = []
    prec_vals: List[float] = []
    lat_entity: List[float] = []
    lat_retrieval: List[float] = []
    lat_ranking: List[float] = []
    lat_reasoning: List[float] = []
    lat_assembly: List[float] = []
    lat_total: List[float] = []
    fallback_n = 0
    attr_refs: List[float] = []
    attr_paras: List[float] = []

    for r in rows:
        ent = r.get("entity") or {}
        if ent.get("detected") or ent.get("name"):
            entity_ok += 1
        try:
            c = float(ent.get("confidence"))
            confs.append(c)
        except (TypeError, ValueError):
            pass
        for rej in r.get("rejected") or []:
            raw = rej.get("raw") if isinstance(rej, dict) else rej
            key = str(raw or "").upper()
            if key:
                rejected_freq[key] = rejected_freq.get(key, 0) + 1
        ev = r.get("evidence") or {}
        for key, bucket in (
            ("retrieved", retrieved_vals),
            ("ranked", ranked_vals),
            ("passed", passed_vals),
            ("passed_to_ice", passed_vals),
            ("referenced", referenced_vals),
            ("utilization", util_vals),
            ("efficiency", eff_vals),
            ("precision", prec_vals),
        ):
            if ev.get(key) is None:
                continue
            try:
                bucket.append(float(ev[key]))
            except (TypeError, ValueError):
                pass
        lat = r.get("latency") or {}

        def _pick(bucket: List[float], *keys: str) -> None:
            for key in keys:
                if lat.get(key) is None:
                    continue
                try:
                    bucket.append(float(lat[key]))
                    return
                except (TypeError, ValueError):
                    continue

        _pick(lat_entity, "entity_ms", "entity_resolution")
        _pick(lat_retrieval, "retrieval_ms", "retrieval")
        _pick(lat_ranking, "ranking_ms", "ranking")
        _pick(lat_reasoning, "reasoning_ms", "reasoning")
        _pick(lat_assembly, "assembly_ms", "response_assembly", "executive_assembly")
        _pick(lat_total, "total_ms", "total")
        if r.get("fallback"):
            fallback_n += 1
        attr_refs.append(float(r.get("attribution_grounded") or 0))
        attr_paras.append(float(r.get("attribution_count") or 0))

    top_rejected = sorted(rejected_freq.items(), key=lambda kv: (-kv[1], kv[0]))[:12]

    return {
        "ok": True,
        "sample_size": total,
        "entity": {
            "success_rate": _pct(entity_ok, total),
            "average_confidence": _avg(confs),
            "top_rejected": [{"token": k, "count": v} for k, v in top_rejected],
        },
        "funnel": {
            "avg_retrieved": _avg(retrieved_vals),
            "avg_ranked": _avg(ranked_vals),
            "avg_passed": _avg(passed_vals),
            "avg_referenced": _avg(referenced_vals),
            "avg_utilization": _avg(util_vals),
            "avg_efficiency": _avg(eff_vals),
            "avg_precision": _avg(prec_vals),
        },
        "latency": {
            "avg_entity_ms": _avg(lat_entity),
            "avg_retrieval_ms": _avg(lat_retrieval),
            "avg_ranking_ms": _avg(lat_ranking),
            "avg_reasoning_ms": _avg(lat_reasoning),
            "avg_assembly_ms": _avg(lat_assembly),
            "avg_total_ms": _avg(lat_total),
            "p95_total_ms": _percentile(lat_total, 95),
            "p99_total_ms": _percentile(lat_total, 99),
            "timeout_or_fallback_rate": _pct(fallback_n, total),
        },
        "executive": {
            "avg_paragraphs": _avg(attr_paras),
            "avg_grounded_refs": _avg(attr_refs),
        },
        "kpis": {
            "entity_success_rate": _pct(entity_ok, total),
            "average_entity_confidence": _avg(confs),
            "avg_retrieved_docs": _avg(retrieved_vals),
            "avg_referenced_docs": _avg(referenced_vals),
            "evidence_utilization": _avg(util_vals),
            "evidence_efficiency": _avg(eff_vals),
            "retrieval_precision": _avg(prec_vals),
            "reasoning_latency_ms": _avg(lat_reasoning),
            "fallback_rate": _pct(fallback_n, total),
        },
        "recent": rows[:15],
    }


def reset_for_tests() -> None:
    with _LOCK:
        _TRACES.clear()
        _PARTIAL.clear()
        _PIPELINE.clear()
        _PIPELINE_ORDER.clear()
