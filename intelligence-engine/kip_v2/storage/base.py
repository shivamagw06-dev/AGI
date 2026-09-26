"""Abstract KnowledgeStore contract implemented by both the SQLite (default)
and Postgres/pgvector (production) backends.

Every mutating method that accepts a :class:`~kip_v2.schema.Fact` runs it
through :func:`kip_v2.evidence.validate_fact` first (Module 7). This is
enforced here, in the base class, via :meth:`KnowledgeStore.store_fact`
calling :meth:`_persist_fact` only after validation — so a backend cannot
accidentally skip the gate by overriding the wrong method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from kip_v2.evidence import validate_fact
from kip_v2.schema import (
    ChangeDelta,
    Document,
    Fact,
    FactStatus,
    GraphEdge,
    GraphNode,
    Paragraph,
)


class KnowledgeStore(ABC):
    # ---- documents -------------------------------------------------
    @abstractmethod
    def store_document(self, document: Document) -> None: ...

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]: ...

    @abstractmethod
    def list_documents(self, company_id: str) -> list[Document]: ...

    # ---- paragraphs (Module 1 evidence index) -----------------------
    @abstractmethod
    def paragraph_exists(self, document_id: str, evidence_hash: str) -> bool: ...

    @abstractmethod
    def store_paragraph(self, paragraph: Paragraph) -> bool:
        """Returns True if newly stored, False if it already existed
        (idempotent re-ingestion, Module 10)."""

    @abstractmethod
    def list_paragraphs(self, document_id: str) -> list[Paragraph]: ...

    @abstractmethod
    def all_paragraphs(self, company_id: str) -> list[Paragraph]: ...

    # ---- facts (Modules 2/3/4, gated by Module 7) -------------------
    def store_fact(self, fact: Fact) -> tuple[bool, list[str]]:
        ok, errors = validate_fact(fact)
        if not ok:
            self.record_rejection(fact.category, errors)
            return False, errors
        self._persist_fact(fact)
        return True, []

    @abstractmethod
    def _persist_fact(self, fact: Fact) -> None: ...

    @abstractmethod
    def get_facts(
        self,
        company_id: str,
        category: Optional[str] = None,
        key: Optional[str] = None,
        period: Optional[str] = None,
        status: Optional[str] = FactStatus.ACTIVE.value,
    ) -> list[Fact]: ...

    @abstractmethod
    def get_fact(self, fact_id: str) -> Optional[Fact]: ...

    @abstractmethod
    def supersede_fact(self, old_fact_id: str, new_fact_id: str) -> None: ...

    @abstractmethod
    def record_rejection(self, category: str, errors: list[str]) -> None: ...

    # ---- knowledge graph (Module 6) ---------------------------------
    @abstractmethod
    def upsert_node(self, node: GraphNode) -> None: ...

    @abstractmethod
    def upsert_edge(self, edge: GraphEdge) -> None: ...

    @abstractmethod
    def get_graph(self, node_id: str) -> tuple[list[GraphNode], list[GraphEdge]]: ...

    # ---- change deltas (Module 5) ------------------------------------
    @abstractmethod
    def store_delta(self, delta: ChangeDelta) -> None: ...

    @abstractmethod
    def get_deltas(
        self, company_id: str, from_period: Optional[str] = None, to_period: Optional[str] = None
    ) -> list[ChangeDelta]: ...

    # ---- observability -----------------------------------------------
    @abstractmethod
    def stats(self) -> dict[str, Any]: ...
