"""Attach Evidence Intelligence to claims / analyst statements."""

from __future__ import annotations

from typing import Any

from academy.evidence.confidence import score_claim_support
from academy.evidence.live_cases import case_11_jul2026 as case11
from academy.evidence.schema import EIL_VERSION


def load_case(case_id: str = "acs_live_11_jul2026") -> dict[str, Any]:
    if case_id in {case11.CASE_ID, "case_11", "jul2026", "acs_live_11_jul2026"}:
        return case11.pack()
    raise KeyError(f"unknown_evidence_case:{case_id}")


def attach_to_claim(claim: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Enrich one claim with sources, metrics, confidence breakdown, gaps."""
    sources = case.get("sources") or {}
    metrics = case.get("metrics") or {}
    src_ids = claim.get("source_ids") or []
    metric_ids = claim.get("metric_ids") or []

    attached_sources = [sources[s] for s in src_ids if s in sources]
    attached_metrics = [metrics[m] for m in metric_ids if m in metrics]

    evidence_class = claim.get("evidence_class") or "prior"
    is_prior = evidence_class == "prior"
    has_facts = evidence_class in {"fact", "street", "market"} and bool(attached_sources)
    street_named = True
    if evidence_class == "street":
        street_named = any(
            (sources.get(s) or {}).get("source_type") in {"broker", "wire", "filing"}
            and "Street" not in (claim.get("statement") or "")
            for s in src_ids
        ) or bool(attached_sources)

    has_history = bool(claim.get("history_required")) is False or False
    # history counted present only if explicitly marked populated — default missing
    history_populated = bool(claim.get("history_populated"))
    peer_populated = bool(claim.get("peers_populated")) or bool(
        any((metrics.get(m) or {}).get("peer_context") for m in metric_ids)
    )

    conf = score_claim_support(
        has_sourced_facts=has_facts and not is_prior,
        n_sources=len(attached_sources),
        has_history=history_populated,
        has_peers=peer_populated,
        street_named=street_named if evidence_class == "street" else True,
        is_prior_only=is_prior,
    )

    gaps = []
    for h in claim.get("history_required") or []:
        gaps.append({"type": "history", "item": h, "status": "missing"})
    for p in claim.get("peers_required") or []:
        if not peer_populated:
            gaps.append({"type": "peer", "item": p, "status": "missing"})

    return {
        **claim,
        "eil_version": EIL_VERSION,
        "attached_sources": attached_sources,
        "attached_metrics": attached_metrics,
        "confidence": conf["confidence"],
        "confidence_breakdown": conf,
        "epistemic_label": evidence_class,
        "is_evidence": evidence_class in {"fact", "street", "market"} and not is_prior,
        "gaps": gaps,
        "traceability": {
            "publishers": [s.get("publisher") for s in attached_sources],
            "as_of": [s.get("as_of") for s in attached_sources],
            "urls": [s.get("url") for s in attached_sources if s.get("url")],
        },
    }


def enrich_case(case_id: str = "acs_live_11_jul2026") -> dict[str, Any]:
    case = load_case(case_id)
    enriched_claims = [attach_to_claim(c, case) for c in case.get("claims") or []]
    triggers = case.get("decision_triggers") or []

    # Aggregate confidence for case (facts only weighted higher)
    fact_confs = [c["confidence"] for c in enriched_claims if c.get("epistemic_label") == "fact"]
    all_confs = [c["confidence"] for c in enriched_claims]
    return {
        **case,
        "claims": enriched_claims,
        "decision_triggers": triggers,
        "eil_version": EIL_VERSION,
        "summary": {
            "claims": len(enriched_claims),
            "facts": sum(1 for c in enriched_claims if c.get("epistemic_label") == "fact"),
            "priors": sum(1 for c in enriched_claims if c.get("epistemic_label") == "prior"),
            "street_named": sum(1 for c in enriched_claims if c.get("epistemic_label") == "street"),
            "mean_confidence_facts": round(sum(fact_confs) / len(fact_confs), 2) if fact_confs else 0.0,
            "mean_confidence_all": round(sum(all_confs) / len(all_confs), 2) if all_confs else 0.0,
            "open_gaps": sum(len(c.get("gaps") or []) for c in enriched_claims),
            "peer_panel_status": case.get("peer_panel_status"),
            "macro_transmission": case.get("transmission_macro"),
        },
        "institutional_rules": [
            "Never label priors as observed evidence",
            "Name consensus source (Bloomberg/MS/LSEG/internal) — never bare 'Street'",
            "Peer + history gaps must remain visible",
            "Confidence must include Evidence/Historical/Peer/Macro breakdown",
            "Decision triggers: evidence required → timeline → trigger → action",
        ],
    }


def support_statement(
    statement: str,
    *,
    case_id: str = "acs_live_11_jul2026",
    analyst: str | None = None,
) -> dict[str, Any]:
    """Find supporting claims for a free-text statement and return EIL attachments."""
    case = enrich_case(case_id)
    q = statement.lower()
    hits = []
    for c in case["claims"]:
        blob = f"{c.get('statement')} {' '.join(c.get('metric_ids') or [])}".lower()
        score = sum(1 for tok in q.split() if len(tok) > 3 and tok in blob)
        if analyst and c.get("analyst") != analyst:
            score *= 0.5
        if score > 0:
            hits.append((score, c))
    hits.sort(key=lambda x: -x[0])
    return {
        "statement": statement,
        "supports": [h for _, h in hits[:5]],
        "eil_version": EIL_VERSION,
        "case_id": case_id,
        "rule": "If supports empty or only priors — claim is not evidence-backed",
    }
