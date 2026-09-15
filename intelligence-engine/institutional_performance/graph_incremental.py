"""Incremental graph update soft-path (PRP-01) — reasons over KG-01, does not rebuild."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from institutional_performance.cache import graph_cache
from institutional_performance.metrics import record_latency
from institutional_performance.schema import PRP_01_ID

logger = logging.getLogger(__name__)


def apply_incremental_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Soft incremental update:
    - Invalidates affected entity/edge cache keys
    - Optionally refreshes a narrow neighbourhood via KG-01 when available
    - Never owns a second graph; KG-01 remains SoR
    """
    t0 = time.perf_counter()
    entity_ids: List[str] = list(payload.get("entity_ids") or [])
    edge_ids: List[str] = list(payload.get("edge_ids") or [])
    reason = str(payload.get("reason") or "incremental")

    invalidated = 0
    gc = graph_cache()
    for eid in entity_ids:
        if gc.delete(f"entity:{eid}"):
            invalidated += 1
        if gc.delete(f"neighbourhood:{eid}"):
            invalidated += 1
    for edge in edge_ids:
        if gc.delete(f"edge:{edge}"):
            invalidated += 1

    refreshed: List[Dict[str, Any]] = []
    if entity_ids:
        refreshed = _soft_refresh_neighbourhood(entity_ids[:20])

    elapsed = time.perf_counter() - t0
    record_latency("graph_incremental", elapsed)
    return {
        "id": PRP_01_ID,
        "mode": "incremental",
        "reason": reason,
        "entity_ids": entity_ids,
        "edge_ids": edge_ids,
        "keys_invalidated": invalidated,
        "neighbourhoods_refreshed": len(refreshed),
        "refreshed": refreshed,
        "elapsed_seconds": round(elapsed, 4),
        "graph_sor": "KG-01 institutional_graph",
        "note": "Incremental path; full rebuild not required for hot entity updates.",
    }


def _soft_refresh_neighbourhood(entity_ids: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from institutional_graph import get_graph  # type: ignore

        graph = get_graph()
        for eid in entity_ids:
            try:
                if hasattr(graph, "neighbourhood"):
                    nh = graph.neighbourhood(eid)
                elif hasattr(graph, "neighbors"):
                    nh = graph.neighbors(eid)
                else:
                    nh = {"entity_id": eid, "edges": []}
                snap = nh if isinstance(nh, dict) else {"entity_id": eid, "data": nh}
                graph_cache().set(f"neighbourhood:{eid}", snap, ttl_seconds=120)
                out.append({"entity_id": eid, "cached": True})
            except Exception as exc:  # noqa: BLE001
                logger.debug("PRP-01 neighbourhood refresh skip %s: %s", eid, exc)
                out.append({"entity_id": eid, "cached": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.debug("PRP-01 KG soft refresh unavailable: %s", exc)
        for eid in entity_ids:
            stub = {"entity_id": eid, "edges": [], "stub": True}
            graph_cache().set(f"neighbourhood:{eid}", stub, ttl_seconds=60)
            out.append({"entity_id": eid, "cached": True, "stub": True})
    return out


def get_cached_neighbourhood(entity_id: str) -> Optional[Dict[str, Any]]:
    return graph_cache().get(f"neighbourhood:{entity_id}")
