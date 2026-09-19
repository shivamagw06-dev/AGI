"""Knowledge Production Engine (KPE) — aliases: IKF."""

from institutional_knowledge_factory.production import (
    apply_ikf,
    calculate_knowledge_kpis,
    calculate_maturity,
    compile_company,
    compile_universe,
    compute_knowledge_quality,
    evaluate_thesis,
    extract_claims,
    gather_sources,
    get_decision_memory,
    get_graph_pack,
    graph_stats,
    health,
    institutional_review,
    load_iko,
    normalize_source,
    process_evidence,
    record_decision_memory,
    save_iko,
    update_company_dna,
)
from institutional_knowledge_factory.schema import (
    COMPILE_PIPELINE_STEPS,
    EXECUTION_MODES,
    IKF_VERSION,
    KPE_VERSION,
    PIPELINE_STEPS,
)

# Aliases for Architecture Freeze v1.0 naming
apply_kpe = apply_ikf
run_incremental = process_evidence
run_compile = compile_company

__all__ = [
    "COMPILE_PIPELINE_STEPS",
    "EXECUTION_MODES",
    "IKF_VERSION",
    "KPE_VERSION",
    "PIPELINE_STEPS",
    "apply_ikf",
    "apply_kpe",
    "calculate_knowledge_kpis",
    "calculate_maturity",
    "compile_company",
    "compile_universe",
    "compute_knowledge_quality",
    "evaluate_thesis",
    "extract_claims",
    "gather_sources",
    "get_decision_memory",
    "get_graph_pack",
    "graph_stats",
    "health",
    "institutional_review",
    "load_iko",
    "normalize_source",
    "process_evidence",
    "record_decision_memory",
    "run_compile",
    "run_incremental",
    "save_iko",
    "update_company_dna",
]
