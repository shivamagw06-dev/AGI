"""Shared office request/response contracts — dict-native for API stability."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence


SCHEMA_EVIDENCE_BLOCK = "office_sdk.evidence_block.v1"
SCHEMA_EVIDENCE_REF = "office_sdk.evidence_reference.v1"
SCHEMA_CONFIDENCE = "office_sdk.confidence_summary.v1"
SCHEMA_PROVENANCE = "office_sdk.provenance_bundle.v1"
SCHEMA_METADATA = "office_sdk.office_metadata.v1"
SCHEMA_SECTION = "office_sdk.office_section.v1"
SCHEMA_REQUEST = "office_sdk.office_request.v1"
SCHEMA_RESPONSE = "office_sdk.office_response.v1"


def evidence_block(
    text: str,
    *,
    module: str,
    evidence_ids: Optional[Sequence[str]] = None,
    confidence: float = 0.0,
    reporting_period: Optional[str] = None,
    tickers: Optional[Sequence[str]] = None,
    kind: str = "narrative",
    extras: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Canonical narrative unit — every office paragraph should use this shape."""
    block: dict[str, Any] = {
        "schema": SCHEMA_EVIDENCE_BLOCK,
        "text": str(text or ""),
        "module": str(module or ""),
        "evidence_ids": [str(x) for x in (evidence_ids or []) if x is not None and str(x).strip()],
        "confidence": float(confidence or 0.0),
        "reporting_period": reporting_period,
        "tickers": [str(t).upper() for t in (tickers or []) if str(t).strip()],
        "kind": kind,
    }
    if extras:
        for k, v in extras.items():
            if k not in block:
                block[k] = v
    return block


def evidence_reference(
    evidence_id: str,
    *,
    module: str,
    confidence: float = 0.0,
    reporting_period: Optional[str] = None,
    ticker: Optional[str] = None,
    source: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_EVIDENCE_REF,
        "evidence_id": str(evidence_id),
        "module": str(module or ""),
        "confidence": float(confidence or 0.0),
        "reporting_period": reporting_period,
        "ticker": ticker.upper() if isinstance(ticker, str) and ticker.strip() else ticker,
        "source": source,
    }


def confidence_summary(
    *,
    mean_confidence: float = 0.0,
    by_module: Optional[Sequence[Mapping[str, Any]]] = None,
    by_company_module: Optional[Sequence[Mapping[str, Any]]] = None,
    ok_count: int = 0,
    total: int = 0,
    extras: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": SCHEMA_CONFIDENCE,
        "mean_confidence": float(mean_confidence or 0.0),
        "by_module": list(by_module or []),
        "by_company_module": list(by_company_module or []),
        "ok_count": int(ok_count),
        "total": int(total),
    }
    if extras:
        out.update(dict(extras))
    return out


def provenance_bundle(
    *,
    blocks: Optional[Sequence[Mapping[str, Any]]] = None,
    references: Optional[Sequence[Mapping[str, Any]]] = None,
    modules_invoked: Optional[Sequence[str]] = None,
    modules_ok: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_PROVENANCE,
        "blocks": [dict(b) for b in (blocks or [])],
        "references": [dict(r) for r in (references or [])],
        "modules_invoked": list(modules_invoked or []),
        "modules_ok": list(modules_ok or []),
    }


def office_metadata(
    *,
    office_id: str,
    workstream_id: str,
    product: str,
    version: str,
    domain: str,
    role: str = "orchestration",
    compares_only: bool = False,
    orchestrates_only: bool = True,
    buy_sell: bool = False,
    valuation: bool = False,
    recalculates: bool = False,
    invents_conclusions: bool = False,
    extras: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "schema": SCHEMA_METADATA,
        "office_id": office_id,
        "workstream_id": workstream_id,
        "product": product,
        "version": version,
        "domain": domain,
        "role": role,
        "orchestrates_only": bool(orchestrates_only),
        "compares_only": bool(compares_only),
        "guardrails": {
            "recalculates": bool(recalculates),
            "invents_conclusions": bool(invents_conclusions),
            "buy_sell": bool(buy_sell),
            "valuation": bool(valuation),
        },
    }
    if extras:
        meta["extras"] = dict(extras)
    return meta


