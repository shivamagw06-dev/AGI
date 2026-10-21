"""IADI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from knowledge_factory.alternative_data_intelligence import store as iadi_store
from knowledge_factory.alternative_data_intelligence.dashboards import alternative_data_dashboard
from knowledge_factory.alternative_data_intelligence.links.connect import (
    company_dataset_view,
    industry_dataset_view,
    soft_relationship_links,
)
from knowledge_factory.alternative_data_intelligence.pipeline import run_alternative_data_pipeline
from knowledge_factory.alternative_data_intelligence.registry.catalog import registry_snapshot
from knowledge_factory.alternative_data_intelligence.schema import (
    FREEZE_LOCKS,
    IADI_VERSION,
    LAYER,
    PHASE_1_DATASETS,
    PROGRAMME,
)
from knowledge_factory.alternative_data_intelligence.trends.compute import compute_trends


def _ensure() -> None:
    if iadi_store.dataset_count() == 0:
        run_alternative_data_pipeline()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": IADI_VERSION,
        "architecture_status": "SOFT_ALTERNATIVE_DATA_INTELLIGENCE",
        "delivery_phase": "phase_1_high_signal",
        "phase_1_datasets": list(PHASE_1_DATASETS),
        "not_a_reasoning_engine": True,
        "not_a_prediction_engine": True,
        "never_fabricate": True,
        "never_interpolate_unsupported": True,
        "point_in_time_integrity": True,
        "soft_wire_only": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/alternative-data",
        "modules": [
            "Dataset Registry",
            "Observations",
            "Trend Intelligence",
            "Company Links",
            "Industry Links",
            "Historical Replay",
            "Morning Board",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return alternative_data_dashboard(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_alternative_data_pipeline()


def registry() -> dict[str, Any]:
    return registry_snapshot()


def get_dataset(name: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    did = str(name or "").lower().replace(" ", "_").replace("-", "_")
    ds = iadi_store.get_dataset(did)
    if not ds:
        # try name match
        for row in iadi_store.list_datasets():
            if did in str(row.get("name") or "").lower().replace(" ", "_"):
                ds = row
                did = row["dataset_id"]
                break
    obs = iadi_store.list_observations(dataset_id=did, as_of=as_of) if did else []
    links = soft_relationship_links(did) if did else {}
    return {
        "dataset": ds,
        "observations": obs,
        "n_observations": len(obs),
        "links": links,
        "as_of": as_of,
        "version": IADI_VERSION,
        "fabricated": False,
    }


def company(ticker: str) -> dict[str, Any]:
    _ensure()
    return company_dataset_view(ticker)


def industry(name: str) -> dict[str, Any]:
    _ensure()
    return industry_dataset_view(name)


def trends(*, dataset: str | None = None, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    if dataset:
        did = str(dataset).lower().replace(" ", "_").replace("-", "_")
        obs = iadi_store.list_observations(dataset_id=did, as_of=as_of)
        return {
            "dataset_id": did,
            "trends": compute_trends(obs),
            "as_of": as_of,
            "version": IADI_VERSION,
            "fabricated": False,
            "prediction": False,
        }
    out = []
    for ds in iadi_store.list_datasets():
        out.append(
            {
                "dataset_id": ds.get("dataset_id"),
                "domain": ds.get("domain"),
                "trends": ds.get("trends") or compute_trends(
                    iadi_store.list_observations(dataset_id=ds.get("dataset_id"), as_of=as_of)
                ),
            }
        )
    return {"n": len(out), "datasets": out, "as_of": as_of, "version": IADI_VERSION, "prediction": False}


def search(q: str = "", *, limit: int = 25) -> dict[str, Any]:
    _ensure()
    query = str(q or "").strip().lower()
    hits = []
    for ds in iadi_store.list_datasets():
        blob = " ".join(
            [
                str(ds.get("dataset_id") or ""),
                str(ds.get("name") or ""),
                str(ds.get("domain") or ""),
                str(ds.get("provider") or ""),
                " ".join(str(x) for x in (ds.get("company_links") or [])),
                " ".join(str(x) for x in (ds.get("industry_links") or [])),
            ]
        ).lower()
        if not query or query in blob:
            hits.append(
                {
                    "dataset_id": ds.get("dataset_id"),
                    "name": ds.get("name"),
                    "domain": ds.get("domain"),
                    "provider": ds.get("provider"),
                    "latest_available": ds.get("latest_available"),
                    "trend": (ds.get("trends") or {}).get("trend"),
                    "momentum": (ds.get("trends") or {}).get("momentum"),
                    "institutional_ready": ds.get("institutional_ready"),
                }
            )
        if len(hits) >= limit:
            break
    return {"q": q, "n": len(hits), "results": hits, "version": IADI_VERSION}


def replay(*, as_of: str, dataset: str | None = None) -> dict[str, Any]:
    """Point-in-time replay — available_from <= as_of only. No future leakage."""
    _ensure()
    if dataset:
        did = str(dataset).lower().replace(" ", "_").replace("-", "_")
        obs = iadi_store.list_observations(dataset_id=did, as_of=as_of)
        datasets = [iadi_store.get_dataset(did)] if iadi_store.get_dataset(did) else []
    else:
        obs = iadi_store.list_observations(as_of=as_of)
        # recompute which datasets have any obs as-of
        dids = sorted({o.get("dataset_id") for o in obs})
        datasets = [iadi_store.get_dataset(d) for d in dids if d]

    # Verify no leakage
    leaked = [o for o in obs if str(o.get("available_from") or "") > as_of]
    return {
        "as_of": as_of,
        "dataset": dataset,
        "n_observations": len(obs),
        "n_datasets": len([d for d in datasets if d]),
        "observations": [
            {
                "observation_id": o.get("observation_id"),
                "dataset_id": o.get("dataset_id"),
                "date": o.get("date"),
                "available_from": o.get("available_from"),
                "value": (o.get("observation") or {}).get("value"),
            }
            for o in obs
        ],
        "trends_as_of": compute_trends(obs) if dataset else None,
        "future_leak": len(leaked) > 0,
        "leaked_count": len(leaked),
        "version": IADI_VERSION,
        "fabricated": False,
    }


def beneficiaries(dataset: str) -> dict[str, Any]:
    """Companies/industries linked to a dataset — knowledge links only, not predictions."""
    _ensure()
    did = str(dataset or "").lower().replace(" ", "_").replace("-", "_")
    ds = iadi_store.get_dataset(did)
    if not ds:
        return {"dataset_id": did, "error": "unknown_dataset", "version": IADI_VERSION}
    trends = ds.get("trends") or {}
    return {
        "dataset_id": did,
        "name": ds.get("name"),
        "observed_trend": trends.get("trend"),
        "observed_momentum": trends.get("momentum"),
        "linked_companies": ds.get("company_links") or [],
        "linked_industries": ds.get("industry_links") or [],
        "linked_macros": ds.get("macro_links") or [],
        "government_links": ds.get("government_links") or [],
        "economic_relationship_links": soft_relationship_links(did).get("economic_relationship_links"),
        "version": IADI_VERSION,
        "fabricated": False,
        "prediction": False,
        "note": "Linked entities from registry/IERI only — not earnings forecasts.",
    }
