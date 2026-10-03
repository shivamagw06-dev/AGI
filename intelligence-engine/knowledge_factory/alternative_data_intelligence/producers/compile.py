"""Compile Alternative Data objects — datasets + observations + trends."""

from __future__ import annotations

from typing import Any

from knowledge_factory.alternative_data_intelligence import store as iadi_store
from knowledge_factory.alternative_data_intelligence.collectors.soft import collect_phase1_bundle
from knowledge_factory.alternative_data_intelligence.objects.dataset import build_dataset
from knowledge_factory.alternative_data_intelligence.schema import PHASE_1_DATASETS
from knowledge_factory.alternative_data_intelligence.trends.compute import compute_trends
from knowledge_factory.alternative_data_intelligence.validators.gates import (
    validate_corpus,
    validate_dataset,
    validate_observation,
)


def compile_alternative_data(*, persist: bool = True) -> dict[str, Any]:
    bundle = collect_phase1_bundle()
    registry = bundle["datasets"]
    observations = bundle["observations"]

    ready_obs: list[dict[str, Any]] = []
    failed_obs: list[dict[str, Any]] = []
    for o in observations:
        vr = validate_observation(o)
        o = dict(o)
        o["validation"] = {
            "status": "pass" if vr["gate_pass"] else "fail",
            "gates": vr["gates"],
            "failures": vr["failures"],
        }
        if vr["gate_pass"]:
            if persist:
                iadi_store.put_observation(o)
            ready_obs.append(o)
        else:
            failed_obs.append({"observation_id": o.get("observation_id"), "failures": vr["failures"]})

    datasets_out = []
    failed_ds = []
    for did in PHASE_1_DATASETS:
        meta = registry.get(did) or {}
        ds_obs = [o for o in ready_obs if o.get("dataset_id") == did]
        dates = [o.get("date") for o in ds_obs if o.get("date")]
        trends = compute_trends(ds_obs)
        obj = build_dataset(
            dataset_id=did,
            name=str(meta.get("name") or did),
            provider=str(meta.get("provider") or "UNKNOWN"),
            description=str(meta.get("description") or ""),
            frequency=str(meta.get("frequency") or "monthly"),
            coverage=str(meta.get("coverage") or "india"),
            first_available=min(dates) if dates else None,
            latest_available=max(dates) if dates else None,
            confidence=float(meta.get("confidence") or 0.85),
            source=str(meta.get("source_priority") or "government_open_data"),
            company_links=list(meta.get("company_links") or []),
            industry_links=list(meta.get("industry_links") or []),
            sector_links=list(meta.get("sector_links") or []),
            macro_links=list(meta.get("macro_links") or []),
            government_links=list(meta.get("government_links") or []),
            domain=str(meta.get("domain") or ""),
            unit=str(meta.get("unit") or ""),
            notes=meta.get("notes"),
            observation_count=len(ds_obs),
            trends=trends,
        )
        vr = validate_dataset(obj, observations=ds_obs)
        obj["validation"] = {
            "status": "pass" if vr["gate_pass"] else "fail",
            "gates": vr["gates"],
            "failures": vr["failures"],
        }
        obj["institutional_ready"] = vr["gate_pass"]
        if persist:
            iadi_store.put_dataset(obj)
        if vr["gate_pass"]:
            datasets_out.append(obj)
        else:
            failed_ds.append({"dataset_id": did, "failures": vr["failures"]})

    corpus = validate_corpus(ready_obs)
    return {
        "datasets": datasets_out,
        "dataset_count": len(datasets_out),
        "observation_count": len(ready_obs),
        "failed_observations": len(failed_obs),
        "failed_datasets": failed_ds,
        "phase_1_complete": len(datasets_out) == len(PHASE_1_DATASETS),
        "corpus_ready": corpus.get("institutional_ready"),
        "institutional_ready": corpus.get("institutional_ready") and len(failed_ds) == 0,
        "fabricated": False,
    }
