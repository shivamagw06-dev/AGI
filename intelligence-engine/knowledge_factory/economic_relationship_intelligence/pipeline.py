"""IERI pipeline — soft KF only. Compiles relationship corpus + graph."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.collectors.soft import (
    soft_relationships_from_priors,
)
from knowledge_factory.economic_relationship_intelligence.commodity_links.catalog import (
    build_commodity_objects,
)
from knowledge_factory.economic_relationship_intelligence.dashboards import relationship_dashboard
from knowledge_factory.economic_relationship_intelligence.fixtures.seeds import (
    curated_relationship_seeds,
)
from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION
from knowledge_factory.economic_relationship_intelligence.transmission.orders import (
    build_transmission_records,
)
from knowledge_factory.economic_relationship_intelligence.validators.gates import (
    validate_corpus,
    validate_relationship,
)

PIPELINE_VERSION = "ieri-pipeline-v2.0.0"


def run_economic_relationship_pipeline() -> dict[str, Any]:
    t0 = time.perf_counter()
    ieri_store.reset()

    # Commodities
    commodities = build_commodity_objects()
    for c in commodities:
        ieri_store.put_commodity(c)
        ieri_store.put_node(
            {
                "node_id": f"commodity:{c['commodity_id']}",
                "kind": "commodity",
                "id": c["commodity_id"],
                "label": c["name"],
            }
        )

    # Relationships: curated seeds + soft priors (dedupe by immutable relationship_id)
    relationships: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for r in list(curated_relationship_seeds()) + soft_relationships_from_priors():
        rid = r.get("relationship_id")
        if not rid or rid in seen_ids:
            continue
        relationships.append(r)
        seen_ids.add(str(rid))

    ready = []
    failed = []
    for r in relationships:
        vr = validate_relationship(r)
        r = dict(r)
        r["validation"] = {
            "status": "pass" if vr["gate_pass"] else "fail",
            "gates": vr["gates"],
            "failures": vr["failures"],
        }
        if vr["gate_pass"]:
            ieri_store.put_relationship(r)
            ready.append(r)
            for ref_key in ("source_ref", "target_ref"):
                ref = r.get(ref_key) or {}
                if ref.get("id"):
                    ieri_store.put_node(
                        {
                            "node_id": f"{ref.get('kind')}:{ref.get('id')}",
                            "kind": ref.get("kind"),
                            "id": ref.get("id"),
                            "label": ref.get("label"),
                        }
                    )
        else:
            failed.append({"relationship_id": r.get("relationship_id"), "failures": vr["failures"]})

    transmissions = build_transmission_records(ready)
    for tx in transmissions:
        ieri_store.put_transmission(tx)

    corpus = validate_corpus(ready)
    dash = relationship_dashboard(ensure=False)
    runtime = round(time.perf_counter() - t0, 2)

    report = {
        "pipeline_version": PIPELINE_VERSION,
        "ieri_version": IERI_VERSION,
        "relationships": len(ready),
        "validation_failures": len(failed),
        "failed_samples": failed[:10],
        "commodities": len(commodities),
        "transmissions": len(transmissions),
        "nodes": ieri_store.node_count(),
        "corpus_ready": corpus.get("institutional_ready"),
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if corpus.get("institutional_ready") and len(failed) == 0 else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
        "planner_changed": False,
        "soft_wire_only": True,
    }
    ieri_store.record_run(report)
    return report
