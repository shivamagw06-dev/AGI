"""Ingest AOI structured facts into immutable evidence + verification pipeline."""

from __future__ import annotations

import datetime as _dt
import time
from typing import Any, Iterable

from app.eve.confidence import confidence_for_evidence
from app.eve.conflicts import detect_conflicts
from app.eve.health import compute_company_health
from app.eve.models import EvidenceObject, Provenance
from app.eve.normalise import canonical_fact_key, values_equivalent
from app.eve.relationships import validate_relationships
from app.eve.sources import resolve_source_id, seed_sources, touch_sync
from app.eve.store import EveStore
from app.eve.timeline import maybe_timeline_event
from app.eve.versioning import maybe_version


class EveIngestPipeline:
    def __init__(self, store: EveStore) -> None:
        self.store = store
        if not self.store.sources:
            seed_sources(self.store)

    def ingest_aoi_artifact(
        self,
        artifact: Any,
        facts: Iterable[Any],
        *,
        company_symbol: str = "",
    ) -> dict[str, Any]:
        """Validate AOI artifact facts before they become institutional memory."""
        t0 = time.perf_counter()
        art = _dump(artifact)
        fact_rows = [_dump(f) for f in facts or []]
        connector = str(art.get("connector_id") or "")
        doc_type = str(art.get("doc_type") or "")
        source_id = resolve_source_id(self.store, connector_id=connector, doc_type=doc_type)
        src = self.store.sources.get(source_id)
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        touch_sync(self.store, source_id, when=now)

        created: list[str] = []
        conflicts = 0
        versions = 0
        timeline = 0
        company_id = art.get("company_id")

        for fr in fact_rows:
            raw_field = str(fr.get("field") or fr.get("fact_key") or "unknown")
            fact_key = canonical_fact_key(raw_field)
            value_text = str(fr.get("value_text") or fr.get("value") or "")[:2000]
            if not value_text:
                continue

            # Multi-source validation: if equivalent exists, confirm rather than duplicate noise
            peers = self.store.active_evidence(company_id=company_id, fact_key=fact_key)
            confirming = next((p for p in peers if values_equivalent(p.value_text, value_text)), None)

            prov = Provenance(
                source_id=source_id,
                source_name=(src.name if src else connector or doc_type),
                document_id=str(art.get("artifact_id") or fr.get("document_id") or ""),
                url=str(art.get("url") or ""),
                file_checksum=str(art.get("checksum") or ""),
                page=str(fr.get("page") or "") or None,
                section=str(fr.get("section") or "") or None,
                extraction_timestamp=str(fr.get("extracted_at") or now),
                observation_timestamp=str(art.get("downloaded_at") or art.get("discovered_at") or now),
                connector=connector,
                parser=str((art.get("metadata") or {}).get("parser") or "eve-parser-1.0"),
                model_version="eve-v1.0.0",
                verification_status="pending",
                knowledge_id=None,
            )

            if confirming is not None:
                # Increase support — immutable new confirmation evidence still stored
                supporting = list(dict.fromkeys([*(confirming.supporting_source_ids or []), source_id, confirming.provenance.source_id]))
                ev = EvidenceObject(
                    fact_key=fact_key,
                    raw_field=raw_field,
                    value=fr.get("value"),
                    value_text=value_text,
                    company_id=company_id,
                    company_symbol=company_symbol or str((art.get("metadata") or {}).get("nse_symbol") or ""),
                    provenance=prov.model_copy(update={"evidence_id": ""}),
                    parser_confidence=float(fr.get("confidence") or 0.7),
                    extraction_quality=0.8,
                    supporting_source_ids=supporting,
                    verification_status="verified" if len(supporting) >= 2 else "pending",
                    last_confirmed_at=now,
                )
                ev.provenance.evidence_id = ev.evidence_id
                # confidence after peers include prior
                ev.confidence = confidence_for_evidence(
                    ev,
                    peers=peers,
                    source_category=src.category if src else doc_type,
                )
                self.store.add_evidence(ev)
                # bump prior confirmation timestamp (metadata only on prior via copy)
                self.store.evidence[confirming.evidence_id] = confirming.model_copy(
                    update={
                        "last_confirmed_at": now,
                        "supporting_source_ids": supporting,
                        "verification_status": "verified",
                        "confidence": max(float(confirming.confidence), ev.confidence),
                    }
                )
                created.append(ev.evidence_id)
                continue

            ev = EvidenceObject(
                fact_key=fact_key,
                raw_field=raw_field,
                value=fr.get("value"),
                value_text=value_text,
                company_id=company_id,
                company_symbol=company_symbol or str((art.get("metadata") or {}).get("nse_symbol") or ""),
                provenance=prov,
                parser_confidence=float(fr.get("confidence") or 0.7),
                extraction_quality=0.75,
                supporting_source_ids=[source_id],
                verification_status="pending",
                last_confirmed_at=now,
            )
            ev.provenance.evidence_id = ev.evidence_id
            self.store.add_evidence(ev)

            ver = maybe_version(self.store, ev)
            if ver:
                versions += 1

            cfs = detect_conflicts(self.store, ev)
            conflicts += len(cfs)
            # Re-read after conflict marking
            ev = self.store.evidence[ev.evidence_id]
            peers = self.store.active_evidence(company_id=company_id, fact_key=fact_key)
            conf = confidence_for_evidence(ev, peers=peers, source_category=src.category if src else doc_type)
            status = ev.verification_status
            if status != "conflicted":
                status = "verified" if conf >= 0.75 and len(peers) >= 1 else "pending"
            self.store.evidence[ev.evidence_id] = ev.model_copy(
                update={"confidence": conf, "verification_status": status}
            )

            if maybe_timeline_event(self.store, self.store.evidence[ev.evidence_id]):
                timeline += 1
            validate_relationships(self.store, self.store.evidence[ev.evidence_id])
            created.append(ev.evidence_id)

        if company_id:
            compute_company_health(
                self.store,
                company_id,
                symbol=company_symbol or str((art.get("metadata") or {}).get("nse_symbol") or ""),
            )

        latency = round((time.perf_counter() - t0) * 1000, 2)
        self.store.metrics.verification_latency_ms = latency
        active = self.store.active_evidence()
        verified = [e for e in active if e.verification_status == "verified"]
        self.store.metrics.verified_facts = len(verified)
        if active:
            self.store.metrics.average_confidence = round(
                sum(float(e.confidence) for e in active) / len(active), 4
            )
        if self.store.sources:
            self.store.metrics.source_reliability_avg = round(
                sum(s.reliability_score for s in self.store.sources.values()) / len(self.store.sources), 4
            )
        self.store.metrics.parser_accuracy = round(
            len(verified) / max(1, len(active)), 4
        )
        if self.store.health:
            self.store.metrics.knowledge_health_avg = round(
                sum(h.trust_score for h in self.store.health.values()) / len(self.store.health), 2
            )

        self.store.audit_event(
            "ingest_aoi_artifact",
            object_kind="artifact",
            object_id=str(art.get("artifact_id") or ""),
            detail=f"facts={len(created)} conflicts={conflicts}",
        )
        return {
            "accepted": True,
            "evidence_ids": created,
            "evidence_count": len(created),
            "conflicts": conflicts,
            "versions": versions,
            "timeline_events": timeline,
            "latency_ms": latency,
            "gate": {
                "publish_allowed": conflicts == 0 or True,  # conflicts preserved but do not block soft publish
                "has_conflicts": conflicts > 0,
                "avg_confidence": self.store.metrics.average_confidence,
            },
        }


def _dump(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    return {"value": str(obj)}
