"""MEE engines — detect, normalise, severity, impact, similar, propagate."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

from app.mee.config import (
    DETECTION_KEYWORDS,
    EVENT_TAXONOMY,
    EVENT_TYPE_CATEGORY,
    IMPACT_CHAINS,
    MIN_EVIDENCE_CONFIDENCE,
)
from app.mee.models import (
    ImpactGraph,
    ImpactNode,
    MarketEvent,
    PropagationRecord,
    RelationshipEdge,
    TimelineEntry,
    new_id,
    now_iso,
)
from app.mee.store import MeeStore


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _canonical_type(raw: str) -> str:
    key = _norm_key(raw)
    if key in EVENT_TAXONOMY:
        return EVENT_TAXONOMY[key]
    for alias, canon in EVENT_TAXONOMY.items():
        if alias in key or key in alias:
            return canon
    # snake-ish fallback
    return re.sub(r"[^a-z0-9]+", "_", key).strip("_") or "other"


def _stable_fingerprint(event_type: str, company_ids: list[str], effective_date: str | None, title: str) -> str:
    blob = f"{event_type}|{','.join(sorted(company_ids))}|{effective_date or ''}|{_norm_key(title)[:80]}"
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def _avg(vals: list[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0.0


class MeeEngines:
    def __init__(
        self,
        store: MeeStore,
        *,
        eve: Any | None = None,
        iie: Any | None = None,
        fle: Any | None = None,
    ) -> None:
        self.store = store
        self.eve = eve
        self.iie = iie
        self.fle = fle
        self._fingerprints: dict[str, str] = {}  # fingerprint -> event_id

    # --- Normalisation -------------------------------------------------------

    def normalise_type(self, raw: str) -> tuple[str, str]:
        canon = _canonical_type(raw)
        category = EVENT_TYPE_CATEGORY.get(canon, "corporate")
        return canon, category

    # --- Detection -----------------------------------------------------------

    def detect_from_text(
        self,
        text: str,
        *,
        company_id: str = "",
        company_symbol: str = "",
        sector_id: str = "",
        evidence_ids: list[str] | None = None,
        evidence_links: list[dict[str, Any]] | None = None,
        confidence: float = 0.55,
        origin: str = "eve",
        effective_date: str | None = None,
        theme_ids: list[str] | None = None,
        forecast_ids: list[str] | None = None,
    ) -> list[MarketEvent]:
        blob = _norm_key(text)
        created: list[MarketEvent] = []
        for event_type, kws in DETECTION_KEYWORDS.items():
            if any(k in blob for k in kws):
                ev = self.create_event(
                    event_type=event_type,
                    title=text.strip()[:160] or event_type,
                    summary=text.strip()[:500],
                    company_ids=[company_id] if company_id else [],
                    company_symbols=[company_symbol] if company_symbol else [],
                    sector_ids=[sector_id] if sector_id else [],
                    theme_ids=list(theme_ids or []),
                    evidence_ids=list(evidence_ids or []),
                    evidence_links=list(evidence_links or []),
                    confidence=confidence,
                    origin=origin,
                    effective_date=effective_date,
                    forecast_ids=list(forecast_ids or []),
                )
                if ev:
                    created.append(ev)
        return created

    def create_event(
        self,
        *,
        event_type: str,
        title: str,
        summary: str = "",
        company_ids: list[str] | None = None,
        company_symbols: list[str] | None = None,
        sector_ids: list[str] | None = None,
        theme_ids: list[str] | None = None,
        evidence_ids: list[str] | None = None,
        evidence_links: list[dict[str, Any]] | None = None,
        confidence: float = 0.55,
        origin: str = "eve",
        effective_date: str | None = None,
        event_time: str | None = None,
        forecast_ids: list[str] | None = None,
        risk_ids: list[str] | None = None,
        catalyst_ids: list[str] | None = None,
        tags: list[str] | None = None,
        status: str = "detected",
        parent_event_id: str = "",
        version: int = 1,
        subcategory: str = "",
        country: str = "IN",
    ) -> MarketEvent | None:
        canon, category = self.normalise_type(event_type)
        company_ids = list(company_ids or [])
        company_symbols = list(company_symbols or [])
        sector_ids = list(sector_ids or [])
        theme_ids = list(theme_ids or [])
        evidence_ids = list(evidence_ids or [])
        evidence_links = list(evidence_links or [])
        conf = float(confidence)
        if conf < MIN_EVIDENCE_CONFIDENCE and not evidence_ids and not evidence_links:
            return None

        fp = _stable_fingerprint(canon, company_ids, effective_date, title)
        if fp in self._fingerprints:
            existing_id = self._fingerprints[fp]
            # Duplicate detection
            dup = MarketEvent(
                event_id=new_id("evt"),
                event_type=canon,
                category=category,
                subcategory=subcategory or canon,
                title=title,
                summary=summary or title,
                confidence=conf,
                status="archived",
                duplicate_of=existing_id,
                origin=origin,
                evidence_ids=evidence_ids,
                company_ids=company_ids,
            )
            self.store.add_event(dup)
            self.store.mark_duplicate(dup.event_id, existing_id)
            # bump source count on original
            orig = self.store.events.get(existing_id)
            if orig:
                orig.source_count += 1
                for eid in evidence_ids:
                    if eid and eid not in orig.evidence_ids:
                        orig.evidence_ids.append(eid)
            return None

        severity = self.score_severity(
            event_type=canon,
            category=category,
            company_ids=company_ids,
            sector_ids=sector_ids,
            confidence=conf,
            title=title,
        )
        monitoring = [
            "Confirm official disclosure",
            "Update affected company timelines",
            "Review forecast implications",
            "Check portfolio exposure",
        ]
        event = MarketEvent(
            event_id=new_id("evt"),
            event_type=canon,
            category=category,
            subcategory=subcategory or canon,
            title=title[:200],
            summary=summary or title,
            effective_date=effective_date,
            event_time=event_time,
            severity=severity,
            confidence=conf,
            importance="high" if severity in {"critical", "high"} else "normal",
            status=status,
            source_count=max(1, len(set(evidence_ids)) or len(evidence_links) or 1),
            evidence_ids=evidence_ids,
            evidence_links=evidence_links[:20],
            version=version,
            parent_event_id=parent_event_id,
            company_ids=company_ids,
            company_symbols=company_symbols,
            sector_ids=sector_ids,
            theme_ids=theme_ids,
            forecast_ids=list(forecast_ids or []),
            risk_ids=list(risk_ids or []),
            catalyst_ids=list(catalyst_ids or []),
            tags=list(tags or [canon, category]),
            country=country,
            expected_duration="event_dependent",
            monitoring_checklist=monitoring,
            forecast_implications=[f"Reassess {canon} implications for related forecasts"],
            portfolio_implications=["Review exposure to affected companies/sectors"],
            origin=origin,
        )
        self.store.add_event(event)
        self._fingerprints[fp] = event.event_id
        self._link_event(event)
        return event

    def version_event(self, event_id: str, **updates: Any) -> MarketEvent:
        prior = self.store.events.get(event_id)
        if not prior:
            raise KeyError(f"Event '{event_id}' not found")
        # clear fingerprint so new version can register
        for fp, eid in list(self._fingerprints.items()):
            if eid == event_id:
                del self._fingerprints[fp]
        new = self.create_event(
            event_type=updates.get("event_type", prior.event_type),
            title=updates.get("title", prior.title),
            summary=updates.get("summary", prior.summary),
            company_ids=list(updates.get("company_ids", prior.company_ids)),
            company_symbols=list(prior.company_symbols),
            sector_ids=list(updates.get("sector_ids", prior.sector_ids)),
            theme_ids=list(prior.theme_ids),
            evidence_ids=list(updates.get("evidence_ids", prior.evidence_ids)),
            evidence_links=list(updates.get("evidence_links", prior.evidence_links)),
            confidence=float(updates.get("confidence", prior.confidence)),
            origin=prior.origin,
            effective_date=updates.get("effective_date", prior.effective_date),
            forecast_ids=list(prior.forecast_ids),
            status="updated",
            parent_event_id=prior.event_id,
            version=prior.version + 1,
        )
        if not new:
            raise RuntimeError("Failed to create event version")
        self.store.mark_status(prior.event_id, "superseded")
        return new

    # --- Severity ------------------------------------------------------------

    def score_severity(
        self,
        *,
        event_type: str,
        category: str,
        company_ids: list[str],
        sector_ids: list[str],
        confidence: float,
        title: str,
    ) -> str:
        score = 0.0
        critical_types = {"acquisition", "merger", "rating_downgrade", "repo_rate", "cyber_attack", "sanctions"}
        high_types = {"buyback", "executive_change", "large_order", "oil_price", "budget", "guidance"}
        if event_type in critical_types or category in {"geopolitical", "central_bank"}:
            score += 0.45
        elif event_type in high_types:
            score += 0.3
        else:
            score += 0.15
        if len(company_ids) > 1 or len(sector_ids) > 1:
            score += 0.1
        if confidence >= 0.75:
            score += 0.15
        elif confidence >= 0.55:
            score += 0.08
        text = _norm_key(title)
        if any(w in text for w in ("major", "shock", "crisis", "default", "resign")):
            score += 0.15
        # soft portfolio exposure hint via FLE/IIE presence
        if company_ids and self.fle:
            try:
                for cid in company_ids[:2]:
                    pack = self.fle.company(cid, generate_if_empty=False)
                    if isinstance(pack, dict) and (pack.get("pending_forecasts") or pack.get("historical_forecasts")):
                        score += 0.05
                        break
            except Exception:
                pass
        if score >= 0.75:
            return "critical"
        if score >= 0.55:
            return "high"
        if score >= 0.35:
            return "medium"
        if score >= 0.2:
            return "low"
        return "informational"

    # --- Impact --------------------------------------------------------------

    def build_impact(self, event_id: str) -> ImpactGraph:
        ev = self.store.events.get(event_id)
        if not ev:
            raise KeyError(f"Event '{event_id}' not found")
        chain = list(IMPACT_CHAINS.get(ev.event_type) or [])
        # company-direct
        first: list[ImpactNode] = []
        for cid in ev.company_ids:
            first.append(
                ImpactNode(
                    order=1,
                    entity_type="company",
                    entity_id=cid,
                    impact="direct",
                    description=f"Direct impact from {ev.event_type}",
                    confidence=ev.confidence,
                )
            )
        for sid in ev.sector_ids:
            first.append(
                ImpactNode(
                    order=1,
                    entity_type="sector",
                    entity_id=sid,
                    impact="direct",
                    description=f"Direct sector impact from {ev.event_type}",
                    confidence=ev.confidence * 0.95,
                )
            )
        if not first and chain:
            first.append(
                ImpactNode(
                    order=1,
                    entity_type="sector",
                    entity_id=chain[0],
                    impact="direct",
                    description=f"Primary sector in {ev.event_type} chain",
                    confidence=ev.confidence * 0.9,
                )
            )

        second: list[ImpactNode] = []
        third: list[ImpactNode] = []
        for i, sid in enumerate(chain):
            node = ImpactNode(
                order=2 if i < 3 else 3,
                entity_type="sector",
                entity_id=sid,
                impact="indirect",
                description=f"Propagation hop {i + 1} for {ev.event_type}",
                confidence=max(0.2, ev.confidence - 0.08 * i),
            )
            if i == 0 and not ev.sector_ids:
                continue  # already as first if chain[0]
            if i < 3:
                second.append(node)
            else:
                third.append(node)

        # Enrich company lists from IIE sector packs (soft)
        if self.iie and chain:
            try:
                for sid in chain[:3]:
                    sec = self.iie.sector(sid)
                    for co in (sec.get("companies") or [])[:5]:
                        cid = co.get("company_id") if isinstance(co, dict) else None
                        if cid and cid not in {n.entity_id for n in first}:
                            second.append(
                                ImpactNode(
                                    order=2,
                                    entity_type="company",
                                    entity_id=cid,
                                    impact="indirect",
                                    description=f"Listed company in {sid}",
                                    confidence=ev.confidence * 0.6,
                                )
                            )
            except Exception:
                pass

        for tid in ev.theme_ids:
            second.append(
                ImpactNode(
                    order=2,
                    entity_type="theme",
                    entity_id=tid,
                    impact="indirect",
                    description="Theme exposure",
                    confidence=ev.confidence * 0.7,
                )
            )

        graph = ImpactGraph(
            impact_id=new_id("imp"),
            event_id=event_id,
            direct=[n for n in first if n.impact == "direct"],
            indirect=second + third,
            first_order=first,
            second_order=second,
            third_order=third,
            chain=chain or [n.entity_id for n in first],
        )
        self.store.put_impact(graph)
        # relationship edges for graph query
        for node in first + second + third:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"),
                    from_id=event_id,
                    to_id=node.entity_id,
                    relation_type=f"impacts_{node.entity_type}_order_{node.order}",
                )
            )
        return graph

    # --- Verify + Timeline + Propagate ---------------------------------------

    def verify(self, event_id: str) -> MarketEvent:
        t0 = time.perf_counter()
        ev = self.store.events.get(event_id)
        if not ev or ev.soft_deleted:
            raise KeyError(f"Event '{event_id}' not found")
        if ev.duplicate_of:
            return ev
        self.store.mark_status(event_id, "verified", verified=True)
        # build impact
        self.build_impact(event_id)
        # timelines
        self._write_timelines(ev)
        # soft historical analogues
        analogues = self.find_similar(event_id, limit=5)
        ev.historical_analogues = [a["event_id"] for a in analogues]
        # propagate
        self.propagate(event_id)
        self.store.mark_status(event_id, "published")
        self.store.dequeue(event_id)
        self.store.metrics.verification_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return ev

    def propagate(self, event_id: str) -> PropagationRecord:
        t0 = time.perf_counter()
        ev = self.store.events.get(event_id)
        if not ev:
            raise KeyError(f"Event '{event_id}' not found")
        key = f"prop:{event_id}:v{ev.version}"
        # idempotent
        for p in self.store.propagations:
            if p.idempotency_key == key and p.status == "done":
                return p
        targets = ["iie", "fle", "pmo", "ime", "ams", "ask_agi"]
        detail: dict[str, Any] = {"soft_updates": {}, "future_hooks": ["pmo", "ime", "ams"]}
        # Soft, non-destructive hints — do not redesign IIE/FLE
        if self.iie:
            try:
                for cid in ev.company_ids[:3]:
                    # touch company pack (may analyse if missing) — additive only
                    self.iie.company(cid, analyse_if_missing=False)
                detail["soft_updates"]["iie"] = {"companies_touched": ev.company_ids[:3]}
            except Exception as exc:
                detail["soft_updates"]["iie"] = {"error": str(exc)[:120]}
        if self.fle:
            try:
                # link event to forecast implications without mutating forecasts
                detail["soft_updates"]["fle"] = {
                    "forecast_ids": list(ev.forecast_ids),
                    "implication": "reassess_on_event",
                }
            except Exception as exc:
                detail["soft_updates"]["fle"] = {"error": str(exc)[:120]}
        detail["soft_updates"]["ask_agi"] = {"notify": "recent_events_context"}
        rec = PropagationRecord(
            propagation_id=new_id("prop"),
            event_id=event_id,
            targets=targets,
            status="done",
            idempotency_key=key,
            detail=detail,
            completed_at=now_iso(),
        )
        self.store.add_propagation(rec)
        self.store.metrics.propagation_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        self.store.audit_event("propagate", object_kind="event", object_id=event_id, detail=key)
        return rec

    def find_similar(self, event_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
        ev = self.store.events.get(event_id)
        if not ev:
            return []
        hits = []
        for other in self.store.active_events():
            if other.event_id == event_id:
                continue
            score = 0.0
            if other.event_type == ev.event_type:
                score += 0.5
            if other.category == ev.category:
                score += 0.15
            if set(other.sector_ids) & set(ev.sector_ids):
                score += 0.15
            if set(other.company_ids) & set(ev.company_ids):
                score += 0.1
            if abs(other.confidence - ev.confidence) < 0.15:
                score += 0.05
            if score >= 0.5:
                outcome_note = ""
                if self.fle and other.forecast_ids:
                    outcome_note = "linked_forecasts_present"
                hits.append(
                    {
                        "event_id": other.event_id,
                        "event_type": other.event_type,
                        "title": other.title,
                        "severity": other.severity,
                        "score": round(score, 4),
                        "effective_date": other.effective_date,
                        "lessons": outcome_note or "review_historical_market_impact",
                    }
                )
        hits.sort(key=lambda h: -h["score"])
        return hits[:limit]

    # --- Ingest from upstream ------------------------------------------------

    def ingest_from_eve(self, *, limit: int = 50) -> dict[str, Any]:
        if not self.eve:
            return {"created": 0, "events": []}
        try:
            listed = self.eve.list_evidence(limit=limit)
            rows = listed.get("evidence") if isinstance(listed, dict) else []
        except Exception:
            rows = []
        created_ids = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            conf = float(row.get("confidence") or 0)
            if conf < MIN_EVIDENCE_CONFIDENCE:
                continue
            text = row.get("value_text") or row.get("fact_key") or ""
            events = self.detect_from_text(
                text,
                company_id=row.get("company_id") or "",
                company_symbol=row.get("company_symbol") or "",
                evidence_ids=[row["evidence_id"]] if row.get("evidence_id") else [],
                evidence_links=[
                    {
                        "evidence_id": row.get("evidence_id"),
                        "claim_text": (row.get("value_text") or "")[:200],
                        "confidence": conf,
                        "status": row.get("verification_status"),
                    }
                ],
                confidence=conf,
                origin="eve",
            )
            for ev in events:
                created_ids.append(ev.event_id)
                if ev.status == "detected":
                    try:
                        self.verify(ev.event_id)
                    except Exception:
                        self.store.metrics.processing_failures += 1
        return {"created": len(created_ids), "events": created_ids}

    def ingest_from_iie(self, company_key: str) -> dict[str, Any]:
        if not self.iie:
            return {"created": 0, "events": []}
        try:
            pack = self.iie.company(company_key, analyse_if_missing=True)
        except Exception:
            return {"created": 0, "events": []}
        company_id = pack.get("company_id") or company_key
        symbol = pack.get("symbol") or ""
        created_ids = []
        for cat in pack.get("catalysts") or []:
            if not isinstance(cat, dict):
                continue
            title = cat.get("title") or cat.get("catalyst_type") or "catalyst"
            ev = self.create_event(
                event_type=cat.get("catalyst_type") or title,
                title=title,
                summary=title,
                company_ids=[company_id],
                company_symbols=[symbol] if symbol else [],
                evidence_ids=list(cat.get("evidence_ids") or []),
                evidence_links=list((cat.get("explainability") or {}).get("supporting_evidence") or []),
                confidence=float(cat.get("confidence") or 0.55),
                origin="iie",
                catalyst_ids=[cat.get("catalyst_id")] if cat.get("catalyst_id") else [],
                tags=["iie", "catalyst"],
            )
            if ev:
                created_ids.append(ev.event_id)
                self.verify(ev.event_id)
        for risk in pack.get("risks") or []:
            if not isinstance(risk, dict):
                continue
            title = risk.get("title") or risk.get("risk_type") or "risk"
            # only materialise as event for certain risk types
            if risk.get("risk_type") not in {"regulatory", "governance", "financial"}:
                continue
            ev = self.create_event(
                event_type=risk.get("risk_type") or "regulatory_action",
                title=title,
                summary=risk.get("description") or title,
                company_ids=[company_id],
                company_symbols=[symbol] if symbol else [],
                evidence_ids=list(risk.get("evidence_ids") or []),
                confidence=float(risk.get("confidence") or 0.5),
                origin="iie",
                risk_ids=[risk.get("risk_id")] if risk.get("risk_id") else [],
                tags=["iie", "risk"],
            )
            if ev:
                created_ids.append(ev.event_id)
                self.verify(ev.event_id)
        return {"created": len(created_ids), "events": created_ids}

    def ingest_from_fle(self, company_key: str) -> dict[str, Any]:
        if not self.fle:
            return {"created": 0, "events": []}
        try:
            pack = self.fle.company(company_key, generate_if_empty=False)
        except Exception:
            return {"created": 0, "events": []}
        company_id = pack.get("company_id") or company_key
        created_ids = []
        for fc in (pack.get("pending_forecasts") or [])[:5]:
            if not isinstance(fc, dict):
                continue
            title = f"Forecast outstanding: {fc.get('metric')} → {fc.get('predicted_value')}"
            ev = self.create_event(
                event_type="guidance",
                title=title[:160],
                summary=title,
                company_ids=[company_id],
                company_symbols=[fc.get("company_symbol") or ""],
                evidence_ids=list(fc.get("evidence_ids") or []),
                evidence_links=list(fc.get("evidence_links") or []),
                confidence=float(fc.get("confidence") or 0.5),
                origin="fle",
                forecast_ids=[fc.get("forecast_id")] if fc.get("forecast_id") else [],
                tags=["fle", "forecast"],
            )
            if ev:
                created_ids.append(ev.event_id)
                self.verify(ev.event_id)
        return {"created": len(created_ids), "events": created_ids}

    # --- helpers -------------------------------------------------------------

    def _link_event(self, ev: MarketEvent) -> None:
        for eid in ev.evidence_ids:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"), from_id=ev.event_id, to_id=eid, relation_type="supported_by_evidence"
                )
            )
        for cid in ev.company_ids:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"), from_id=ev.event_id, to_id=cid, relation_type="affects_company"
                )
            )
        for sid in ev.sector_ids:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"), from_id=ev.event_id, to_id=sid, relation_type="affects_sector"
                )
            )
        for tid in ev.theme_ids:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"), from_id=ev.event_id, to_id=tid, relation_type="affects_theme"
                )
            )
        for fid in ev.forecast_ids:
            self.store.add_relationship(
                RelationshipEdge(
                    edge_id=new_id("rel"), from_id=ev.event_id, to_id=fid, relation_type="linked_forecast"
                )
            )

    def _write_timelines(self, ev: MarketEvent) -> None:
        for cid in ev.company_ids:
            self.store.add_timeline(
                TimelineEntry(
                    entry_id=new_id("tl"),
                    scope="company",
                    scope_id=cid,
                    event_id=ev.event_id,
                    event_type=ev.event_type,
                    title=ev.title,
                    effective_date=ev.effective_date or ev.detected_at[:10],
                    severity=ev.severity,
                )
            )
        for sid in ev.sector_ids or (self.store.impacts.get(ev.event_id).chain[:1] if self.store.impacts.get(ev.event_id) else []):
            self.store.add_timeline(
                TimelineEntry(
                    entry_id=new_id("tl"),
                    scope="sector",
                    scope_id=sid,
                    event_id=ev.event_id,
                    event_type=ev.event_type,
                    title=ev.title,
                    effective_date=ev.effective_date or ev.detected_at[:10],
                    severity=ev.severity,
                )
            )
        for tid in ev.theme_ids:
            self.store.add_timeline(
                TimelineEntry(
                    entry_id=new_id("tl"),
                    scope="theme",
                    scope_id=tid,
                    event_id=ev.event_id,
                    event_type=ev.event_type,
                    title=ev.title,
                    effective_date=ev.effective_date or ev.detected_at[:10],
                    severity=ev.severity,
                )
            )
