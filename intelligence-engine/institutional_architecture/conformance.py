"""Run full AGIB v1.0 architecture conformance suite (RC-01)."""

from __future__ import annotations

from typing import Any

from institutional_architecture.architecture_report import build_report, score_architecture
from institutional_architecture.dependency_rules import (
    build_import_graph,
    check_forbidden_imports,
    layer_isolation_summary,
)
from institutional_architecture.invariants import run_invariant_checks
from institutional_architecture.lineage_validator import (
    validate_canonical_lineage,
    validate_context_propagation_contracts,
    validate_publication_manifest_contract,
    validate_uag_no_direct_recommendations,
)
from institutional_architecture.schema import (
    AGIB_PLATFORM_VERSION,
    AGIB_RELEASE_CANDIDATE,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    RC_PRODUCT,
    RC_VERSION,
    RC_WORKSTREAM_ID,
)


def run_conformance() -> dict[str, Any]:
    """Execute all architectural quality gates."""
    invariants = run_invariant_checks()
    deps = check_forbidden_imports()
    lineage = validate_canonical_lineage()
    publication = validate_publication_manifest_contract()
    uag = validate_uag_no_direct_recommendations()
    contexts = validate_context_propagation_contracts()
    import_graph = build_import_graph()
    layers = layer_isolation_summary()

    sections = {
        "invariants": invariants,
        "dependencies": deps,
        "lineage": lineage,
        "publication": publication,
        "uag": uag,
        "contexts": contexts,
    }
    violations = []
    for name, section in sections.items():
        for v in section.get("violations") or []:
            row = dict(v)
            row.setdefault("section", name)
            violations.append(row)
        # Normalize section-level ok
        if section.get("ok") is False and not section.get("violations"):
            for err in section.get("errors") or []:
                violations.append({"section": name, "message": err})

    ok = all(s.get("ok") is True for s in sections.values())
    score = score_architecture(sections)

    report = build_report(
        ok=ok,
        score=score,
        sections=sections,
        violations=violations,
        import_graph=import_graph,
        layers=layers,
    )
    return {
        "ok": ok,
        "workstream_id": RC_WORKSTREAM_ID,
        "product": RC_PRODUCT,
        "version": RC_VERSION,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "agib_release_candidate": AGIB_RELEASE_CANDIDATE,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "guiding_principle": GUIDING_PRINCIPLE,
        "is_quality_gate": True,
        "is_feature": False,
        "architecture_score": score,
        "violation_count": len(violations),
        "violations": violations,
        "sections": sections,
        "import_graph": import_graph,
        "layers": layers,
        "report": report,
        "adds_intelligence_engines": False,
    }
