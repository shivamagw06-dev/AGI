"""Company knowledge health from evidence / conflicts / confidence."""

from __future__ import annotations

from app.eve.confidence import freshness_from_timestamp
from app.eve.models import CompanyKnowledgeHealth
from app.eve.store import EveStore


def compute_company_health(store: EveStore, company_id: str, *, symbol: str = "") -> CompanyKnowledgeHealth:
    evidence = store.active_evidence(company_id=company_id)
    conflicts = [c for c in store.conflicts.values() if c.company_id == company_id and c.status == "open"]
    verified = [e for e in evidence if e.verification_status == "verified"]
    unverified = [e for e in evidence if e.verification_status in {"unverified", "pending", "stale"}]
    confs = [float(e.confidence) for e in evidence]
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    fresh_vals = [freshness_from_timestamp(e.last_confirmed_at or e.created_at) for e in evidence]
    freshness = sum(fresh_vals) / len(fresh_vals) if fresh_vals else 0.0
    # Coverage: diversity of fact keys
    keys = {e.fact_key for e in evidence}
    coverage = min(1.0, len(keys) / 8.0)
    verification_pct = (len(verified) / len(evidence)) if evidence else 0.0
    trust = round(
        100
        * (
            0.30 * avg_conf
            + 0.20 * verification_pct
            + 0.15 * freshness
            + 0.15 * coverage
            + 0.20 * (1.0 - min(1.0, len(conflicts) / 5.0))
        ),
        2,
    )
    health = CompanyKnowledgeHealth(
        company_id=company_id,
        company_symbol=symbol,
        evidence_count=len(evidence),
        verification_pct=round(verification_pct, 4),
        unverified_facts=len(unverified),
        conflicts=len(conflicts),
        average_confidence=round(avg_conf, 4),
        freshness=round(freshness, 4),
        coverage=round(coverage, 4),
        trust_score=trust,
    )
    store.health[company_id] = health
    return health


def recompute_all_health(store: EveStore, company_symbols: dict[str, str] | None = None) -> list[CompanyKnowledgeHealth]:
    company_symbols = company_symbols or {}
    ids = {e.company_id for e in store.active_evidence() if e.company_id}
    return [compute_company_health(store, cid, symbol=company_symbols.get(cid, "")) for cid in sorted(ids)]
