"""Historical Relationship Engine — evidence-backed cause-and-effect graph."""

from __future__ import annotations

from typing import Any
from uuid import uuid5, NAMESPACE_URL

from app.contracts.models import (
    HistoricalRelationship,
    RelationshipConfidence,
    RelationshipDirection,
    RelationshipDomain,
    RelationshipEvidence,
    RelationshipType,
)
from app.hri import traces
from app.hri.catalog import all_catalog_entries
from app.hri.validation import score_confidence, validate_relationship
from app.storage.db import HipStore


def _stable_id(domain: str, source: str, target: str, rel_type: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"hri:{domain}:{source}:{target}:{rel_type}"))


class HistoricalRelationshipEngine:
    def __init__(self, store: HipStore) -> None:
        self.store = store

    def rebuild_all(self, symbols: list[str] | None = None) -> dict[str, Any]:
        span = traces.begin("historical_relationship_builder", meta={"symbols": symbols or []})
        self.store.clear_relationship_graph()
        published = 0
        rejected = 0
        derived = 0

        for entry in all_catalog_entries():
            rel = self._from_catalog(entry)
            ok = self._validate_and_publish(rel)
            if ok:
                published += 1
            else:
                rejected += 1

        # Derive additional edges from timeline links (only with evidence)
        for symbol in symbols or []:
            n = self._derive_from_timeline(symbol.upper())
            derived += n
            published += n

        # Sector/market/macro timeline link derivation
        for scope, subject in (
            ("sector", "information_technology"),
            ("sector", "financials"),
            ("market", "nifty"),
            ("macro", "india"),
        ):
            n = self._derive_timeline_scope(scope, subject)
            derived += n
            published += n

        out = {
            "published": published,
            "rejected": rejected,
            "derived_from_timelines": derived,
            "total": self.store.count_relationships(published_only=True),
        }
        traces.end(span, output=out)
        return out

    def _from_catalog(self, entry: dict[str, Any]) -> HistoricalRelationship:
        evidence = [
            RelationshipEvidence(
                kind=e["kind"],
                summary=e["summary"],
                period=e.get("period"),
                source_refs=list(e.get("source_refs") or []),
                weight=float(e.get("weight") or 1.0),
            )
            for e in (entry.get("evidence") or [])
        ]
        domain = RelationshipDomain(entry["domain"])
        rel_type = RelationshipType(entry["relationship_type"])
        conf = RelationshipConfidence(entry.get("confidence") or RelationshipConfidence.MEDIUM.value)
        rid = _stable_id(domain.value, entry["source_key"], entry["target_key"], rel_type.value)
        return HistoricalRelationship(
            relationship_id=rid,
            domain=domain,
            source_key=entry["source_key"],
            source_label=entry["source_label"],
            target_key=entry["target_key"],
            target_label=entry["target_label"],
            relationship_type=rel_type,
            direction=RelationshipDirection.DIRECTED,
            confidence=conf,
            occurrences=int(entry.get("occurrences") or 1),
            average_delay=entry.get("average_delay"),
            first_observed=entry.get("first_observed"),
            last_confirmed=entry.get("last_confirmed"),
            evidence=evidence,
            chain=list(entry.get("chain") or []),
            version=1,
            published=False,
            status="draft",
        )

    def _validate_and_publish(self, rel: HistoricalRelationship) -> bool:
        vspan = traces.begin(
            "relationship_validation",
            meta={"source": rel.source_key, "target": rel.target_key, "type": rel.relationship_type.value},
        )
        errors = validate_relationship(rel)
        if errors:
            traces.end(vspan, ok=False, output={"errors": errors})
            return False
        # Re-score confidence from evidence weight (never upgrade beyond evidence)
        scored = score_confidence(rel)
        # Keep catalog High only if scorer agrees High or Medium with strong occurrences
        if rel.confidence == RelationshipConfidence.HIGH and scored == RelationshipConfidence.LOW:
            rel.confidence = scored
        elif scored == RelationshipConfidence.HIGH:
            rel.confidence = RelationshipConfidence.HIGH
        traces.end(vspan, output={"confidence": rel.confidence.value})

        pspan = traces.begin(
            "relationship_publication",
            meta={"relationship_id": rel.relationship_id},
        )
        rel.published = True
        rel.status = "published"
        self.store.upsert_relationship(rel)
        traces.end(pspan, output={"published": True, "evidence": len(rel.evidence)})
        return True

    def _derive_from_timeline(self, symbol: str) -> int:
        links = self.store.list_timeline_links(symbol)
        events = self.store.get_timeline("company", symbol)
        titles = {e.get("title") for e in events}
        count = 0
        for link in links:
            from_key = link.get("from_key") or ""
            to_key = link.get("to_key") or ""
            relation = link.get("relation") or "affected"
            if not from_key or not to_key:
                continue
            # Evidence: the timeline link itself + matching event titles
            evidence = [
                RelationshipEvidence(
                    kind="timeline_link",
                    summary=f"Timeline link {from_key} —{relation}→ {to_key}",
                    period=None,
                    source_refs=[from_key, to_key],
                    weight=1.0,
                )
            ]
            # Prefer mapping known relation names
            try:
                rel_type = {
                    "caused": RelationshipType.CAUSED,
                    "affected": RelationshipType.AFFECTED,
                    "transmitted_to": RelationshipType.TRANSMISSION,
                    "joined_market": RelationshipType.TRANSMISSION,
                }.get(relation, RelationshipType.AFFECTED)
            except Exception:
                rel_type = RelationshipType.AFFECTED

            # Domain: company if symbol appears, else macro/sector heuristic
            domain = RelationshipDomain.COMPANY
            if from_key.startswith("macro:") or "macro:" in from_key:
                domain = RelationshipDomain.MACRO
            elif from_key.startswith("information_technology") or "information_technology" in from_key:
                domain = RelationshipDomain.SECTOR

            rel = HistoricalRelationship(
                relationship_id=_stable_id(domain.value, from_key, to_key, rel_type.value),
                domain=domain,
                source_key=from_key,
                source_label=from_key.split(":")[-1] if ":" in from_key else from_key,
                target_key=to_key,
                target_label=to_key.split(":")[-1] if ":" in to_key else to_key,
                relationship_type=rel_type,
                confidence=RelationshipConfidence.MEDIUM,
                occurrences=1,
                evidence=evidence,
                chain=[],
                version=1,
            )
            # Only publish if we have timeline support (title overlap or link note)
            if any(t and (str(t) in from_key or str(t) in to_key) for t in titles) or link.get("note"):
                if self._validate_and_publish(rel):
                    count += 1
            elif self._validate_and_publish(rel):
                # Still publish when evidence list is non-empty (timeline_link evidence)
                count += 1
        return count

    def _derive_timeline_scope(self, scope: str, subject: str) -> int:
        events = self.store.get_timeline(scope, subject)
        if len(events) < 2:
            return 0
        count = 0
        # Connect consecutive narrative anchors as temporal transmission (evidence = both events)
        ordered = sorted(events, key=lambda e: (e.get("year") or 0, e.get("title") or ""))
        for a, b in zip(ordered, ordered[1:]):
            evidence = [
                RelationshipEvidence(
                    kind="timeline_link",
                    summary=f"{scope} timeline succession {a.get('year')} {a.get('title')} → {b.get('year')} {b.get('title')}",
                    period=f"{a.get('year')}-{b.get('year')}",
                    source_refs=[a.get("event_id") or "", b.get("event_id") or ""],
                    weight=0.8,
                )
            ]
            domain = {
                "company": RelationshipDomain.COMPANY,
                "sector": RelationshipDomain.SECTOR,
                "market": RelationshipDomain.MARKET,
                "macro": RelationshipDomain.MACRO,
            }.get(scope, RelationshipDomain.MARKET)
            src = f"{subject}:{a.get('year')}:{a.get('title')}"
            tgt = f"{subject}:{b.get('year')}:{b.get('title')}"
            rel = HistoricalRelationship(
                relationship_id=_stable_id(domain.value, src, tgt, RelationshipType.TRANSMISSION.value),
                domain=domain,
                source_key=src,
                source_label=str(a.get("title")),
                target_key=tgt,
                target_label=str(b.get("title")),
                relationship_type=RelationshipType.TRANSMISSION,
                confidence=RelationshipConfidence.LOW,
                occurrences=1,
                first_observed=str(a.get("year")),
                last_confirmed=str(b.get("year")),
                evidence=evidence,
                version=1,
            )
            if self._validate_and_publish(rel):
                count += 1
        return count

    # ----- Retrieval -----

    def company_relationships(self, symbol: str) -> dict[str, Any]:
        span = traces.begin("relationship_retrieval", meta={"kind": "company", "symbol": symbol})
        rows = self.store.list_relationships(company_symbol=symbol)
        out = {
            "company_symbol": symbol.upper(),
            "providers_queried": [],
            "count": len(rows),
            "relationships": rows,
            "graph": self._graph_view(rows, root=symbol.upper()),
        }
        traces.end(span, output={"count": len(rows)})
        return out

    def sector_relationships(self, sector: str) -> dict[str, Any]:
        span = traces.begin("relationship_retrieval", meta={"kind": "sector", "sector": sector})
        rows = self.store.list_relationships(sector_key=sector)
        # Also include catalog domain=sector by source/target match
        if not rows:
            rows = self.store.list_relationships(domain="sector")
            sk = sector.lower().replace(" ", "_")
            rows = [
                r
                for r in rows
                if sk in (r.get("source_key") or "")
                or sk in (r.get("target_key") or "")
                or sk in str(r.get("source_label") or "").lower().replace(" ", "_")
            ]
        out = {
            "sector_key": sector.lower().replace(" ", "_"),
            "providers_queried": [],
            "count": len(rows),
            "relationships": rows,
            "graph": self._graph_view(rows, root=sector),
        }
        traces.end(span, output={"count": len(rows)})
        return out

    def macro_relationships(self, event: str) -> dict[str, Any]:
        span = traces.begin("relationship_retrieval", meta={"kind": "macro", "event": event})
        rows = self.store.list_relationships(macro_event=event)
        out = {
            "macro_event": event,
            "providers_queried": [],
            "count": len(rows),
            "relationships": rows,
            "transmission_chains": [
                {
                    "source": r.get("source_label"),
                    "target": r.get("target_label"),
                    "chain": r.get("chain") or [],
                    "relationship": r.get("relationship_type"),
                    "confidence": r.get("confidence"),
                    "occurrences": r.get("occurrences"),
                    "average_delay": r.get("average_delay"),
                    "evidence": r.get("evidence") or [],
                }
                for r in rows
            ],
            "graph": self._graph_view(rows, root=event),
        }
        traces.end(span, output={"count": len(rows)})
        return out

    def market_relationships(self) -> dict[str, Any]:
        span = traces.begin("relationship_retrieval", meta={"kind": "market"})
        rows = self.store.list_relationships(market=True)
        if not rows:
            rows = self.store.list_relationships(domain="market")
        out = {
            "market": "NIFTY",
            "providers_queried": [],
            "count": len(rows),
            "relationships": rows,
            "graph": self._graph_view(rows, root="nifty"),
        }
        traces.end(span, output={"count": len(rows)})
        return out

    def explain(
        self,
        *,
        source: str,
        target: str,
    ) -> dict[str, Any]:
        """Retrieval path for questions like: How have RBI rate cuts affected HDFC Bank?"""
        span = traces.begin(
            "relationship_retrieval",
            meta={"kind": "explain", "source": source, "target": target},
        )
        source_l = source.lower().replace(" ", "_")
        target_u = target.upper()
        target_l = target.lower().replace(" ", "_")

        # Pull macro + company intersections
        macro_rows = self.store.list_relationships(macro_event=source_l)
        company_rows = self.store.list_relationships(company_symbol=target_u) if target_u.isalpha() else []
        matched = []
        for r in macro_rows + company_rows:
            sk = (r.get("source_key") or "").lower()
            sl = (r.get("source_label") or "").lower()
            tk = (r.get("target_key") or "").lower()
            tl = (r.get("target_label") or "").lower()
            src_hit = source_l in sk or source_l.replace("_", " ") in sl or "rbi" in source_l and ("rbi" in sk or "rbi" in sl or "rate" in sk)
            tgt_hit = target_l in tk or target_l in tl or target_u.lower() in tk or target_u.lower() in tl
            if src_hit and tgt_hit:
                matched.append(r)
            elif src_hit and (target_u in (r.get("chain") or []) or any(target_l in str(c).lower() for c in (r.get("chain") or []))):
                matched.append(r)

        # Dedup
        seen = set()
        unique = []
        for r in matched:
            rid = r.get("relationship_id")
            if rid in seen:
                continue
            seen.add(rid)
            unique.append(r)

        timeline = self.store.get_timeline("company", target_u) if target_u.isalpha() else []
        financials = (
            self.store.list_financials(target_u, period_kind="annual", limit=20) if target_u.isalpha() else []
        )
        out = {
            "question": f"How have {source} historically affected {target}?",
            "providers_queried": [],
            "source": source,
            "target": target,
            "relationships": unique,
            "transmission_chains": [
                {
                    "path": [r.get("source_label"), *(r.get("chain") or []), r.get("target_label")],
                    "relationship": r.get("relationship_type"),
                    "confidence": r.get("confidence"),
                    "occurrences": r.get("occurrences"),
                    "average_delay": r.get("average_delay"),
                    "evidence": r.get("evidence") or [],
                }
                for r in unique
            ],
            "bundle": {
                "historical_macro_cycles": [r for r in unique if r.get("domain") == "macro"],
                "historical_company_performance_tip": financials[-3:] if financials else [],
                "relationship_evidence": [e for r in unique for e in (r.get("evidence") or [])],
                "timeline": [
                    {"year": e.get("year"), "title": e.get("title")}
                    for e in timeline
                    if e.get("title")
                ],
                "current_entity": self.store.get_entity(target_u) if target_u.isalpha() else None,
            },
            "note": "KRIG/Ask consume this bundle — zero external provider calls. Judgment remains in IE.",
        }
        traces.end(span, output={"matched": len(unique)})
        return out

    @staticmethod
    def _graph_view(rows: list[dict[str, Any]], *, root: str) -> dict[str, Any]:
        nodes = {root}
        edges = []
        for r in rows:
            nodes.add(r.get("source_label") or r.get("source_key"))
            nodes.add(r.get("target_label") or r.get("target_key"))
            for c in r.get("chain") or []:
                nodes.add(c)
            edges.append(
                {
                    "from": r.get("source_label") or r.get("source_key"),
                    "to": r.get("target_label") or r.get("target_key"),
                    "type": r.get("relationship_type"),
                    "confidence": r.get("confidence"),
                    "chain": r.get("chain") or [],
                }
            )
        return {"root": root, "nodes": sorted(str(n) for n in nodes if n), "edges": edges}
