"""CAE retrieval orchestration — soft-call existing engines only."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from app.cae.config import ENGINE_TIMEOUT_MS
from app.cae.models import EngineContribution, RankedItem, new_id


def _soft(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _estimate_tokens(obj: Any) -> int:
    try:
        text = str(obj)
    except Exception:
        text = ""
    return max(1, len(text) // 4)


def _item(
    *,
    engine: str,
    kind: str,
    title: str,
    content: Any,
    confidence: float = 0.5,
    why: str = "",
    latency_ms: float = 0.0,
    dedupe_key: str = "",
    freshness: float = 0.6,
    evidence_quality: float = 0.5,
    event_severity: float = 0.0,
    forecast_accuracy: float = 0.0,
    source_trust: float = 0.6,
    knowledge_quality: float = 0.5,
) -> RankedItem:
    return RankedItem(
        item_id=new_id("itm"),
        engine=engine,
        kind=kind,
        title=title[:160],
        content=content,
        confidence=float(confidence or 0),
        freshness=freshness,
        evidence_quality=evidence_quality,
        event_severity=event_severity,
        forecast_accuracy=forecast_accuracy,
        source_trust=source_trust,
        knowledge_quality=knowledge_quality,
        why_included=why or f"Retrieved from {engine}",
        token_estimate=_estimate_tokens(content),
        retrieval_latency_ms=latency_ms,
        dedupe_key=dedupe_key or f"{engine}:{kind}:{title[:80]}".lower(),
    )


class CaeRetriever:
    def __init__(
        self,
        *,
        kf: Any | None = None,
        kc: Any | None = None,
        aoi: Any | None = None,
        eve: Any | None = None,
        iie: Any | None = None,
        fle: Any | None = None,
        mee: Any | None = None,
        fre: Any | None = None,
        parallel: bool = True,
    ) -> None:
        self.kf = kf
        self.kc = kc
        self.aoi = aoi
        self.eve = eve
        self.iie = iie
        self.fle = fle
        self.mee = mee
        self.fre = fre
        self.parallel = parallel

    def retrieve(self, query: str, engines: list[str], *, limit: int = 8) -> tuple[list[RankedItem], list[EngineContribution]]:
        jobs: dict[str, Callable[[], tuple[list[RankedItem], EngineContribution]]] = {}
        mapping = {
            "kf": lambda: self._from_kf(query, limit),
            "kc": lambda: self._from_kc(query, limit),
            "aoi": lambda: self._from_aoi(query, limit),
            "eve": lambda: self._from_eve(query, limit),
            "iie": lambda: self._from_iie(query, limit),
            "fle": lambda: self._from_fle(query, limit),
            "mee": lambda: self._from_mee(query, limit),
            "fre": lambda: self._from_fre(query, limit),
        }
        for eng in engines:
            if eng in mapping:
                jobs[eng] = mapping[eng]

        items: list[RankedItem] = []
        contribs: list[EngineContribution] = []

        if self.parallel and len(jobs) > 1:
            with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
                futs = {pool.submit(fn): name for name, fn in jobs.items()}
                for fut in as_completed(futs, timeout=max(1.0, ENGINE_TIMEOUT_MS / 1000.0 * 2)):
                    name = futs[fut]
                    try:
                        got_items, contrib = fut.result(timeout=ENGINE_TIMEOUT_MS / 1000.0)
                        items.extend(got_items)
                        contribs.append(contrib)
                    except Exception as exc:
                        contribs.append(
                            EngineContribution(engine=name, requested=True, succeeded=False, error=str(exc)[:160])
                        )
        else:
            for name, fn in jobs.items():
                try:
                    got_items, contrib = fn()
                    items.extend(got_items)
                    contribs.append(contrib)
                except Exception as exc:
                    contribs.append(
                        EngineContribution(engine=name, requested=True, succeeded=False, error=str(exc)[:160])
                    )
        # Mark engines requested but missing bindings
        for eng in engines:
            if eng not in {c.engine for c in contribs}:
                contribs.append(EngineContribution(engine=eng, requested=True, succeeded=False, error="not_bound"))
        return items, contribs

    def _from_kf(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.kf:
            return [], EngineContribution(engine="kf", requested=True, succeeded=False, error="unbound")
        res = _soft(self.kf.search, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        hits = res.get("hits") if isinstance(res, dict) else []
        items = [
            _item(
                engine="kf",
                kind="knowledge",
                title=str(h.get("label") or h.get("key") or "knowledge"),
                content=h,
                confidence=float(h.get("score") or 0.55),
                knowledge_quality=float(h.get("score") or 0.55),
                source_trust=0.7,
                why="Canonical Knowledge Foundation object",
                latency_ms=ms,
                dedupe_key=f"kf:{h.get('kind')}:{h.get('key') or h.get('id')}",
            )
            for h in (hits or [])
            if isinstance(h, dict)
        ]
        return items, EngineContribution(engine="kf", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)

    def _from_kc(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.kc:
            return [], EngineContribution(engine="kc", requested=True, succeeded=False, error="unbound")
        res = _soft(self.kc.consult, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        hits = res.get("hits") if isinstance(res, dict) else []
        items = [
            _item(
                engine="kc",
                kind="knowledge",
                title=str(h.get("label") or h.get("id") or "corpus"),
                content=h,
                confidence=float(h.get("score") or 0.5),
                knowledge_quality=0.65,
                why="Knowledge Corpus consult hit",
                latency_ms=ms,
                dedupe_key=f"kc:{h.get('kind')}:{h.get('id') or h.get('key')}",
            )
            for h in (hits or [])
            if isinstance(h, dict)
        ]
        return items, EngineContribution(engine="kc", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)

    def _from_aoi(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.aoi:
            return [], EngineContribution(engine="aoi", requested=True, succeeded=False, error="unbound")
        res = _soft(self.aoi.consult, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        items: list[RankedItem] = []
        if isinstance(res, dict):
            hits = res.get("hits") or []
            for h in hits:
                if isinstance(h, dict):
                    items.append(
                        _item(
                            engine="aoi",
                            kind="open_intelligence",
                            title=str(h.get("label") or "aoi"),
                            content=h,
                            confidence=float(h.get("score") or 0.45),
                            freshness=0.85,
                            source_trust=0.55,
                            why="Latest public open intelligence",
                            latency_ms=ms,
                            dedupe_key=f"aoi:{h.get('id') or h.get('label')}",
                        )
                    )
            if res.get("company"):
                items.append(
                    _item(
                        engine="aoi",
                        kind="open_intelligence",
                        title="AOI company pack",
                        content=res.get("company"),
                        confidence=0.55,
                        freshness=0.8,
                        why="AOI company registry/pack",
                        latency_ms=ms,
                        dedupe_key="aoi:company_pack",
                    )
                )
        return items, EngineContribution(engine="aoi", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)

    def _from_eve(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.eve:
            return [], EngineContribution(engine="eve", requested=True, succeeded=False, error="unbound")
        res = _soft(self.eve.consult, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        items: list[RankedItem] = []
        if isinstance(res, dict):
            for h in res.get("hits") or []:
                if not isinstance(h, dict):
                    continue
                items.append(
                    _item(
                        engine="eve",
                        kind="evidence",
                        title=str(h.get("label") or "evidence"),
                        content=h,
                        confidence=float(h.get("confidence") or h.get("score") or 0.5),
                        evidence_quality=float(h.get("confidence") or 0.5),
                        source_trust=0.85,
                        why="Verified evidence (EVE)",
                        latency_ms=ms,
                        dedupe_key=f"eve:{h.get('id') or h.get('label')}",
                    )
                )
            for c in res.get("conflicts") or []:
                if isinstance(c, dict):
                    items.append(
                        _item(
                            engine="eve",
                            kind="conflict",
                            title=str(c.get("label") or "conflict"),
                            content=c,
                            confidence=0.5,
                            evidence_quality=0.7,
                            why="Open evidence conflict — preserve uncertainty",
                            latency_ms=ms,
                            dedupe_key=f"eve:conflict:{c.get('id')}",
                        )
                    )
            if res.get("company"):
                items.append(
                    _item(
                        engine="eve",
                        kind="evidence",
                        title="EVE company pack",
                        content=res.get("company"),
                        confidence=0.65,
                        evidence_quality=0.75,
                        why="Company evidence pack",
                        latency_ms=ms,
                        dedupe_key="eve:company_pack",
                    )
                )
        return items, EngineContribution(engine="eve", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)

    def _from_iie(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.iie:
            return [], EngineContribution(engine="iie", requested=True, succeeded=False, error="unbound")
        res = _soft(self.iie.consult, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        items: list[RankedItem] = []
        if isinstance(res, dict):
            for h in res.get("hits") or []:
                if isinstance(h, dict):
                    items.append(
                        _item(
                            engine="iie",
                            kind="investment",
                            title=str(h.get("label") or "iie"),
                            content=h,
                            confidence=float(h.get("confidence") or h.get("score") or 0.55),
                            knowledge_quality=0.7,
                            why="Investment intelligence object",
                            latency_ms=ms,
                            dedupe_key=f"iie:{h.get('kind')}:{h.get('id')}",
                        )
                    )
            company = res.get("company") or {}
            if isinstance(company, dict) and company:
                thesis = company.get("thesis") or {}
                if thesis:
                    items.append(
                        _item(
                            engine="iie",
                            kind="investment",
                            title="Investment thesis",
                            content=thesis,
                            confidence=float(thesis.get("confidence") or 0.55),
                            why="IIE investment thesis",
                            latency_ms=ms,
                            dedupe_key=f"iie:thesis:{company.get('company_id')}",
                        )
                    )
                for r in (company.get("risks") or [])[:5]:
                    if isinstance(r, dict):
                        items.append(
                            _item(
                                engine="iie",
                                kind="risk",
                                title=str(r.get("title") or "risk"),
                                content=r,
                                confidence=float(r.get("confidence") or 0.5),
                                why="IIE risk object",
                                latency_ms=ms,
                                dedupe_key=f"iie:risk:{r.get('risk_id')}",
                            )
                        )
                for c in (company.get("catalysts") or [])[:5]:
                    if isinstance(c, dict):
                        items.append(
                            _item(
                                engine="iie",
                                kind="catalyst",
                                title=str(c.get("title") or "catalyst"),
                                content=c,
                                confidence=float(c.get("confidence") or 0.5),
                                freshness=0.7,
                                why="IIE catalyst",
                                latency_ms=ms,
                                dedupe_key=f"iie:cat:{c.get('catalyst_id')}",
                            )
                        )
        return items, EngineContribution(engine="iie", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)

    def _from_fle(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.fle:
            return [], EngineContribution(engine="fle", requested=True, succeeded=False, error="unbound")
        res = _soft(self.fle.consult, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        items: list[RankedItem] = []
        if isinstance(res, dict):
            for h in res.get("hits") or []:
                if isinstance(h, dict):
                    items.append(
                        _item(
                            engine="fle",
                            kind="forecast",
                            title=str(h.get("label") or "forecast"),
                            content=h,
                            confidence=float(h.get("score") or 0.5),
                            forecast_accuracy=0.5,
                            why="Forecast registry hit",
                            latency_ms=ms,
                            dedupe_key=f"fle:{h.get('kind')}:{h.get('id')}",
                        )
                    )
            for f in (res.get("current_predictions") or [])[:6]:
                if isinstance(f, dict):
                    items.append(
                        _item(
                            engine="fle",
                            kind="forecast",
                            title=f"{f.get('metric')}: {f.get('predicted_value')}",
                            content=f,
                            confidence=float(f.get("confidence") or 0.5),
                            freshness=0.75,
                            why="Pending forecast",
                            latency_ms=ms,
                            dedupe_key=f"fle:fc:{f.get('forecast_id')}",
                        )
                    )
            for l in (res.get("learnings") or [])[:4]:
                if isinstance(l, dict):
                    items.append(
                        _item(
                            engine="fle",
                            kind="forecast",
                            title="Learning: " + "; ".join((l.get("lessons_learned") or [])[:1]),
                            content=l,
                            confidence=0.55,
                            forecast_accuracy=0.6,
                            why="Forecast learning object",
                            latency_ms=ms,
                            dedupe_key=f"fle:learn:{l.get('learning_id')}",
                        )
                    )
            cal = res.get("calibration") or {}
            if cal:
                items.append(
                    _item(
                        engine="fle",
                        kind="forecast",
                        title="Calibration snapshot",
                        content=cal,
                        confidence=0.6,
                        why="Confidence calibration context",
                        latency_ms=ms,
                        dedupe_key="fle:calibration",
                    )
                )
        return items, EngineContribution(engine="fle", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)

    def _from_mee(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.mee:
            return [], EngineContribution(engine="mee", requested=True, succeeded=False, error="unbound")
        res = _soft(self.mee.consult, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        items: list[RankedItem] = []
        sev_map = {"critical": 1.0, "high": 0.8, "medium": 0.55, "low": 0.3, "informational": 0.15}
        if isinstance(res, dict):
            for e in (res.get("recent_events") or [])[:limit]:
                if not isinstance(e, dict):
                    continue
                items.append(
                    _item(
                        engine="mee",
                        kind="event",
                        title=str(e.get("title") or e.get("event_type") or "event"),
                        content=e,
                        confidence=float(e.get("confidence") or 0.55),
                        freshness=0.9,
                        event_severity=sev_map.get(str(e.get("severity") or "medium"), 0.55),
                        why="Recent canonical market event",
                        latency_ms=ms,
                        dedupe_key=f"mee:{e.get('event_id')}",
                    )
                )
            for s in (res.get("historical_similar_events") or [])[:4]:
                if isinstance(s, dict):
                    items.append(
                        _item(
                            engine="mee",
                            kind="event",
                            title="Similar: " + str(s.get("title") or s.get("event_type")),
                            content=s,
                            confidence=float(s.get("score") or 0.5),
                            freshness=0.4,
                            why="Historical similar event analogue",
                            latency_ms=ms,
                            dedupe_key=f"mee:sim:{s.get('event_id')}",
                        )
                    )
        return items, EngineContribution(engine="mee", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)

    def _from_fre(self, query: str, limit: int) -> tuple[list[RankedItem], EngineContribution]:
        t0 = time.perf_counter()
        if not self.fre:
            return [], EngineContribution(engine="fre", requested=True, succeeded=False, error="unbound")
        res = _soft(self.fre.consult, query, limit=limit) or {}
        ms = (time.perf_counter() - t0) * 1000
        items: list[RankedItem] = []
        if isinstance(res, dict):
            for h in res.get("hits") or []:
                if not isinstance(h, dict):
                    continue
                items.append(
                    _item(
                        engine="fre",
                        kind="evidence",
                        title=str(h.get("label") or h.get("claim") or "evidence"),
                        content=h,
                        confidence=float(h.get("score") or h.get("confidence") or 0.55),
                        freshness=0.8 if (h.get("published_at") or "") >= "2026-01-01" else 0.5,
                        evidence_quality=float(h.get("score") or h.get("confidence") or 0.55),
                        source_trust=0.85,
                        why="Finance Retrieval Engine authoritative evidence",
                        latency_ms=ms,
                        dedupe_key=f"fre:{h.get('evidence_id') or h.get('label')}",
                    )
                )
            for s in (res.get("top_sources") or [])[:4]:
                if isinstance(s, dict):
                    items.append(
                        _item(
                            engine="fre",
                            kind="evidence",
                            title=str(s.get("title") or "source"),
                            content=s,
                            confidence=0.6,
                            source_trust=float(s.get("authority") or 6) / 10.0,
                            why="FRE related source document",
                            latency_ms=ms,
                            dedupe_key=f"fre:src:{s.get('title')}",
                        )
                    )
        return items, EngineContribution(engine="fre", requested=True, succeeded=True, item_count=len(items), latency_ms=ms)
