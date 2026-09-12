"""In-memory FRE store — documents, chunks, evidence, graph, metrics."""

from __future__ import annotations

from typing import Any

from app.fre.models import FreChunk, FreDocument, FreEvidence, FreMetrics, GraphEdge, GraphNode, utc_now


class FreStore:
    def __init__(self) -> None:
        self.documents: dict[str, FreDocument] = {}
        self.chunks: dict[str, FreChunk] = {}
        self.evidence: dict[str, FreEvidence] = {}
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}
        self.checksum_index: dict[str, str] = {}
        self.metrics = FreMetrics()
        self.audit: list[dict[str, Any]] = []
        self._embed_samples: list[float] = []
        self._search_samples: list[float] = []
        self._retrieval_samples: list[float] = []

    def audit_event(self, action: str, **detail: Any) -> None:
        self.audit.append({"action": action, "at": utc_now().isoformat(), **detail})
        self.audit = self.audit[-200:]

    def put_document(self, doc: FreDocument) -> FreDocument:
        doc.ensure_checksum()
        existing_id = self.checksum_index.get(doc.checksum)
        if existing_id and existing_id in self.documents:
            prev = self.documents[existing_id]
            prev.version += 1
            prev.raw_text = doc.raw_text
            prev.title = doc.title or prev.title
            prev.retrieved_at = utc_now()
            self.audit_event("document_versioned", document_id=prev.document_id, version=prev.version)
            return prev
        self.documents[doc.document_id] = doc
        self.checksum_index[doc.checksum] = doc.document_id
        self.metrics.documents_processed += 1
        self.metrics.last_ingest_at = utc_now().isoformat()
        self.audit_event("document_stored", document_id=doc.document_id)
        return doc

    def put_chunks(self, chunks: list[FreChunk]) -> int:
        for ch in chunks:
            self.chunks[ch.chunk_id] = ch
        self.metrics.chunks_indexed = len(self.chunks)
        return len(chunks)

    def put_evidence(self, items: list[FreEvidence]) -> int:
        for ev in items:
            self.evidence[ev.evidence_id] = ev
        self.metrics.evidence_extracted = len(self.evidence)
        return len(items)

    def put_graph(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        for n in nodes:
            self.nodes[n.node_id] = n
        for e in edges:
            self.edges[e.edge_id] = e
        self.metrics.graph_nodes = len(self.nodes)
        self.metrics.graph_edges = len(self.edges)

    def record_latency(self, *, embed_ms: float | None = None, search_ms: float | None = None, retrieval_ms: float | None = None) -> None:
        if embed_ms is not None:
            self._embed_samples.append(embed_ms)
            self._embed_samples = self._embed_samples[-100:]
            self.metrics.avg_embed_ms = sum(self._embed_samples) / len(self._embed_samples)
        if search_ms is not None:
            self._search_samples.append(search_ms)
            self._search_samples = self._search_samples[-100:]
            self.metrics.avg_search_ms = sum(self._search_samples) / len(self._search_samples)
        if retrieval_ms is not None:
            self._retrieval_samples.append(retrieval_ms)
            self._retrieval_samples = self._retrieval_samples[-100:]
            self.metrics.avg_retrieval_ms = sum(self._retrieval_samples) / len(self._retrieval_samples)

    def snapshot(self) -> dict[str, Any]:
        return {
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "evidence": len(self.evidence),
            "graph_nodes": len(self.nodes),
            "graph_edges": len(self.edges),
            "unique_checksums": len(self.checksum_index),
        }

    def documents_for_company(self, key: str) -> list[FreDocument]:
        k = (key or "").lower()
        return [
            d
            for d in self.documents.values()
            if k
            and (
                k in (d.company or "").lower()
                or k == (d.symbol or "").lower()
                or k in (d.title or "").lower()
            )
        ]

    def evidence_for_company(self, key: str) -> list[FreEvidence]:
        k = (key or "").lower()
        return [
            e
            for e in self.evidence.values()
            if k and (k in (e.company or "").lower() or k == (e.symbol or "").lower())
        ]
