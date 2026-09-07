"""Relationship Builder — Company → Industry → Sector → Index → Peers → Clients."""

from __future__ import annotations

from app.contracts.models import EntityRefs, KnowledgeObject, KnowledgeObjectType
from app.storage.db import KaipStore


class RelationshipBuilder:
    def __init__(self, store: KaipStore) -> None:
        self.store = store

    def apply(self, ko: KnowledgeObject) -> EntityRefs:
        knowledge = ko.knowledge or ko.payload
        business = knowledge.get("business") if isinstance(knowledge.get("business"), dict) else {}
        sector = business.get("sector") or knowledge.get("sector")
        industry = business.get("industry") or knowledge.get("industry")
        clients = knowledge.get("customers") or business.get("customers") or []

        if ko.object_type == KnowledgeObjectType.COMPANY_PROFILE and ko.company_symbol:
            updated = self.store.update_entity_relationships(
                ko.company_symbol,
                sector=sector,
                industry=industry,
                clients=clients if isinstance(clients, list) else None,
            )
            if updated:
                ko.entity_refs = updated
                self._write_edges(updated)
                return updated

        if ko.company_symbol:
            current = self.store.get_entity(ko.company_symbol)
            if current:
                ko.entity_refs = current
                self._write_edges(current)
                return current
        return ko.entity_refs

    def _write_edges(self, refs: EntityRefs) -> None:
        symbol = refs.company_symbol
        if not symbol:
            return
        if refs.industry:
            self.store.upsert_relationship_edge(
                from_type="Company",
                from_key=symbol,
                edge_type="IN_INDUSTRY",
                to_type="Industry",
                to_key=refs.industry,
            )
            if refs.sector:
                self.store.upsert_relationship_edge(
                    from_type="Industry",
                    from_key=refs.industry,
                    edge_type="IN_SECTOR",
                    to_type="Sector",
                    to_key=refs.sector,
                )
        if refs.sector:
            self.store.upsert_relationship_edge(
                from_type="Company",
                from_key=symbol,
                edge_type="IN_SECTOR",
                to_type="Sector",
                to_key=refs.sector,
            )
        for index in refs.indexes:
            self.store.upsert_relationship_edge(
                from_type="Company",
                from_key=symbol,
                edge_type="IN_INDEX",
                to_type="Index",
                to_key=index,
            )
        for peer in refs.peers:
            self.store.upsert_relationship_edge(
                from_type="Company",
                from_key=symbol,
                edge_type="PEER_OF",
                to_type="Company",
                to_key=peer,
            )
        for client in refs.clients:
            self.store.upsert_relationship_edge(
                from_type="Company",
                from_key=symbol,
                edge_type="HAS_CLIENT",
                to_type="Client",
                to_key=str(client),
            )
