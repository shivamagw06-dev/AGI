"""Ask Phase-1 pipeline observability — named stages, request_id, debug payload.

Observability only. Does not change retrieval, prompts, or LLM behavior.
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger("agi.ask.pipeline")

# Named stages (Phase-1 contract)
STAGE_REQUEST_RECEIVED = "REQUEST_RECEIVED"
STAGE_REQUEST_FORWARDED = "REQUEST_FORWARDED"
STAGE_ENGINE_RECEIVED = "ENGINE_RECEIVED"
STAGE_INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
STAGE_ENTITY_EXTRACTED = "ENTITY_EXTRACTED"
STAGE_RETRIEVAL_STARTED = "RETRIEVAL_STARTED"
STAGE_RETRIEVAL_COMPLETED = "RETRIEVAL_COMPLETED"
STAGE_EVIDENCE_FUSED = "EVIDENCE_FUSED"
STAGE_PROMPT_BUILT = "PROMPT_BUILT"
STAGE_LLM_STARTED = "LLM_STARTED"
STAGE_LLM_COMPLETED = "LLM_COMPLETED"
STAGE_RESPONSE_SENT = "RESPONSE_SENT"
STAGE_FALLBACK_USED = "FALLBACK_USED"
STAGE_ERROR = "ERROR"

PIPELINE_STAGES: tuple[str, ...] = (
    STAGE_REQUEST_RECEIVED,
    STAGE_REQUEST_FORWARDED,
    STAGE_ENGINE_RECEIVED,
    STAGE_INTENT_CLASSIFIED,
    STAGE_ENTITY_EXTRACTED,
    STAGE_RETRIEVAL_STARTED,
    STAGE_RETRIEVAL_COMPLETED,
    STAGE_EVIDENCE_FUSED,
    STAGE_PROMPT_BUILT,
    STAGE_LLM_STARTED,
    STAGE_LLM_COMPLETED,
    STAGE_RESPONSE_SENT,
    STAGE_FALLBACK_USED,
    STAGE_ERROR,
)

# Canonical source names for per-source retrieval rows (observability labels only).
SOURCE_LABELS: Dict[str, str] = {
    "knowledge_factory": "Knowledge Factory",
    "kf": "Knowledge Factory",
    "krig": "Knowledge Factory",
    "kip": "KIP",
    "finance_academy": "Academy",
    "academy": "Academy",
    "academy_books": "Academy",
    "multi_source": "Private Markets",
    "private_markets": "Private Markets",
    "valuation": "Valuation",
    "ve": "Valuation",
    "nifty": "Nifty Scores",
    "market_indices": "Nifty Scores",
    "live_filings": "Live Filings",
    "live_evidence": "Live Market",
    "leo": "Live Market",
    "finance_retrieval": "Live Filings",
    "fre": "Live Filings",
}


def new_request_id() -> str:
    """Canonical Phase-1 request id: ask_YYYYMMDD_<hex>."""
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ask_{day}_{secrets.token_hex(4)}"


def normalize_request_id(raw: Optional[str]) -> str:
    """Accept ask_* / ASK-* / empty → always return a usable request_id."""
    s = (raw or "").strip()
    if not s:
        return new_request_id()
    # Legacy ASK-YYYYMMDD-HEX → ask_YYYYMMDD_hex
    if s.upper().startswith("ASK-") and "_" not in s[:4]:
        parts = s.split("-")
        if len(parts) >= 3:
            day = parts[1]
            hexpart = "".join(parts[2:]).lower()
            if day.isdigit() and hexpart:
                return f"ask_{day}_{hexpart}"
    if s.lower().startswith("ask_"):
        return s if s.startswith("ask_") else s.lower()
    return s


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AskPipelineTrace:
    """Mutable per-request pipeline recorder (process-local)."""

    def __init__(
        self,
        *,
        request_id: Optional[str] = None,
        question: str = "",
    ) -> None:
        self.request_id = normalize_request_id(request_id)
        # Backward-compatible alias used by existing orch / Mission Control.
        self.ask_trace_id = self.request_id
        self.question = (question or "")[:500]
        self._t0 = time.perf_counter()
        self._last = self._t0
        self.events: List[Dict[str, Any]] = []
        self.intent: Optional[str] = None
        self.intent_confidence: Optional[float] = None
        self.intent_why_unknown: Optional[str] = None
        self.entities: List[Dict[str, Any]] = []
        self.entity_note: Optional[str] = None
        self.sources: List[Dict[str, Any]] = []
        self.evidence_count: int = 0
        self.evidence_used: int = 0
        self.top_evidence_ids: List[str] = []
        self.evidence_sources: List[str] = []
        self.prompt: Dict[str, Any] = {}
        self.llm: Dict[str, Any] = {}
        self.fallback_used: bool = False
        self.fallback_reason: Optional[str] = None
        self.status: str = "in_progress"
        self.error: Optional[Dict[str, Any]] = None
        self.latency_breakdown: Dict[str, int] = {}
        self._persist()

    def elapsed_ms(self) -> int:
        return max(0, int((time.perf_counter() - self._t0) * 1000))

    def mark(
        self,
        stage: str,
        *,
        status: str = "ok",
        detail: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = time.perf_counter()
        dur = (
            max(0, int(duration_ms))
            if duration_ms is not None
            else max(0, int((now - self._last) * 1000))
        )
        self._last = now
        event = {
            "stage": stage,
            "timestamp": _iso_now(),
            "request_id": self.request_id,
            "duration_ms": dur,
            "status": status,
            "elapsed_ms": self.elapsed_ms(),
        }
        if detail:
            event["detail"] = detail
        self.events.append(event)
        # Latency breakdown by short key
        key = stage.lower().replace("_", "")
        short_map = {
            STAGE_REQUEST_RECEIVED: "node_receive_ms",
            STAGE_REQUEST_FORWARDED: "node_forward_ms",
            STAGE_ENGINE_RECEIVED: "engine_receive_ms",
            STAGE_INTENT_CLASSIFIED: "intent_ms",
            STAGE_ENTITY_EXTRACTED: "entity_ms",
            STAGE_RETRIEVAL_STARTED: "retrieval_start_ms",
            STAGE_RETRIEVAL_COMPLETED: "retrieval_ms",
            STAGE_EVIDENCE_FUSED: "fusion_ms",
            STAGE_PROMPT_BUILT: "prompt_build_ms",
            STAGE_LLM_STARTED: "llm_start_ms",
            STAGE_LLM_COMPLETED: "llm_ms",
            STAGE_RESPONSE_SENT: "formatting_ms",
            STAGE_FALLBACK_USED: "fallback_ms",
            STAGE_ERROR: "error_ms",
        }
        bucket = short_map.get(stage) or f"{key}_ms"
        self.latency_breakdown[bucket] = int(self.latency_breakdown.get(bucket) or 0) + dur
        _LOG.info(
            "ask_pipeline request_id=%s stage=%s status=%s duration_ms=%s elapsed_ms=%s",
            self.request_id,
            stage,
            status,
            dur,
            event["elapsed_ms"],
        )
        self._persist()
        return event

    def set_intent(
        self,
        intent: Optional[str],
        *,
        confidence: Optional[float] = None,
        latency_ms: Optional[int] = None,
        why_unknown: Optional[str] = None,
    ) -> None:
        self.intent = intent or "Unknown"
        self.intent_confidence = confidence
        self.intent_why_unknown = why_unknown
        detail: Dict[str, Any] = {
            "intent": self.intent,
            "confidence": confidence,
        }
        if why_unknown:
            detail["why_unknown"] = why_unknown
        self.mark(
            STAGE_INTENT_CLASSIFIED,
            status="ok" if intent and str(intent).lower() != "unknown" else "unknown",
            detail=detail,
            duration_ms=latency_ms,
        )

    def set_entities(
        self,
        entities: List[Dict[str, Any]] | List[str],
        *,
        confidence: Optional[float] = None,
        aliases_matched: Optional[List[str]] = None,
        latency_ms: Optional[int] = None,
        none_found: bool = False,
    ) -> None:
        rows: List[Dict[str, Any]] = []
        for e in entities or []:
            if isinstance(e, str):
                rows.append({"name": e, "confidence": confidence})
            elif isinstance(e, dict):
                rows.append(e)
        self.entities = rows
        if none_found or not rows:
            self.entity_note = "No entity found"
        detail: Dict[str, Any] = {
            "entities": rows,
            "confidence": confidence,
            "aliases_matched": list(aliases_matched or []),
        }
        if self.entity_note:
            detail["note"] = self.entity_note
        self.mark(
            STAGE_ENTITY_EXTRACTED,
            status="ok" if rows else "no_entity",
            detail=detail,
            duration_ms=latency_ms,
        )

    def set_source(
        self,
        name: str,
        *,
        searched: bool,
        latency_ms: int = 0,
        returned: int = 0,
        selected: int = 0,
        status: str = "ok",
    ) -> None:
        label = SOURCE_LABELS.get(name.lower(), name)
        row = {
            "name": label,
            "key": name,
            "searched": bool(searched),
            "latency_ms": int(latency_ms or 0),
            "returned": int(returned or 0),
            "selected": int(selected or 0),
            "status": status,
        }
        # Upsert by key
        for i, existing in enumerate(self.sources):
            if existing.get("key") == name or existing.get("name") == label:
                self.sources[i] = row
                self._persist()
                return
        self.sources.append(row)
        self._persist()

    def set_evidence(
        self,
        *,
        retrieved: int,
        used: int,
        top_ids: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        self.evidence_count = int(retrieved or 0)
        self.evidence_used = int(used or 0)
        self.top_evidence_ids = [str(x) for x in (top_ids or [])[:12]]
        self.evidence_sources = list(sources or [])
        self.mark(
            STAGE_EVIDENCE_FUSED,
            detail={
                "retrieved": self.evidence_count,
                "used": self.evidence_used,
                "top_evidence_ids": self.top_evidence_ids,
                "sources": self.evidence_sources,
            },
            duration_ms=latency_ms,
        )

    def set_prompt(
        self,
        *,
        prompt_chars: int = 0,
        estimated_tokens: int = 0,
        evidence_count: int = 0,
        system_prompt_version: Optional[str] = None,
        playbook: Optional[str] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        # Never store raw prompt / user PII — sizes only.
        self.prompt = {
            "prompt_chars": int(prompt_chars or 0),
            "estimated_tokens": int(estimated_tokens or 0),
            "evidence_count": int(evidence_count or 0),
            "system_prompt_version": system_prompt_version,
            "playbook": playbook,
        }
        self.mark(STAGE_PROMPT_BUILT, detail=dict(self.prompt), duration_ms=latency_ms)

    def set_llm(
        self,
        *,
        model: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        finish_reason: Optional[str] = None,
        error: Optional[str] = None,
        timed_out: bool = False,
        used: bool = True,
    ) -> None:
        self.llm = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "finish_reason": finish_reason,
            "error": error,
            "timed_out": timed_out,
            "used": used,
        }
        status = "ok"
        if timed_out:
            status = "timeout"
        elif error:
            status = "error"
        elif not used:
            status = "skipped"
        self.mark(STAGE_LLM_COMPLETED, status=status, detail=dict(self.llm), duration_ms=latency_ms)

    def set_fallback(self, reason: str, *, detail: Optional[Dict[str, Any]] = None) -> None:
        self.fallback_used = True
        self.fallback_reason = reason
        self.status = "fallback"
        payload = {"reason": reason}
        if detail:
            payload.update(detail)
        self.mark(STAGE_FALLBACK_USED, status="fallback", detail=payload)

    def set_error(
        self,
        *,
        stage: str,
        message: str,
        root_cause: Optional[str] = None,
        stack: Optional[str] = None,
    ) -> None:
        self.error = {
            "stage": stage,
            "message": (message or "")[:500],
            "root_cause": (root_cause or message or "")[:500],
            "stack": (stack or "")[:4000],
            "elapsed_ms": self.elapsed_ms(),
        }
        self.status = "error"
        self.mark(
            STAGE_ERROR,
            status="error",
            detail=self.error,
        )

    def complete(self, *, status: str = "success") -> None:
        if self.status == "in_progress":
            self.status = status
        self.mark(STAGE_RESPONSE_SENT, status=self.status)
        self.latency_breakdown["total_ms"] = self.elapsed_ms()
        self._persist(final=True)
        self.print_developer_console()

    def to_debug_payload(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "ask_trace_id": self.ask_trace_id,
            "question_excerpt": self.question[:160],
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "intent_why_unknown": self.intent_why_unknown,
            "entities": self.entities,
            "entity_note": self.entity_note,
            "sources": self.sources,
            "evidence_count": self.evidence_count,
            "evidence_used": self.evidence_used,
            "top_evidence_ids": self.top_evidence_ids,
            "evidence_sources": self.evidence_sources,
            "prompt": self.prompt,
            "prompt_tokens": (self.prompt or {}).get("estimated_tokens")
            or (self.llm or {}).get("prompt_tokens"),
            "completion_tokens": (self.llm or {}).get("completion_tokens"),
            "llm_latency_ms": (self.llm or {}).get("latency_ms"),
            "llm": self.llm,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "total_latency_ms": self.elapsed_ms(),
            "latency_breakdown": dict(self.latency_breakdown),
            "events": list(self.events),
            "status": self.status,
            "error": self.error,
            "diagnostics_visibility": "internal",
        }

    def print_developer_console(self) -> None:
        ents = ", ".join(
            str(e.get("name") or e.get("ticker") or e)
            for e in self.entities
        ) or (self.entity_note or "—")
        srcs = ", ".join(
            s.get("name") for s in self.sources if s.get("searched") or s.get("returned")
        ) or ", ".join(self.evidence_sources) or "—"
        llm_model = (self.llm or {}).get("model") or ("skipped" if (self.llm or {}).get("used") is False else "—")
        lines = [
            "",
            "=================================================",
            f"Request ID: {self.request_id}",
            f"Question: {self.question[:160] or '—'}",
            f"Intent: {self.intent or '—'}",
            f"Entities: {ents}",
            f"Sources: {srcs}",
            f"Evidence: {self.evidence_count} (used {self.evidence_used})",
            f"Prompt Tokens: {(self.prompt or {}).get('estimated_tokens') or (self.llm or {}).get('prompt_tokens') or '—'}",
            f"LLM: {llm_model}",
            f"Latency: {self.elapsed_ms() / 1000:.2f}s",
            f"Fallback: {'YES' if self.fallback_used else 'NO'}"
            + (f" ({self.fallback_reason})" if self.fallback_reason else ""),
            f"Status: {str(self.status or '—').upper()}",
            "=================================================",
            "",
        ]
        text = "\n".join(lines)
        _LOG.info("ask_pipeline_console\n%s", text)
        # Also emit to stdout for Render log drains / founder debugging.
        try:
            print(text, flush=True)
        except Exception:
            pass

    def _persist(self, *, final: bool = False) -> None:
        try:
            from app.ui.ask_observability_store import record_pipeline_trace

            record_pipeline_trace(self.to_debug_payload(), final=final)
        except Exception:
            pass


def get_or_create_trace(
    request_id: Optional[str] = None,
    *,
    question: str = "",
) -> AskPipelineTrace:
    """Return an in-flight trace if present, else create one."""
    rid = normalize_request_id(request_id)
    try:
        from app.ui.ask_observability_store import get_pipeline_trace

        existing = get_pipeline_trace(rid)
        if existing and existing.get("_trace_obj"):
            return existing["_trace_obj"]  # type: ignore[return-value]
    except Exception:
        pass
    return AskPipelineTrace(request_id=rid, question=question)


def sources_from_degradation(degradation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map Ask degradation ledger → per-source observability rows (no retrieval change).

    Always emits the Phase-1 canonical source list so no source is a silent black box.
    """
    if not isinstance(degradation, dict):
        degradation = {}
    rows: List[Dict[str, Any]] = []
    # Canonical Phase-1 sources (labels fixed for Mission Control / debug endpoint).
    mapping = (
        ("krig", "Knowledge Factory"),
        ("kip", "KIP"),
        ("finance_academy", "Academy"),
        ("multi_source", "Private Markets"),
        ("valuation", "Valuation"),
        ("market_indices", "Nifty Scores"),
        ("finance_retrieval", "Live Filings"),
        ("live_evidence", "Live Market"),
    )
    # Alias keys that should fold into the same label when present.
    aliases = {
        "complete_ask": "krig",
        "dvc": "valuation",
        "nifty": "market_indices",
        "leo": "live_evidence",
        "fre": "finance_retrieval",
        "academy": "finance_academy",
        "academy_books": "finance_academy",
    }
    effective: Dict[str, Any] = dict(degradation)
    for alias, primary in aliases.items():
        if alias in degradation and primary not in effective:
            effective[primary] = degradation.get(alias)
    seen: set[str] = set()
    for key, label in mapping:
        status = str(effective.get(key) or "not_queried")
        searched = status not in {
            "",
            "unavailable",
            "skipped_slim",
            "skipped",
            "not_queried",
            "unknown",
        }
        if label in seen:
            continue
        seen.add(label)
        rows.append(
            {
                "name": label,
                "key": key,
                "searched": searched,
                "latency_ms": 0,
                "returned": 0,
                "selected": 0,
                "status": status,
            }
        )
    return rows
