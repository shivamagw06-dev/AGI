"""Ask orchestration observability — retrieval funnel, latency, entity confidence.

Internal telemetry for founder debugging. Not a user-facing surface.
Progressive stage checkpoints survive hangs / timeouts so baselines always
record last_completed_stage.
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

_LOG = logging.getLogger("agi.ask.orchestration")

# Soft thresholds (ms) — warnings only; never change business logic / timeouts.
STAGE_THRESHOLDS_MS: Dict[str, int] = {
    "entity_resolution": 250,
    "ikl": 500,
    "retrieval": 2000,
    "ranking": 1000,
    "reasoning": 20_000,
    "response_assembly": 2000,
    "executive_assembly": 2000,
    "serialization": 2000,
    "http": 120_000,
}

REASONING_WARN_MS = 30_000


def new_ask_trace_id() -> str:
    """Stable per-request id (Phase-1): ask_YYYYMMDD_<hex>.

    Legacy ASK-YYYYMMDD-HEX ids are still accepted via normalize_request_id.
    """
    try:
        from app.ui.ask_pipeline_trace import new_request_id

        return new_request_id()
    except Exception:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"ask_{day}_{secrets.token_hex(4)}"


class StageTimer:
    """Accumulate wall-clock ms per named stage + progressive checkpoints."""

    def __init__(
        self,
        *,
        ask_trace_id: Optional[str] = None,
        on_checkpoint: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self._t0 = time.perf_counter()
        self._marks: Dict[str, float] = {"start": self._t0}
        self.stages_ms: Dict[str, int] = {}
        self.warnings: List[Dict[str, Any]] = []
        self.last_completed_stage: Optional[str] = "http_ingress"
        self.ask_trace_id = ask_trace_id or new_ask_trace_id()
        self._on_checkpoint = on_checkpoint
        self._context: Dict[str, Any] = {}
        # Record ingress immediately
        self.stages_ms["http_ingress"] = 0
        self._emit_checkpoint(completed=False, stage="http_ingress")

    def set_context(self, **kwargs: Any) -> None:
        """Attach entity / funnel / IKL snapshots for partial flush."""
        for k, v in kwargs.items():
            if v is not None:
                self._context[k] = v

    def mark(self, name: str) -> int:
        now = time.perf_counter()
        prev = self._marks.get("_last", self._t0)
        elapsed = max(0, int((now - prev) * 1000))
        self.stages_ms[name] = elapsed
        self._marks[name] = now
        self._marks["_last"] = now
        self.last_completed_stage = name
        self._check_threshold(name, elapsed)
        if name == "reasoning" and elapsed >= REASONING_WARN_MS:
            self._reasoning_slow_warning(elapsed)
        self._emit_checkpoint(completed=False, stage=name)
        _LOG.info(
            "ask_stage trace=%s stage=%s ms=%s total_ms=%s",
            self.ask_trace_id,
            name,
            elapsed,
            self.total_ms(),
        )
        return elapsed

    def _check_threshold(self, name: str, elapsed_ms: int) -> None:
        limit = STAGE_THRESHOLDS_MS.get(name)
        if limit is None or elapsed_ms <= limit:
            return
        warn = {
            "stage": name,
            "elapsed_ms": elapsed_ms,
            "threshold_ms": limit,
            "ask_trace_id": self.ask_trace_id,
            "kind": "stage_threshold_exceeded",
        }
        self.warnings.append(warn)
        _LOG.warning(
            "ask_stage_threshold trace=%s stage=%s elapsed_ms=%s threshold_ms=%s",
            self.ask_trace_id,
            name,
            elapsed_ms,
            limit,
        )

    def _reasoning_slow_warning(self, elapsed_ms: int) -> None:
        ctx = self._context
        funnel = ctx.get("funnel") if isinstance(ctx.get("funnel"), dict) else {}
        warn = {
            "kind": "reasoning_slow",
            "ask_trace_id": self.ask_trace_id,
            "elapsed_ms": elapsed_ms,
            "documents_passed": funnel.get("passed") or ctx.get("documents_passed"),
            "token_estimate": ctx.get("token_estimate"),
            "reasoning_model": ctx.get("reasoning_model"),
            "retrieval_latency_ms": self.stages_ms.get("retrieval"),
            "ikl_latency_ms": self.stages_ms.get("ikl"),
        }
        self.warnings.append(warn)
        _LOG.warning(
            "ask_reasoning_slow trace=%s reasoning_ms=%s passed=%s retrieval_ms=%s ikl_ms=%s model=%s",
            self.ask_trace_id,
            elapsed_ms,
            warn.get("documents_passed"),
            warn.get("retrieval_latency_ms"),
            warn.get("ikl_latency_ms"),
            warn.get("reasoning_model"),
        )

    def _emit_checkpoint(self, *, completed: bool, stage: str) -> None:
        row = self.partial_snapshot(completed=completed, timeout=False)
        row["checkpoint_stage"] = stage
        if self._on_checkpoint:
            try:
                self._on_checkpoint(row)
            except Exception:
                pass
        else:
            try:
                from app.ui.ask_observability_store import record_partial_trace

                record_partial_trace(row)
            except Exception:
                pass

    def total_ms(self) -> int:
        return max(0, int((time.perf_counter() - self._t0) * 1000))

    def as_dict(self) -> Dict[str, int]:
        out = dict(self.stages_ms)
        out["total"] = self.total_ms()
        return out

    def as_latency_block(self) -> Dict[str, Any]:
        """Spec-shaped latency keys for diagnostics / Mission Control."""
        s = self.stages_ms
        return {
            "entity_ms": int(s.get("entity_resolution") or 0),
            "ikl_ms": int(s.get("ikl") or 0),
            "retrieval_ms": int(s.get("retrieval") or 0),
            "ranking_ms": int(s.get("ranking") or 0),
            "reasoning_ms": int(s.get("reasoning") or 0),
            "assembly_ms": int(
                s.get("response_assembly")
                or s.get("executive_assembly")
                or 0
            ),
            "serialization_ms": int(s.get("serialization") or 0),
            "http_ms": int(s.get("http") or 0),
            "http_ingress_ms": int(s.get("http_ingress") or 0),
            "total_ms": self.total_ms(),
            "last_completed_stage": self.last_completed_stage,
            "stages": dict(s),
            "warnings": list(self.warnings),
        }

    def partial_snapshot(
        self,
        *,
        completed: bool,
        timeout: bool = False,
        fallback_used: bool = False,
        engine_reached: Optional[bool] = None,
    ) -> Dict[str, Any]:
        ctx = dict(self._context)
        latency = self.as_latency_block()
        funnel = ctx.get("funnel") if isinstance(ctx.get("funnel"), dict) else {}
        entity = ctx.get("entity") if isinstance(ctx.get("entity"), dict) else {}
        return {
            "version": "ask-orchestration-trace-2",
            "ask_trace_id": self.ask_trace_id,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "completed": completed,
            "timeout": timeout,
            "last_completed_stage": self.last_completed_stage,
            "elapsed_ms": self.total_ms(),
            "engine_reached": True if engine_reached is None else engine_reached,
            "fallback_used": fallback_used,
            "fallback": fallback_used,
            "entity": entity,
            "funnel": funnel,
            "evidence": funnel,
            "latency": latency,
            "latency_ms": self.as_dict(),
            "ikl": ctx.get("ikl") or {},
            "stage_warnings": list(self.warnings),
            "diagnostics_visibility": "internal",
            "partial": not completed,
        }


def _len_list(obj: Any) -> int:
    return len(obj) if isinstance(obj, list) else 0


def _pack_hit_count(pack: Any, *keys: str) -> int:
    if not isinstance(pack, dict):
        return 0
    n = 0
    for k in keys:
        v = pack.get(k)
        if isinstance(v, list):
            n += len(v)
        elif isinstance(v, dict):
            for nk in ("hits", "items", "evidence_objects", "documents", "articles"):
                if isinstance(v.get(nk), list):
                    n += len(v[nk])
    return n


def count_retrieved(
    *,
    kf_hits: Any = None,
    finance_retrieval: Any = None,
    live_evidence: Any = None,
    multi_source: Any = None,
    knowledge_corpus: Any = None,
    open_intelligence: Any = None,
    hits: Any = None,
    articles: Any = None,
    supporting: Any = None,
) -> int:
    n = 0
    n += _len_list(kf_hits)
    n += _pack_hit_count(finance_retrieval, "hits", "evidence")
    n += _pack_hit_count(live_evidence, "evidence_objects", "items", "hits")
    if isinstance(multi_source, dict):
        try:
            n += int(multi_source.get("evidence_count") or 0)
        except (TypeError, ValueError):
            n += _pack_hit_count(multi_source, "hits", "items", "evidence")
    n += _pack_hit_count(knowledge_corpus, "hits", "items")
    n += _pack_hit_count(open_intelligence, "hits", "items")
    n += _len_list(hits)
    n += _len_list(articles)
    n += _len_list(supporting)
    return n


def count_ranked(*, evidence_used: Any = None, supporting_research: Any = None, support_ev: Any = None) -> int:
    n = _len_list(evidence_used) + _len_list(supporting_research)
    if n == 0:
        n = _len_list(support_ev)
    return n


def count_passed_to_ice(ask_pipeline_runtime: Any, ice_view: Any) -> int:
    n = 0
    if isinstance(ask_pipeline_runtime, dict):
        ev = ask_pipeline_runtime.get("evidence") or {}
        if isinstance(ev, dict):
            n = max(n, _len_list(ev.get("items")))
        ia = ask_pipeline_runtime.get("institutional_answer") or {}
        if isinstance(ia, dict):
            ia_ev = ia.get("evidence") or {}
            if isinstance(ia_ev, dict):
                n = max(n, _len_list(ia_ev.get("items")))
    if isinstance(ice_view, dict):
        secs = ice_view.get("sections") or {}
        ev_sec = secs.get("evidence") if isinstance(secs, dict) else None
        if isinstance(ev_sec, dict):
            n = max(n, _len_list(ev_sec.get("bullets")))
        cites = ice_view.get("why") or []
        if isinstance(cites, list):
            n = max(n, min(len(cites), 14))
    return n


def count_referenced(
    *,
    ice_view: Any = None,
    evidence_used: Any = None,
    why: Any = None,
    executive: str = "",
) -> int:
    referenced_ids: set[str] = set()
    titles: List[str] = []

    if isinstance(ice_view, dict):
        secs = ice_view.get("sections") or {}
        for name in ("sources", "evidence", "analysis"):
            sec = secs.get(name) if isinstance(secs, dict) else None
            for b in (sec or {}).get("bullets") or []:
                s = str(b)
                if "evidence id" in s.lower() or "source=" in s.lower() or s.strip().startswith("-"):
                    referenced_ids.add(s[:120])
        for item in (ice_view.get("citations") or []) if isinstance(ice_view.get("citations"), list) else []:
            if isinstance(item, dict) and item.get("evidence_id"):
                referenced_ids.add(str(item["evidence_id"]))

    for item in evidence_used or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("source") or "").strip()
        if not title:
            continue
        titles.append(title)
        blob = f"{executive} {' '.join(str(x) for x in (why or []))}".lower()
        needle = title.lower()[:40]
        if needle and needle in blob:
            referenced_ids.add(title)

    for line in why or []:
        low = str(line).lower()
        if "supported by evidence" in low or "evidence:" in low or "source:" in low:
            referenced_ids.add(str(line)[:120])

    if referenced_ids:
        return len(referenced_ids)
    if titles and executive and len(executive) >= 40:
        return min(len(titles), 3)
    return 0


def entity_confidence_block(
    *,
    detected_ticker: Optional[str],
    ere_body: Any,
    ticker_source: Optional[str],
    question: str,
    alias_hit: Optional[str] = None,
) -> Dict[str, Any]:
    ere = ere_body if isinstance(ere_body, dict) else {}
    aliases: List[str] = []
    if detected_ticker:
        aliases.append(detected_ticker)
    if alias_hit and alias_hit not in aliases:
        aliases.append(alias_hit)
    canon = ere.get("entity") or ere.get("canonical_entity")
    if isinstance(canon, dict):
        name = canon.get("canonical_name") or canon.get("name")
        if name:
            aliases.append(str(name))
        for a in canon.get("aliases") or []:
            if str(a) not in aliases:
                aliases.append(str(a))
    elif isinstance(canon, str) and canon not in aliases:
        aliases.append(canon)
    if ere.get("entity") and isinstance(ere.get("entity"), str):
        if ere["entity"] not in aliases:
            aliases.append(str(ere["entity"]))

    conf = ere.get("confidence")
    try:
        conf_f = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf_f = None
    if conf_f is not None and conf_f > 1.0:
        conf_f = conf_f / 100.0

    if ticker_source in {"alias", "alias_override", "alias_final"} and detected_ticker:
        conf_f = max(conf_f or 0.0, 0.98)
    elif ticker_source == "ere" and detected_ticker:
        conf_f = conf_f if conf_f is not None else 0.9
    elif ticker_source == "user" and detected_ticker:
        conf_f = max(conf_f or 0.0, 0.95)
    elif detected_ticker:
        conf_f = conf_f if conf_f is not None else 0.55
    else:
        conf_f = conf_f if conf_f is not None else 0.0

    needs_clarification = bool(ere.get("needs_clarification") or ere.get("research_blocked"))
    low_confidence = bool(detected_ticker) and conf_f < 0.7

    name = None
    if isinstance(ere.get("entity"), str):
        name = ere.get("entity")
    elif isinstance(canon, dict):
        name = canon.get("canonical_name") or canon.get("name")
    if not name and detected_ticker:
        name = detected_ticker

    return {
        "name": name,
        "detected": detected_ticker,
        "entity_name": name,
        "entity_type": ere.get("entity_type"),
        "aliases_matched": aliases[:8],
        "confidence": round(conf_f, 3),
        "source": ticker_source,
        "resolution_source": ticker_source,
        "needs_clarification": needs_clarification or low_confidence,
        "low_confidence": low_confidence,
        "silently_bound": bool(
            low_confidence
            and ticker_source not in {"user", "alias", "alias_override", "alias_final", "ere"}
        ),
        "question_excerpt": (question or "")[:160],
    }


def executive_attribution(
    *,
    executive: str,
    evidence_used: Any = None,
    supporting_research: Any = None,
    ice_view: Any = None,
) -> List[Dict[str, Any]]:
    text = (executive or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in text.replace("·", ".").split(".") if len(p.strip()) >= 24]
    if not parts:
        parts = [text[:280]]

    corpus: List[Dict[str, str]] = []
    for item in list(evidence_used or []) + list(supporting_research or []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        source = str(item.get("source") or item.get("provider") or item.get("type") or "").strip()
        if title or source:
            corpus.append({"title": title or source, "source": source or "evidence"})

    if isinstance(ice_view, dict):
        for b in ((ice_view.get("sections") or {}).get("sources") or {}).get("bullets") or []:
            corpus.append({"title": str(b)[:120], "source": "ice_sources"})

    rows: List[Dict[str, Any]] = []
    for i, para in enumerate(parts[:6], 1):
        low = para.lower()
        match = None
        for c in corpus:
            needle = (c["title"] or "").lower()[:32]
            if needle and any(tok in low for tok in needle.split()[:3] if len(tok) > 3):
                match = c
                break
        rows.append(
            {
                "paragraph": i,
                "text_excerpt": para[:180],
                "evidence_title": (match or {}).get("title"),
                "evidence_source": (match or {}).get("source"),
                "grounded": bool(match),
            }
        )
    return rows


def build_funnel(
    *,
    retrieved: int,
    ranked: int,
    passed: int,
    referenced: int,
) -> Dict[str, Any]:
    ranked = min(ranked, retrieved) if retrieved else ranked
    passed = min(passed, ranked) if ranked else passed
    utilization = (referenced / passed) if passed else 0.0
    efficiency = (referenced / retrieved) if retrieved else 0.0
    precision = (referenced / ranked) if ranked else 0.0
    return {
        "retrieved": retrieved,
        "ranked": ranked,
        "passed": passed,
        "passed_to_ice": passed,
        "referenced": referenced,
        "utilization": round(min(utilization, 1.0), 3),
        "efficiency": round(min(efficiency, 1.0), 3),
        "precision": round(min(precision, 1.0), 3),
        "zero_stage": (
            "retrieved"
            if retrieved == 0
            else "ranked"
            if ranked == 0
            else "passed"
            if passed == 0
            else "referenced"
            if referenced == 0
            else None
        ),
    }


def format_execution_trace(orch: Dict[str, Any]) -> str:
    """Human-readable founder execution trace (internal)."""
    ent = orch.get("entity") or {}
    funnel = orch.get("funnel") or orch.get("evidence") or {}
    lat = orch.get("latency") or {}
    stages = lat.get("stages") if isinstance(lat.get("stages"), dict) else {}
    ikl_ms = lat.get("ikl_ms")
    if ikl_ms is None:
        ikl_ms = stages.get("ikl") or 0
    reasoning_ms = lat.get("reasoning_ms") or stages.get("reasoning") or 0
    assembly_ms = lat.get("assembly_ms") or stages.get("response_assembly") or 0
    total = lat.get("total_ms") if lat.get("total_ms") is not None else orch.get("elapsed_ms") or 0
    completed = orch.get("completed")
    if completed is None:
        completed = not bool(orch.get("timeout") or orch.get("partial") or orch.get("fallback_used"))
    name = ent.get("name") or ent.get("detected") or ent.get("entity_name") or "—"
    conf = ent.get("confidence")
    conf_s = f"{conf:.2f}" if isinstance(conf, (int, float)) else str(conf or "—")
    lines = [
        f"Ask Trace ID: {orch.get('ask_trace_id') or '—'}",
        f"Entity: {name} ({conf_s})",
        f"IKL: {float(ikl_ms) / 1000:.3f}s" if float(ikl_ms or 0) >= 1000 else f"IKL: {int(ikl_ms or 0)}ms",
        f"Retrieved: {funnel.get('retrieved', 0)}",
        f"Ranked: {funnel.get('ranked', 0)}",
        f"Passed: {funnel.get('passed', funnel.get('passed_to_ice', 0))}",
        f"Referenced: {funnel.get('referenced', 0)}",
        f"Reasoning: {float(reasoning_ms) / 1000:.1f}s",
        f"Assembly: {int(assembly_ms)}ms",
        f"Completed: {str(bool(completed)).lower()}",
        f"Last completed stage: {orch.get('last_completed_stage') or lat.get('last_completed_stage') or '—'}",
        f"Elapsed: {float(total) / 1000:.1f}s",
    ]
    if orch.get("timeout"):
        lines.append("Timeout: true")
    if orch.get("fallback_used") or orch.get("fallback"):
        lines.append("Fallback: true")
    return "\n".join(lines)


def format_trace_summary(orch: Dict[str, Any]) -> str:
    ent = orch.get("entity") or {}
    evidence = orch.get("evidence") or orch.get("funnel") or {}
    lat = orch.get("latency") or orch.get("latency_ms") or {}
    total = lat.get("total_ms") if lat.get("total_ms") is not None else lat.get("total") or 0
    return (
        f"Trace: {orch.get('ask_trace_id') or '—'} | "
        f"Entity: {ent.get('name') or ent.get('detected') or ent.get('entity_name') or '—'} "
        f"({ent.get('confidence', 0)}) | "
        f"IKL: {lat.get('ikl_ms', 0)}ms | "
        f"Retrieved: {evidence.get('retrieved', 0)} → Ranked: {evidence.get('ranked', 0)} → "
        f"Passed: {evidence.get('passed', evidence.get('passed_to_ice', 0))} → "
        f"Referenced: {evidence.get('referenced', 0)} | "
        f"Utilization: {evidence.get('utilization', 0)} | "
        f"Efficiency: {evidence.get('efficiency', 0)} | "
        f"Precision: {evidence.get('precision', 0)} | "
        f"Last stage: {orch.get('last_completed_stage') or lat.get('last_completed_stage') or '—'} | "
        f"Executive overwritten: {'Yes' if orch.get('executive_overwritten') else 'No'} | "
        f"Fallback: {'Yes' if orch.get('fallback') or orch.get('fallback_used') else 'No'} | "
        f"Timeout: {'Yes' if orch.get('timeout') else 'No'} | "
        f"Total: {float(total) / 1000:.1f}s"
    )


def finalize_orchestration(
    base: Dict[str, Any],
    *,
    timer: StageTimer,
    question: str,
    detected_ticker: Optional[str],
    ere_body: Any,
    alias_hit: Optional[str],
    kf_hits: Any = None,
    finance_retrieval: Any = None,
    live_evidence: Any = None,
    multi_source: Any = None,
    knowledge_corpus: Any = None,
    open_intelligence: Any = None,
    hits: Any = None,
    articles: Any = None,
    supporting: Any = None,
    evidence_used: Any = None,
    supporting_research: Any = None,
    support_ev: Any = None,
    ask_pipeline_runtime: Any = None,
    ice_view: Any = None,
    why: Any = None,
    executive: str = "",
    intent: Any = None,
    fallback: bool = False,
    timeout: bool = False,
    persist: bool = True,
) -> Dict[str, Any]:
    orch = dict(base or {})
    ticker_source = orch.get("ticker_source")
    ask_trace_id = orch.get("ask_trace_id") or timer.ask_trace_id or new_ask_trace_id()
    retrieved = count_retrieved(
        kf_hits=kf_hits,
        finance_retrieval=finance_retrieval,
        live_evidence=live_evidence,
        multi_source=multi_source,
        knowledge_corpus=knowledge_corpus,
        open_intelligence=open_intelligence,
        hits=hits,
        articles=articles,
        supporting=supporting,
    )
    ranked = count_ranked(
        evidence_used=evidence_used,
        supporting_research=supporting_research,
        support_ev=support_ev,
    )
    passed = count_passed_to_ice(ask_pipeline_runtime, ice_view)
    if passed == 0 and ranked:
        passed = min(ranked, 6)
    referenced = count_referenced(
        ice_view=ice_view,
        evidence_used=evidence_used,
        why=why,
        executive=executive,
    )
    funnel = build_funnel(
        retrieved=retrieved, ranked=ranked, passed=passed, referenced=referenced
    )
    entity = entity_confidence_block(
        detected_ticker=detected_ticker,
        ere_body=ere_body,
        ticker_source=ticker_source,
        question=question,
        alias_hit=alias_hit,
    )
    rejects = list(orch.get("ticker_rejects") or [])
    entity["rejected_candidates"] = [
        (r.get("raw") if isinstance(r, dict) else r) for r in rejects
    ][:12]
    attribution = executive_attribution(
        executive=executive,
        evidence_used=evidence_used,
        supporting_research=supporting_research,
        ice_view=ice_view,
    )
    grounded = (
        sum(1 for a in attribution if a.get("grounded")) / len(attribution) if attribution else None
    )
    ice_meta = bool(
        ((orch.get("ice_framework_meta_suppressed")) or False)
        or (
            isinstance(ice_view, dict)
            and (ice_view.get("institutional_communication") or {}).get("executive_was_framework_meta")
        )
    )
    executive_overwritten = bool(orch.get("executive_source") == "ice") and not ice_meta

    # Refresh timer context before final latency block (reasoning warnings use it)
    timer.set_context(
        entity=entity,
        funnel=funnel,
        documents_passed=passed,
        ikl=orch.get("ikl"),
        reasoning_model=(
            ((ask_pipeline_runtime or {}).get("communication") or {}).get("model")
            if isinstance(ask_pipeline_runtime, dict)
            else None
        )
        or orch.get("reasoning_model"),
        token_estimate=orch.get("token_estimate"),
    )

    latency = timer.as_latency_block()
    completed = not timeout and not fallback
    orch.update(
        {
            "version": "ask-orchestration-trace-2",
            "ask_trace_id": ask_trace_id,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "fallback": fallback,
            "fallback_used": fallback,
            "timeout": timeout,
            "completed": completed,
            "partial": bool(timeout or not completed),
            "last_completed_stage": timer.last_completed_stage,
            "elapsed_ms": timer.total_ms(),
            "engine_reached": not fallback,
            "intent": intent,
            "bound_ticker": detected_ticker,
            "entity": entity,
            "funnel": funnel,
            "evidence": {
                "retrieved": funnel["retrieved"],
                "ranked": funnel["ranked"],
                "passed": funnel["passed"],
                "referenced": funnel["referenced"],
                "utilization": funnel["utilization"],
                "efficiency": funnel["efficiency"],
                "precision": funnel["precision"],
                "zero_stage": funnel["zero_stage"],
            },
            "latency": latency,
            "latency_ms": timer.as_dict(),
            "stage_warnings": list(timer.warnings),
            "executive_attribution": attribution,
            "grounding": round(grounded, 3) if grounded is not None else None,
            "executive_overwritten": executive_overwritten,
            "executive_source": orch.get("executive_source"),
            "diagnostics_visibility": "internal",
            "trace_summary": "",
            "execution_trace": "",
        }
    )
    orch["trace_summary"] = format_trace_summary(orch)
    orch["execution_trace"] = format_execution_trace(orch)
    _LOG.info("ask_execution_trace\n%s", orch["execution_trace"])
    if persist:
        try:
            from app.ui.ask_observability_store import record_trace

            record_trace(orch)
        except Exception:
            pass
    return orch


def gateway_timeout_orchestration(
    *,
    ask_trace_id: str,
    elapsed_ms: int,
    timeout_ms: int,
    question: str = "",
    detail: str = "",
) -> Dict[str, Any]:
    """Partial orchestration bag when Node times out waiting on the engine."""
    orch = {
        "version": "ask-orchestration-trace-2",
        "ask_trace_id": ask_trace_id,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "completed": False,
        "timeout": True,
        "partial": True,
        "last_completed_stage": "http_ingress",
        "elapsed_ms": elapsed_ms,
        "engine_reached": False,
        "fallback": True,
        "fallback_used": True,
        "reason": detail or f"engine_timeout_{timeout_ms}ms",
        "timeout_ms": timeout_ms,
        "entity": {"name": None, "confidence": 0.0, "question_excerpt": (question or "")[:160]},
        "funnel": {"retrieved": 0, "ranked": 0, "passed": 0, "referenced": 0},
        "evidence": {"retrieved": 0, "ranked": 0, "passed": 0, "referenced": 0},
        "latency": {
            "http_ms": elapsed_ms,
            "total_ms": elapsed_ms,
            "http_ingress_ms": 0,
            "entity_ms": 0,
            "ikl_ms": 0,
            "retrieval_ms": 0,
            "ranking_ms": 0,
            "reasoning_ms": 0,
            "assembly_ms": 0,
            "serialization_ms": 0,
            "last_completed_stage": "http_ingress",
            "stages": {"http_ingress": 0, "http": elapsed_ms},
            "warnings": [
                {
                    "kind": "gateway_engine_timeout",
                    "elapsed_ms": elapsed_ms,
                    "threshold_ms": timeout_ms,
                    "ask_trace_id": ask_trace_id,
                }
            ],
        },
        "diagnostics_visibility": "internal",
    }
    orch["trace_summary"] = format_trace_summary(orch)
    orch["execution_trace"] = format_execution_trace(orch)
    return orch
