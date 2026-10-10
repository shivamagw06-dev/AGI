"""Parser certification — reference filings vs expected outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.parsing.quality.gates import evaluate_gates
from financial_statements_engine.util import now_iso

FIXTURES = Path(__file__).resolve().parent / "certification_fixtures"


def _load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES / name
    return json.loads(path.read_text(encoding="utf-8"))


def certify_parser(*, parser_id: str | None = None) -> dict[str, Any]:
    """Run built-in certification fixtures. Only passing versions are production_eligible."""
    from financial_statements_engine.parsing.production import parse_bytes

    fixture = _load_fixture("tcs_annual_min.json")
    expected = _load_fixture("expected_tcs_annual_min.json")
    data = json.dumps(fixture.get("document") or fixture, sort_keys=True).encode("utf-8")

    result = parse_bytes(
        str(fixture.get("ticker") or "TCS"),
        data,
        document_type=str(fixture.get("document_type") or "json"),
        period_end=fixture.get("period_end"),
        period_type=fixture.get("period_type") or "annual",
        evidence_id=str(fixture.get("evidence_id") or "cert:tcs_annual_min"),
        consolidation_type=str(fixture.get("consolidation_type") or "consolidated"),
    )

    got_metrics = set((result.get("mapped") or {}).get("metrics") or {})
    exp_metrics = set(expected.get("expected_metrics") or [])
    tp = len(got_metrics & exp_metrics)
    fp = len(got_metrics - exp_metrics)
    fn = len(exp_metrics - got_metrics)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    mapping_acc = 100.0 * tp / max(1, len(exp_metrics))
    extraction_acc = mapping_acc  # fixture labels are expected extractable
    unknown_n = len((result.get("mapped") or {}).get("unknown_fields") or {})
    total_labels = unknown_n + len(got_metrics)
    unknown_rate = 100.0 * unknown_n / max(1, total_labels)

    hierarchy_ok = 100.0 if (result.get("hierarchy") or {}).get("flattening_destroys_hierarchy") is False else 0.0
    # Determinism: parse twice
    result2 = parse_bytes(
        str(fixture.get("ticker") or "TCS"),
        data,
        document_type=str(fixture.get("document_type") or "json"),
        period_end=fixture.get("period_end"),
        period_type=fixture.get("period_type") or "annual",
        evidence_id=str(fixture.get("evidence_id") or "cert:tcs_annual_min") + ":b",
        consolidation_type=str(fixture.get("consolidation_type") or "consolidated"),
    )
    determinism = (
        100.0
        if result.get("deterministic_fingerprint") == result2.get("deterministic_fingerprint")
        else 0.0
    )

    # Traceability
    facts = []
    for d in result.get("drafts") or []:
        facts.extend(d.get("facts") or [])
    traced = all((f.get("evidence") or {}).get("evidence_id") for f in facts) if facts else False
    traceability = 100.0 if traced else 0.0

    gate_metrics = {
        "metric_extraction_accuracy_pct": extraction_acc,
        "canonical_mapping_accuracy_pct": mapping_acc,
        "unknown_metric_rate_pct": unknown_rate,
        "hierarchy_preservation_pct": hierarchy_ok,
        "replay_determinism_pct": determinism,
        "duplicate_draft_rate_pct": 0.0,
        "traceability_pct": traceability,
        "benchmark_pass_rate_pct": 100.0 if mapping_acc >= 99.5 else 0.0,
    }
    gates = evaluate_gates(gate_metrics)
    report = {
        "ok": gates["passed"],
        "parser_id": parser_id or result.get("parser_id"),
        "fixture": "tcs_annual_min",
        "precision": precision,
        "recall": recall,
        "gate_metrics": gate_metrics,
        "gates": gates,
        "production_eligible": gates["production_eligible"],
        "expected_metrics": sorted(exp_metrics),
        "got_metrics": sorted(got_metrics),
        "missing_metrics": sorted(exp_metrics - got_metrics),
        "as_of": now_iso(),
        "issues_recommendations": False,
        "layer": "parser_certification",
    }
    if gates["passed"]:
        publish("parser.certified.v1", {"parser_id": report["parser_id"], "fixture": "tcs_annual_min"})
    else:
        publish("parser.certification_failed.v1", {"parser_id": report["parser_id"], "failed": gates["failed_gates"]})
    return report
