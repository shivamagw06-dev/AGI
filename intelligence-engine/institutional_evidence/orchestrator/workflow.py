"""Research Orchestrator — user asks → registry → ingest/publish → pack → research.

User never manually triggers ingestion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def orchestrate_company_research(
    ticker: str,
    *,
    generate_research: bool = False,
    force_ingest: bool = False,
) -> Dict[str, Any]:
    from ..acquisition.collector import acquire_company_documents
    from ..registry.store import register_documents
    from ..canonical.statements import build_canonical_statements
    from ..company_memory_bridge.bridge import build_company_memory_view
    from ..research_pack.builder import build_institutional_research_pack
    from ..flags import iep_flags

    t = str(ticker or "").upper().strip()
    flags = iep_flags()
    steps: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. Check registry
    acq = acquire_company_documents(t, trigger_ingest=False)
    reg = register_documents(acq)
    steps.append({"step": "check_registry", "evidence_count": reg.get("evidence_count")})

    # 2. Statements published?
    canonical = build_canonical_statements(t)
    published = bool(canonical.get("published") and not canonical.get("zero_periods"))
    steps.append(
        {
            "step": "statements_published",
            "published": published,
            "period_count": canonical.get("period_count") or 0,
        }
    )

    # 3–4. If not, run ingest + publish (automatic)
    if (not published and flags.get("auto_ingest_on_ask")) or force_ingest:
        try:
            from financial_statements_engine.production import run_ingest, run_publish  # type: ignore

            ingest_res = run_ingest(t, force=force_ingest)
            steps.append({"step": "run_ingest", "ok": True, "result_keys": list((ingest_res or {}).keys())[:10]})
            pub_res = run_publish(t)
            steps.append({"step": "run_publish", "ok": True, "result_keys": list((pub_res or {}).keys())[:10]})
            canonical = build_canonical_statements(t, trigger_publish=False)
            published = bool(canonical.get("published") and not canonical.get("zero_periods"))
        except Exception as exc:
            steps.append({"step": "run_ingest_publish", "ok": False, "error": str(exc)})

    # 5. Re-acquire after ingest
    acq = acquire_company_documents(t, trigger_ingest=False)
    reg = register_documents(acq)
    steps.append({"step": "run_validation_prep", "evidence_count": reg.get("evidence_count")})

    # 6. Rebuild company memory
    memory = build_company_memory_view(t, canonical=canonical, registry=reg)
    steps.append({"step": "rebuild_company_memory", "slot_coverage": memory.get("slot_coverage")})

    # 7. Recompute Financial Intelligence (soft)
    fi: Dict[str, Any] = {}
    try:
        from financial_intelligence.production import get_financial_intelligence  # type: ignore

        fi = get_financial_intelligence(t) or {}
        steps.append({"step": "recompute_financial_intelligence", "ok": True})
    except Exception as exc:
        steps.append({"step": "recompute_financial_intelligence", "ok": False, "error": str(exc)})

    # 8. Build Research Pack
    pack = build_institutional_research_pack(t, auto_acquire=True)
    steps.append(
        {
            "step": "build_research_pack",
            "claim_safe": pack.get("claim_safe"),
            "research_ready": pack.get("research_ready"),
            "score": (pack.get("research_readiness") or {}).get("score"),
        }
    )

    # 9. Generate research only if claim_safe
    research: Dict[str, Any] = {"generated": False, "blocked": True}
    if generate_research:
        if pack.get("claim_safe") and pack.get("research_ready"):
            try:
                from institutional_research_writer.production import write_research_note  # type: ignore

                note = write_research_note(t, research_pack=pack)
                research = {"generated": True, "blocked": False, "note": note}
                steps.append({"step": "generate_research", "ok": True})
            except Exception as exc:
                # Soft: return pack-gated stub
                research = {
                    "generated": False,
                    "blocked": False,
                    "stub": True,
                    "message": "Writer unavailable; pack is claim_safe — deferred generation",
                    "error": str(exc),
                }
                steps.append({"step": "generate_research", "ok": False, "error": str(exc)})
        else:
            research = {
                "generated": False,
                "blocked": True,
                "reason": "ResearchPack.claim_safe != true or not Research Ready",
                "failures": (pack.get("validation") or {}).get("failures") or pack.get("missing_components"),
                "evidence_unavailable": "Evidence unavailable.",
            }
            steps.append({"step": "generate_research", "blocked": True})

    return {
        "ok": True,
        "ticker": t,
        "orchestrated_at": now,
        "steps": steps,
        "statements_published": published,
        "financial_intelligence": fi if isinstance(fi, dict) else {},
        "research_pack": pack,
        "research": research,
        "claim_safe": pack.get("claim_safe"),
        "research_ready": pack.get("research_ready"),
        "publication_allowed": bool(pack.get("claim_safe") and pack.get("research_ready")),
        "rule": "User never manually triggers ingestion — orchestrator owns the workflow",
    }
