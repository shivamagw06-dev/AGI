"""PUB-01 production façades — generate / get / export / Publication Center."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Optional

from institutional_publishing.builder import build_publication
from institutional_publishing.diagnostics import build_diagnostics, publication_center_board
from institutional_publishing import distribution as dist_mod
from institutional_publishing.flags import flags_dict, is_enabled
from institutional_publishing.planner import plan_publication, resolve_type_from_request
from institutional_publishing.publication_registry import (
    catalog,
    reset_registry_for_tests,
    types_by_category,
)
from institutional_publishing.renderer import render, supported_renderers
from institutional_publishing.schema import (
    PUB_PRODUCT,
    PUB_ROLE,
    PUB_SPEC,
    PUB_VERSION,
    PUB_WORKSTREAM_ID,
    PUBLICATION_ENGINE_VERSION,
)
from institutional_publishing.validator import validate_publication
from institutional_publishing.versioning import version_record

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_STORE: dict[str, dict[str, Any]] = {}
_ORDER: list[str] = []


def reset_for_tests() -> None:
    _STORE.clear()
    _ORDER.clear()
    dist_mod.reset_for_tests()
    reset_registry_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PUB_WORKSTREAM_ID,
        "product": PUB_PRODUCT,
        "version": PUB_VERSION,
        "role": PUB_ROLE,
        "llm": False,
        "analyzes": False,
        "generates_recommendations": False,
        "reinterprets_evidence": False,
        "compose_only": True,
        "manifest_is_audit_record": True,
        "publication_engine_version": PUBLICATION_ENGINE_VERSION,
        "publication_types": catalog(),
        "renderers": list(supported_renderers()),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PUB_SPEC,
        "brand": "AGI",
        "phase": 5,
        "stored": len(_STORE),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    board = publication_center_board(list(_STORE.values()))
    return {
        "status": h.get("status"),
        "workstream_id": PUB_WORKSTREAM_ID,
        "product": PUB_PRODUCT,
        "version": PUB_VERSION,
        "llm": False,
        "publication_center": True,
        "compose_only": True,
        **board,
    }


def list_types() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PUB_WORKSTREAM_ID,
        "types": catalog(),
        "by_category": types_by_category(),
        "renderers": list(supported_renderers()),
        "compose_only": True,
    }


def generate(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": PUB_WORKSTREAM_ID}

    t0 = time.perf_counter()
    body = dict(payload or {})
    # PRP-03: Observability middleware — observe only
    try:
        from institutional_observability.production import maybe_begin, maybe_end

        maybe_begin(body, name="pub.generate")
    except Exception:
        pass

    # PRP-02: Security Gateway — authorize before compose (PUB still never analyzes)
    try:
        from institutional_security.production import (
            finalize_with_security,
            maybe_gate_publication,
        )

        denied = maybe_gate_publication(body)
        if denied is not None:
            try:
                from institutional_observability.production import maybe_end

                return maybe_end(body, denied, component="pub.generate")
            except Exception:
                return denied
    except Exception:
        pass

    # IEP-01: reject publication if claim_safe == false or Research Ready == false
    try:
        from institutional_evidence.gates import gate_publishing

        ticker = str(body.get("ticker") or body.get("symbol") or "").upper().strip()
        if ticker:
            iep_pub = gate_publishing(ticker, pack=body.get("research_pack"))
            if iep_pub.get("rejected") or not iep_pub.get("allowed"):
                denied = {
                    "ok": False,
                    "published": False,
                    "rejected": True,
                    "workstream_id": PUB_WORKSTREAM_ID,
                    "iep_gate": iep_pub,
                    "failure_reasons": iep_pub.get("failure_reasons") or [],
                    "message": iep_pub.get("message")
                    or "Publication rejected — institutional evidence incomplete",
                }
                try:
                    from institutional_observability.production import maybe_end

                    return maybe_end(body, denied, component="pub.generate")
                except Exception:
                    return denied
    except Exception:
        pass

    # PRP-01: async publication generation via background job queue
    try:
        from institutional_performance.production import maybe_enqueue_publication

        queued = maybe_enqueue_publication(body)
        if queued is not None:
            try:
                from institutional_security.production import finalize_with_security

                queued = finalize_with_security(queued, body)
            except Exception:
                pass
            try:
                from institutional_observability.production import (
                    maybe_end,
                    record_background_job,
                )

                record_background_job()
                return maybe_end(body, queued, component="pub.generate")
            except Exception:
                return queued
    except Exception:
        pass

    # MPC-01: explicit execution context scopes portfolio — compose still never analyzes
    execution_context = body.get("execution_context") or {}
    if not isinstance(execution_context, dict):
        execution_context = {}
    ptype = resolve_type_from_request(body)
    ticker = str(body.get("ticker") or "").upper()
    portfolio_id = str(
        execution_context.get("portfolio_id")
        or body.get("portfolio_id")
        or body.get("portfolio")
        or "agi-core-equity"
    )
    query = str(body.get("query") or body.get("question") or body.get("q") or "")
    renderer = str(body.get("renderer") or "markdown").lower()
    distribute_to = str(body.get("distribute_to") or body.get("target") or "").lower()
    publication_scope = str(body.get("scope") or execution_context.get("scope") or "").lower()

    plan = plan_publication(
        ptype,
        ticker=ticker,
        portfolio_id=portfolio_id,
        query=query,
    )
    publication = build_publication(plan)
    validation = validate_publication(
        publication,
        renderer=renderer,
        known_ids=set(_STORE.keys()),
    )
    latency = (time.perf_counter() - t0) * 1000.0
    diag = build_diagnostics(publication, latency_ms=latency, validation=validation)
    publication = replace(publication, diagnostics=diag)

    if not validation["ok"]:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": PUB_WORKSTREAM_ID,
            "validation_errors": validation["errors"],
            "gates": validation["gates"],
            "plan": plan.to_dict(),
            "publication": publication.to_dict(),
            "manifest": publication.manifest.to_dict() if publication.manifest else None,
            "analyzes": False,
            "compose_only": True,
        }

    rendered = render(publication, renderer)
    if not rendered.get("ok"):
        failed = publication.to_dict()
        failed["status"] = "failed"
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": PUB_WORKSTREAM_ID,
            "validation_errors": [rendered.get("error") or "render failed"],
            "publication": failed,
            "analyzes": False,
        }

    publication = replace(
        publication,
        renderer_outputs=(renderer,),
        status="generated",
    )
    # Update manifest renderer field via rebuild is heavy; stamp on dict store
    stored = publication.to_dict()
    if stored.get("manifest"):
        stored["manifest"]["renderer"] = renderer
    stored["render"] = {
        "renderer": renderer,
        "content_type": rendered.get("content_type"),
        # Keep artifact for export; large HTML/PDF stub OK for institutional demos
        "artifact": rendered.get("artifact"),
    }
    stored["plan"] = plan.to_dict()
    stored["latency_ms"] = round(latency, 2)
    stored["ok"] = True

    _STORE[publication.publication_id] = stored
    _ORDER.append(publication.publication_id)

    distribution = None
    if distribute_to:
        distribution = dist_mod.distribute(
            stored,
            target=distribute_to,
            renderer=renderer,
            artifact=rendered.get("artifact"),
        )
        if distribution.get("ok"):
            stored["status"] = "exported" if distribute_to in {"export", "archive"} else stored["status"]
            stored["distribution"] = distribution

    # Soft MPC scope (same publication object; different destinations)
    scoped = None
    if publication_scope:
        try:
            from institutional_multi_portfolio.production import distribute_publication as mpc_dist

            scoped = mpc_dist(
                {
                    "publication_id": publication.publication_id,
                    "scope": publication_scope,
                    "portfolio_id": portfolio_id,
                    "client_id": str(
                        execution_context.get("client_id") or body.get("client_id") or ""
                    ),
                    "role_id": str(
                        execution_context.get("role_id") or body.get("role_id") or "portfolio_manager"
                    ),
                    "user_id": str(execution_context.get("user_id") or body.get("user_id") or ""),
                }
            )
            stored["publication_scope"] = scoped
        except Exception:
            scoped = None

    result = {
        "ok": True,
        "workstream_id": PUB_WORKSTREAM_ID,
        "product": PUB_PRODUCT,
        "version": PUB_VERSION,
        "publication": stored,
        "manifest": stored.get("manifest"),
        "plan": plan.to_dict(),
        "render": stored.get("render"),
        "distribution": distribution,
        "publication_scope": scoped,
        "execution_context": execution_context or None,
        "version_record": version_record(stored),
        "analyzes": False,
        "generates_recommendations": False,
        "compose_only": True,
        "latency_ms": round(latency, 2),
    }
    try:
        from institutional_security.production import finalize_with_security

        result = finalize_with_security(result, body)
    except Exception:
        pass
    try:
        from institutional_observability.production import maybe_end, record_publication_duration

        record_publication_duration(latency)
        result = maybe_end(body, result, component="pub.generate")
    except Exception:
        pass
    try:
        from institutional_launch.production import maybe_track_publication

        maybe_track_publication(body, result)
    except Exception:
        pass
    return result


def get_publication(publication_id: str) -> dict[str, Any]:
    pub = _STORE.get(str(publication_id))
    if not pub:
        return {
            "ok": False,
            "error": "publication not found",
            "workstream_id": PUB_WORKSTREAM_ID,
        }
    return {
        "ok": True,
        "workstream_id": PUB_WORKSTREAM_ID,
        "publication": pub,
        "manifest": pub.get("manifest"),
        "version_record": version_record(pub),
        "compose_only": True,
    }


def list_publications(limit: int = 20) -> dict[str, Any]:
    ids = list(reversed(_ORDER[-limit:]))
    rows = []
    for pid in ids:
        pub = _STORE.get(pid) or {}
        rows.append(
            {
                "publication_id": pid,
                "publication_type": pub.get("publication_type"),
                "title": pub.get("title"),
                "generated_at": pub.get("generated_at"),
                "status": pub.get("status"),
                "version": pub.get("version"),
                "lineage_hash": (pub.get("manifest") or {}).get("lineage_hash"),
                "source_count": len(pub.get("source_objects") or []),
            }
        )
    return {
        "ok": True,
        "workstream_id": PUB_WORKSTREAM_ID,
        "publications": rows,
        "count": len(rows),
        "distribution_history": dist_mod.distribution_history(10),
    }


def export_publication(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    pid = str(body.get("publication_id") or body.get("id") or "")
    renderer = str(body.get("renderer") or "markdown").lower()
    target = str(body.get("target") or "export").lower()

    if pid and pid in _STORE:
        pub_dict = _STORE[pid]
        # Re-hydrate minimal publication for renderer if needed
        from institutional_publishing.models import (
            EvidenceRef,
            InstitutionalPublication,
            PublicationManifest,
            SourceObjectRef,
        )

        sources = tuple(
            SourceObjectRef(
                object_type=s.get("object_type") or "",
                object_id=s.get("object_id") or "",
                label=s.get("label") or "",
                provider=s.get("provider") or "",
            )
            for s in (pub_dict.get("source_objects") or [])
        )
        evidence = tuple(
            EvidenceRef(
                evidence_id=e.get("evidence_id") or "",
                label=e.get("label") or "",
                object_ref=e.get("object_ref") or "",
                snippet=e.get("snippet") or "",
            )
            for e in (pub_dict.get("evidence") or [])
        )
        man = pub_dict.get("manifest") or {}
        manifest = PublicationManifest(
            publication_type=str(man.get("publication_type") or pub_dict.get("publication_type") or ""),
            template_version=str(man.get("template_version") or "1.0.0"),
            generated_at=str(man.get("generated_at") or pub_dict.get("generated_at") or ""),
            source_objects=tuple(man.get("source_objects") or ()),
            renderer=renderer,
            lineage_hash=str(man.get("lineage_hash") or ""),
            publication_id=str(man.get("publication_id") or pid),
            template=str(man.get("template") or pub_dict.get("template") or ""),
            engine_version=str(man.get("engine_version") or ""),
        )
        publication = InstitutionalPublication(
            publication_id=pid,
            publication_type=str(pub_dict.get("publication_type") or ""),
            title=str(pub_dict.get("title") or ""),
            generated_at=str(pub_dict.get("generated_at") or ""),
            template=str(pub_dict.get("template") or ""),
            source_objects=sources,
            evidence=evidence,
            lineage=tuple(pub_dict.get("lineage") or ()),
            sections=tuple(pub_dict.get("sections") or ()),
            manifest=manifest,
            body_markdown=str(pub_dict.get("body_markdown") or ""),
            status=str(pub_dict.get("status") or "generated"),
            version=str(pub_dict.get("version") or "1"),
            category=str(pub_dict.get("category") or ""),
        )
    else:
        # Generate then export
        gen = generate({**body, "renderer": renderer})
        if not gen.get("ok"):
            return gen
        pid = gen["publication"]["publication_id"]
        return export_publication(
            {"publication_id": pid, "renderer": renderer, "target": target}
        )

    rendered = render(publication, renderer)
    if not rendered.get("ok"):
        return {
            "ok": False,
            "error": rendered.get("error"),
            "workstream_id": PUB_WORKSTREAM_ID,
        }

    distribution = dist_mod.distribute(
        publication.to_dict(),
        target=target,
        renderer=renderer,
        artifact=rendered.get("artifact"),
    )
    pub_dict = _STORE.get(pid) or publication.to_dict()
    pub_dict["status"] = "exported"
    pub_dict["render"] = {
        "renderer": renderer,
        "content_type": rendered.get("content_type"),
        "artifact": rendered.get("artifact"),
    }
    pub_dict["distribution"] = distribution
    _STORE[pid] = pub_dict

    return {
        "ok": True,
        "workstream_id": PUB_WORKSTREAM_ID,
        "publication_id": pid,
        "renderer": renderer,
        "target": target,
        "artifact": rendered.get("artifact"),
        "manifest": rendered.get("manifest") or pub_dict.get("manifest"),
        "distribution": distribution,
        "version_record": version_record(pub_dict),
        "compose_only": True,
        "authoritative_audit_record": "manifest",
    }