def office_section(
    key: str,
    *,
    title: Optional[str] = None,
    order: int = 0,
    blocks: Optional[Sequence[Mapping[str, Any]]] = None,
    board: Any = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_SECTION,
        "key": key,
        "title": title or key,
        "order": int(order),
        "blocks": [dict(b) for b in (blocks or [])],
        "block_count": len(list(blocks or [])),
        "board": board,
    }


def office_request(
    *,
    office_id: str,
    intent: str = "query",
    tickers: Optional[Sequence[str]] = None,
    question: Optional[str] = None,
    package_type: Optional[str] = None,
    comparison_type: Optional[str] = None,
    modules: Optional[Sequence[str]] = None,
    options: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_REQUEST,
        "office_id": office_id,
        "intent": intent,
        "tickers": [str(t).upper() for t in (tickers or []) if str(t).strip()],
        "question": question,
        "package_type": package_type,
        "comparison_type": comparison_type,
        "modules": list(modules or []),
        "options": dict(options or {}),
    }


def office_response(
    *,
    metadata: Mapping[str, Any],
    request: Optional[Mapping[str, Any]] = None,
    report_type: str,
    sections: Optional[Sequence[Mapping[str, Any]]] = None,
    confidence: Optional[Mapping[str, Any]] = None,
    provenance: Optional[Mapping[str, Any]] = None,
    routing: Optional[Mapping[str, Any]] = None,
    assembly_ms: float = 0.0,
    payload: Optional[Mapping[str, Any]] = None,
    ok: bool = True,
    error: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_RESPONSE,
        "ok": bool(ok),
        "error": error,
        "metadata": dict(metadata),
        "request": dict(request or {}),
        "report_type": report_type,
        "sections": [dict(s) for s in (sections or [])],
        "confidence": dict(confidence or confidence_summary()),
        "provenance": dict(provenance or provenance_bundle()),
        "routing": dict(routing or {}),
        "assembly_ms": round(float(assembly_ms or 0.0), 3),
        "payload": dict(payload or {}),
        "guardrails": dict((metadata or {}).get("guardrails") or {}),
    }


def normalize_block(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Coerce office-local blocks into the shared EvidenceBlock shape."""
    if not isinstance(raw, Mapping):
        return evidence_block(str(raw), module="unknown")
    if raw.get("schema") == SCHEMA_EVIDENCE_BLOCK:
        return dict(raw)
    return evidence_block(
        str(raw.get("text") or ""),
        module=str(raw.get("module") or ""),
        evidence_ids=list(raw.get("evidence_ids") or []),
        confidence=float(raw.get("confidence") or 0.0)
        if isinstance(raw.get("confidence"), (int, float))
        else 0.0,
        reporting_period=raw.get("reporting_period") or raw.get("period"),
        tickers=list(raw.get("tickers") or ([raw["ticker"]] if raw.get("ticker") else [])),
        kind=str(raw.get("kind") or "narrative"),
    )


def normalize_sections(sections: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, sec in enumerate(sections or [], start=1):
        if not isinstance(sec, Mapping):
            continue
        blocks = [normalize_block(b) for b in (sec.get("blocks") or []) if isinstance(b, Mapping) or b]
        out.append(
            office_section(
                str(sec.get("key") or sec.get("title") or f"section_{i}"),
                title=sec.get("title"),
                order=int(sec.get("order") or i),
                blocks=blocks,
                board=sec.get("board"),
            )
        )
    return out


def flatten_blocks(sections: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for sec in sections or []:
        for b in sec.get("blocks") or []:
            if isinstance(b, Mapping):
                blocks.append(normalize_block(b))
    return blocks
