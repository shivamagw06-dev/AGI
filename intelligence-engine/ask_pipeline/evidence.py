"""S06 — Evidence Factory assembly from KF knowledge bag."""

from __future__ import annotations

import time
from typing import Any

from ask_pipeline.store import utc_now


def _envelope(
    pack_type: str,
    *,
    entity: str | None,
    evidence: Any,
    quality: float | None,
    coverage: float | None,
    validation: dict[str, Any] | None,
    provenance: dict[str, Any] | None,
) -> dict[str, Any]:
    now = utc_now()
    prov = provenance or {
        "source": "knowledge_factory",
        "retrieved_at": now,
        "validated_at": now,
        "collector": f"ask_pipeline.evidence.{pack_type}",
        "confidence": quality,
        "derived_from": entity,
        "version": "ask-evidence-v1",
        "fabricated": False,
    }
    found = evidence is not None and evidence != {} and not (
        isinstance(evidence, dict) and evidence.get("unavailable")
    )
    return {
        "pack_type": pack_type,
        "entity": entity,
        "evidence": evidence if found else None,
        "quality": quality if quality is not None else (0.7 if found else 0.0),
        "coverage": coverage if coverage is not None else (0.6 if found else 0.0),
        "provenance": prov,
        "validation": validation
        or {
            "ok": found,
            "insufficient": not found,
            "reason": None if found else "knowledge_unavailable",
        },
        "point_in_time": {"integrity": True, "as_of": now, "lookahead": False},
        "found": found,
        "fabricated": False,
    }


