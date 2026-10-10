"""Replay Guard — deterministic PIT gate before analogs / reasoning."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from temporal_integrity.analog_filter.filter import filter_analogs
from temporal_integrity.document_filter.filter import filter_documents
from temporal_integrity.evidence_filter.filter import filter_evidence
from temporal_integrity.graph_filter.filter import filter_graph
from temporal_integrity.schema import MODULE_CODE, TIRC_VERSION


def _checksum(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def apply_replay_guard(
    *,
    as_of: str | None,
    evidence_graph: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    documents: list[dict[str, Any]] | None = None,
    stage: str = "full",
) -> dict[str, Any]:
    """
    Filter all replay consumers for available_from <= as_of and no future-year surfaces.

    Rejected objects are excluded — never silently substituted with alternate facts.
    When as_of is absent, guard is a no-op (passthrough).
    """
    rejected_all: list[dict[str, Any]] = []
    n_checked = 0
    n_rejected = 0

    eg_out = evidence_graph
    im_out = institutional_memory
    ev_out = evidence
    docs_out = documents

    if as_of:
        if evidence_graph is not None and stage in {"full", "graph", "pre_analog"}:
            g = filter_graph(evidence_graph, as_of=as_of)
            eg_out = g["evidence_graph"]
            n_checked += g["n_checked"]
            n_rejected += g["n_rejected"]
            rejected_all.extend(g["rejected"])

        if institutional_memory is not None and stage in {"full", "analog", "post_analog"}:
            a = filter_analogs(institutional_memory, as_of=as_of)
            im_out = a["institutional_memory"]
            n_checked += a["n_checked"]
            n_rejected += a["n_rejected"]
            rejected_all.extend(a["rejected"])

        if evidence is not None and stage in {"full", "evidence"}:
            e = filter_evidence(evidence, as_of=as_of)
            ev_out = e["evidence"]
            n_checked += e["n_checked"]
            n_rejected += e["n_rejected"]
            rejected_all.extend(e["rejected"])

        if documents is not None and stage in {"full", "documents"}:
            d = filter_documents(documents, as_of=as_of)
            docs_out = d["documents"]
            n_checked += d["n_checked"]
            n_rejected += d["n_rejected"]
            rejected_all.extend(d["rejected"])

    # Deterministic checksum over kept surfaces
    checksum_payload = {
        "as_of": as_of,
        "eg_nodes": (eg_out or {}).get("n_nodes") if isinstance(eg_out, dict) else None,
        "eg_bullets": (eg_out or {}).get("surface_bullets") if isinstance(eg_out, dict) else None,
        "im_ids": (im_out or {}).get("top_memory_ids") if isinstance(im_out, dict) else None,
        "im_bullets": (im_out or {}).get("surface_bullets") if isinstance(im_out, dict) else None,
    }
    checksum = _checksum(checksum_payload)

    report = {
        "module": MODULE_CODE,
        "tirc_version": TIRC_VERSION,
        "stage": stage,
        "as_of": as_of,
        "active": bool(as_of),
        "objects_checked": n_checked,
        "objects_rejected": n_rejected,
        "future_leakage_rejected": n_rejected,
        "rejected_sample": [
            {
                "object_id": (r.get("contract") or {}).get("object_id"),
                "reason": (r.get("contract") or {}).get("reason_if_rejected"),
                "source": (r.get("contract") or {}).get("source"),
            }
            for r in rejected_all[:40]
        ],
        "replay_checksum": checksum,
        "deterministic": True,
        "silent_substitution": False,
        "reasoning_changed": False,
        "knowledge_factory_changed": False,
        "fabricated": False,
    }

    return {
        "evidence_graph": eg_out,
        "institutional_memory": im_out,
        "evidence": ev_out,
        "documents": docs_out,
        "rejected": rejected_all,
        "report": report,
        "tirc_version": TIRC_VERSION,
        "fabricated": False,
    }