def assemble_evidence(
    knowledge: dict[str, Any],
    *,
    intent: str,
    entities: list[dict[str, Any]],
) -> dict[str, Any]:
    started = time.time()
    bag = (knowledge or {}).get("bag") or {}
    objects = bag.get("objects") or {}
    company_ids = [
        str(e["id"]).upper() for e in entities if e.get("type") == "company" and e.get("id")
    ] or list(((objects.get("company") or {}).get("by_entity") or {}).keys())

    packs: dict[str, Any] = {}
    governance_packs: dict[str, Any] = {}

    # Company packs (+ governance-facing valuation/company slices from KF feed)
    company_packs = {}
    for cid in company_ids:
        row = ((objects.get("company") or {}).get("by_entity") or {}).get(cid) or {}
        feed = row.get("evidence_feed") or {}
        obj = row.get("object") or {}
        pack = _envelope(
            "company",
            entity=cid,
            evidence={
                "object": obj,
                "evidence_feed": feed,
                "company_intelligence": row.get("company_intelligence"),
            },
            quality=(feed or {}).get("quality"),
            coverage=(feed or {}).get("coverage"),
            validation={"ok": bool(row.get("found")), "insufficient": not row.get("found")},
            provenance=(feed or {}).get("provenance") or row.get("provenance"),
        )
        company_packs[cid] = pack
        # Map into govern_answer pack keys without inventing metrics
        kf_pack = None
        try:
            from knowledge_factory.store import repository as store

            kf_pack = store.get_pack(cid)
        except Exception:
            kf_pack = None
        if isinstance(kf_pack, dict) and kf_pack:
            governance_packs.setdefault("valuation", {})
            if governance_packs["valuation"].get("entity") is None:
                governance_packs["valuation"] = {
                    **kf_pack,
                    "entity": cid,
                    "source": "knowledge_factory",
                    "provenance": pack["provenance"],
                }
            governance_packs["knowledge_factory_pack"] = {
                **kf_pack,
                "entity": cid,
                "provenance": pack["provenance"],
            }
        # Soft institutional feed for IEI consumers
        governance_packs.setdefault("knowledge_factory", {})
        governance_packs["knowledge_factory"][cid] = {
            "evidence_feed": feed,
            "object": obj,
            "provenance": pack["provenance"],
        }

    packs["company"] = company_packs

    if "industry" in objects:
        packs["industry"] = {
            cid: _envelope(
                "industry",
                entity=cid,
                evidence=((objects["industry"].get("by_entity") or {}).get(cid)),
                quality=None,
                coverage=None,
                validation=None,
                provenance=(objects["industry"].get("provenance")),
            )
            for cid in company_ids
        }
        governance_packs["industry"] = packs["industry"]

    if "government" in objects:
        packs["government"] = _envelope(
            "government",
            entity=None,
            evidence=(objects["government"].get("payload")),
            quality=None,
            coverage=None,
            validation=None,
            provenance=objects["government"].get("provenance"),
        )
        governance_packs["government"] = packs["government"]

    if "relationships" in objects:
        packs["relationship"] = {
            cid: _envelope(
                "relationship",
                entity=cid,
                evidence=((objects["relationships"].get("by_entity") or {}).get(cid)),
                quality=None,
                coverage=None,
                validation=None,
                provenance=objects["relationships"].get("provenance"),
            )
            for cid in company_ids
        }
        governance_packs["relationships"] = packs["relationship"]

    if "alternative_data" in objects:
        packs["alternative_data"] = {
            cid: _envelope(
                "alternative_data",
                entity=cid,
                evidence=((objects["alternative_data"].get("by_entity") or {}).get(cid)),
                quality=None,
                coverage=None,
                validation=None,
                provenance=objects["alternative_data"].get("provenance"),
            )
            for cid in company_ids
        }
        governance_packs["alternative_data"] = packs["alternative_data"]

    if "expectations" in objects:
        packs["expectation"] = {
            cid: _envelope(
                "expectation",
                entity=cid,
                evidence=((objects["expectations"].get("by_entity") or {}).get(cid)),
                quality=None,
                coverage=None,
                validation=None,
                provenance=objects["expectations"].get("provenance"),
            )
            for cid in company_ids
        }
        governance_packs["expectations"] = packs["expectation"]

    if intent in {"Portfolio", "Risk"} or company_ids:
        try:
            from knowledge_factory.store import repository as store

            book = store.get_object("portfolio", "BOOK")
        except Exception:
            book = None
        packs["portfolio"] = _envelope(
            "portfolio",
            entity="BOOK",
            evidence=book,
            quality=0.7 if book else 0.0,
            coverage=0.5 if book else 0.0,
            validation={"ok": bool(book), "insufficient": not book},
            provenance={
                "source": "knowledge_factory",
                "collector": "portfolio",
                "retrieved_at": utc_now(),
                "validated_at": utc_now(),
                "fabricated": False,
                "version": "ask-evidence-v1",
            },
        )
        if book:
            governance_packs["portfolio_book"] = book

    packs["decision"] = _envelope(
        "decision",
        entity=company_ids[0] if company_ids else None,
        evidence={"intent": intent, "entities": company_ids},
        quality=1.0,
        coverage=1.0,
        validation={"ok": True, "insufficient": False},
        provenance={
            "source": "ask_pipeline",
            "collector": "decision_pack",
            "retrieved_at": utc_now(),
            "validated_at": utc_now(),
            "fabricated": False,
            "version": "ask-evidence-v1",
        },
    )

    # Soft-wire IERE Evidence Packs — structured only; reasoning unchanged.
    iere = (knowledge or {}).get("iere") or {}
    iere_envelope = iere.get("ask_envelope") if isinstance(iere, dict) else None
    if isinstance(iere_envelope, dict) and iere_envelope.get("packs"):
        packs["iere"] = {
            "pack_type": "iere_evidence_packs",
            "entity": company_ids[0] if company_ids else None,
            "evidence": {
                "retrieval_id": iere_envelope.get("retrieval_id"),
                "packs": iere_envelope.get("packs"),
                "top_evidence": iere_envelope.get("top_evidence") or [],
                "citations": iere_envelope.get("citations") or [],
            },
            "quality": 0.85,
            "coverage": 0.8,
            "provenance": iere_envelope.get("provenance")
            or {
                "source": "evidence_retrieval",
                "collector": "iere",
                "retrieved_at": utc_now(),
                "validated_at": utc_now(),
                "fabricated": False,
                "version": "iere-ask-v1",
            },
            "validation": {"ok": True, "insufficient": False},
            "point_in_time": {"integrity": True, "as_of": utc_now(), "lookahead": False},
            "found": True,
            "fabricated": False,
            "pdf_sent_to_reasoning": False,
        }
        governance_packs["iere_evidence"] = packs["iere"]["evidence"]

    # Phase 6.0 — Universal Knowledge Orchestration evidence graph.
    uko = (knowledge or {}).get("universal_knowledge") or {}
    if isinstance(uko, dict) and (uko.get("providers_used") or uko.get("nodes")):
        packs["universal_knowledge"] = {
            "pack_type": "universal_knowledge_graph",
            "entity": company_ids[0] if company_ids else None,
            "evidence": {
                "summary": uko.get("summary"),
                "why": uko.get("why") or [],
                "facts": uko.get("facts") or [],
                "nodes": uko.get("nodes") or [],
                "by_role": uko.get("by_role") or {},
                "attributions": uko.get("attributions") or [],
                "providers_used": uko.get("providers_used") or [],
                "providers_missing": uko.get("providers_missing") or [],
                "coverage": uko.get("coverage") or {},
            },
            "quality": 0.9,
            "coverage": ((uko.get("coverage") or {}).get("coverage_pct") or 0) / 100.0,
            "provenance": {
                "source": "universal_knowledge",
                "collector": "uko",
                "retrieved_at": utc_now(),
                "validated_at": utc_now(),
                "fabricated": False,
                "version": uko.get("version") or "uko-6.0",
            },
            "validation": {
                "ok": bool(uko.get("answerable") or uko.get("providers_used")),
                "insufficient": not bool(uko.get("providers_used")),
            },
            "point_in_time": {"integrity": True, "as_of": utc_now(), "lookahead": False},
            "found": bool(uko.get("providers_used")),
            "fabricated": False,
            "pdf_sent_to_reasoning": False,
        }
        governance_packs["universal_knowledge"] = packs["universal_knowledge"]["evidence"]

    # Coverage summary
    flat = []
    for k, v in packs.items():
        if isinstance(v, dict) and "pack_type" in v:
            flat.append(v)
        elif isinstance(v, dict):
            flat.extend([p for p in v.values() if isinstance(p, dict)])
    found_n = sum(1 for p in flat if p.get("found"))
    coverage = round(found_n / len(flat), 4) if flat else 0.0
    missing_prov = [p.get("pack_type") for p in flat if not (p.get("provenance") or {}).get("source")]

    return {
        "stage": "evidence_assembly",
        "status": "executed",
        "intent": intent,
        "packs": packs,
        "governance_packs": governance_packs,
        "iere_retrieval_id": (iere or {}).get("retrieval_id") if isinstance(iere, dict) else None,
        "primary_engine": (knowledge or {}).get("primary_engine") or "knowledge_factory",
        "coverage": coverage,
        "pack_count": len(flat),
        "packs_found": found_n,
        "missing_provenance": missing_prov,
        "duration_ms": int((time.time() - started) * 1000),
        "fabricated": False,
    }
