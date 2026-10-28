"""Assemble IRP blocks from collected FIRE outputs — merge/dedupe only; never re-score."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def _as_list(x: Any) -> List[Any]:
    if isinstance(x, list):
        return x
    return []


def _period(payload: Dict[str, Any]) -> Optional[str]:
    for k in ("period", "reporting_period", "as_of", "asOf"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    for k in ("period", "reporting_period", "as_of"):
        v = meta.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _confidence(payload: Dict[str, Any], default: float = 0.0) -> float:
    for k in ("confidence", "overall_confidence", "mean_confidence"):
        v = payload.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    v = meta.get("confidence")
    if isinstance(v, (int, float)):
        return float(v)
    return float(default)


def evidence_ids_from_payload(module: str, payload: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    seen: Set[str] = set()

    def add(eid: Any) -> None:
        if eid is None:
            return
        s = str(eid).strip()
        if not s or s in seen:
            return
        seen.add(s)
        ids.append(s)

    for key in ("evidence_ids", "evidenceIds", "references"):
        for item in _as_list(payload.get(key)):
            if isinstance(item, dict):
                add(item.get("id") or item.get("evidence_id") or item.get("ref"))
            else:
                add(item)

    for key in (
        "trends",
        "relationships",
        "facts",
        "claims",
        "assessments",
        "objectives",
        "pillars",
        "blocks",
        "items",
        "findings",
    ):
        for item in _as_list(payload.get(key)):
            if not isinstance(item, dict):
                continue
            add(item.get("id") or item.get("evidence_id") or item.get("trend_id") or item.get("objective_id"))
            for eid in _as_list(item.get("evidence_ids")):
                add(eid)

    if not ids and payload:
        # Stable provenance handle even when module has no explicit IDs
        add(f"{module}:{payload.get('ticker') or 'unknown'}")
    return ids


def make_block(
    *,
    text: str,
    module: str,
    evidence_ids: List[str],
    confidence: float,
    reporting_period: Optional[str] = None,
    kind: str = "narrative",
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a provenance block via Office SDK EvidenceBlock (soft shared contract)."""
    try:
        from office_sdk.contracts import evidence_block

        return evidence_block(
            text,
            module=module,
            evidence_ids=evidence_ids,
            confidence=confidence,
            reporting_period=reporting_period,
            tickers=tickers,
            kind=kind,
        )
    except Exception:  # noqa: BLE001 — never break IO if SDK unavailable
        return {
            "text": text,
            "module": module,
            "evidence_ids": list(evidence_ids),
            "confidence": float(confidence),
            "reporting_period": reporting_period,
            "kind": kind,
            "tickers": list(tickers or []),
        }


def _dedupe_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate paragraphs by (module, normalized text, evidence signature)."""
    out: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for b in blocks:
        if not isinstance(b, dict):
            continue
        text = " ".join(str(b.get("text") or "").split()).strip().lower()
        if not text:
            continue
        mod = str(b.get("module") or "")
        eids = ",".join(sorted(str(x) for x in _as_list(b.get("evidence_ids"))))
        key = (mod, text, eids)
        if key in seen:
            continue
        seen.add(key)
        out.append(b)
    return out


def _summarize_fire01(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    period = _period(payload)
    conf = _confidence(payload, 0.5)
    eids = evidence_ids_from_payload("FIRE-01", payload)
    trends = _as_list(payload.get("trends") or payload.get("items") or payload.get("findings"))
    if not trends and payload.get("summary"):
        blocks.append(
            make_block(
                text=str(payload["summary"]),
                module="FIRE-01",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
        return blocks
    for t in trends[:12]:
        if not isinstance(t, dict):
            continue
        metric = t.get("metric") or t.get("name") or t.get("series") or "metric"
        direction = t.get("direction") or t.get("trend") or t.get("label") or "observed"
        text = f"{metric}: {direction}"
        if t.get("note"):
            text = f"{text} — {t['note']}"
        te = _as_list(t.get("evidence_ids")) or eids
        tc = t.get("confidence")
        blocks.append(
            make_block(
                text=text,
                module="FIRE-01",
                evidence_ids=[str(x) for x in te] if te else eids,
                confidence=float(tc) if isinstance(tc, (int, float)) else conf,
                reporting_period=period or _period(t),
            )
        )
    if not blocks:
        blocks.append(
            make_block(
                text="FIRE-01 financial trends available; see evidence references.",
                module="FIRE-01",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    return blocks


def _summarize_fire02(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    period = _period(payload)
    conf = _confidence(payload, 0.5)
    eids = evidence_ids_from_payload("FIRE-02", payload)
    rels = _as_list(payload.get("relationships") or payload.get("items") or payload.get("findings"))
    for r in rels[:12]:
        if not isinstance(r, dict):
            continue
        name = r.get("name") or r.get("relationship") or r.get("pair") or "relationship"
        status = r.get("status") or r.get("label") or r.get("assessment") or "observed"
        text = f"{name}: {status}"
        te = _as_list(r.get("evidence_ids")) or eids
        tc = r.get("confidence")
        blocks.append(
            make_block(
                text=text,
                module="FIRE-02",
                evidence_ids=[str(x) for x in te] if te else eids,
                confidence=float(tc) if isinstance(tc, (int, float)) else conf,
                reporting_period=period or _period(r),
            )
        )
    if not blocks and payload.get("summary"):
        blocks.append(
            make_block(
                text=str(payload["summary"]),
                module="FIRE-02",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    if not blocks:
        blocks.append(
            make_block(
                text="FIRE-02 financial relationships available; see evidence references.",
                module="FIRE-02",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    return blocks


def _summarize_fire03(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    period = _period(payload)
    conf = _confidence(payload, 0.5)
    eids = evidence_ids_from_payload("FIRE-03", payload)
    facts = _as_list(payload.get("facts") or payload.get("business_facts") or payload.get("items"))
    for f in facts[:12]:
        if not isinstance(f, dict):
            continue
        text = str(f.get("text") or f.get("statement") or f.get("fact") or f.get("summary") or "").strip()
        if not text:
            continue
        te = _as_list(f.get("evidence_ids")) or ([f.get("id")] if f.get("id") else eids)
        tc = f.get("confidence")
        blocks.append(
            make_block(
                text=text,
                module="FIRE-03",
                evidence_ids=[str(x) for x in te if x],
                confidence=float(tc) if isinstance(tc, (int, float)) else conf,
                reporting_period=period or _period(f),
            )
        )
    if not blocks and payload.get("summary"):
        blocks.append(
            make_block(
                text=str(payload["summary"]),
                module="FIRE-03",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    if not blocks:
        blocks.append(
            make_block(
                text="FIRE-03 business profile / facts available; see evidence references.",
                module="FIRE-03",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    return blocks


def _summarize_fire04(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    period = _period(payload)
    conf = _confidence(payload, 0.5)
    eids = evidence_ids_from_payload("FIRE-04", payload)
    assessments = _as_list(
        payload.get("assessments") or payload.get("claims") or payload.get("items") or payload.get("findings")
    )
    for a in assessments[:12]:
        if not isinstance(a, dict):
            continue
        claim = a.get("claim") or a.get("statement") or a.get("text") or a.get("summary") or "claim"
        status = a.get("status") or a.get("consistency") or a.get("label") or "assessed"
        text = f"{claim}: {status}"
        te = _as_list(a.get("evidence_ids")) or eids
        tc = a.get("confidence")
        blocks.append(
            make_block(
                text=text,
                module="FIRE-04",
                evidence_ids=[str(x) for x in te] if te else eids,
                confidence=float(tc) if isinstance(tc, (int, float)) else conf,
                reporting_period=period or _period(a),
            )
        )
    if not blocks and payload.get("summary"):
        blocks.append(
            make_block(
                text=str(payload["summary"]),
                module="FIRE-04",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    if not blocks:
        blocks.append(
            make_block(
                text="FIRE-04 evidence consistency available; see evidence references.",
                module="FIRE-04",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    return blocks


def _summarize_fire05(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    period = _period(payload)
    conf = _confidence(payload, 0.5)
    eids = evidence_ids_from_payload("FIRE-05", payload)
    objs = _as_list(payload.get("objectives") or payload.get("assessments") or payload.get("items"))
    for o in objs[:12]:
        if not isinstance(o, dict):
            continue
        title = o.get("title") or o.get("objective") or o.get("text") or o.get("statement") or "objective"
        status = o.get("status") or o.get("execution_status") or o.get("label") or "assessed"
        text = f"{title}: {status}"
        te = _as_list(o.get("evidence_ids")) or ([o.get("objective_id") or o.get("id")] if (o.get("objective_id") or o.get("id")) else eids)
        tc = o.get("confidence")
        blocks.append(
            make_block(
                text=text,
                module="FIRE-05",
                evidence_ids=[str(x) for x in te if x],
                confidence=float(tc) if isinstance(tc, (int, float)) else conf,
                reporting_period=period or _period(o),
            )
        )
    if not blocks and payload.get("summary"):
        blocks.append(
            make_block(
                text=str(payload["summary"]),
                module="FIRE-05",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    if not blocks:
        blocks.append(
            make_block(
                text="FIRE-05 management execution available; see evidence references.",
                module="FIRE-05",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    return blocks


def _summarize_fire06(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    period = _period(payload)
    conf = _confidence(payload, 0.5)
    eids = evidence_ids_from_payload("FIRE-06", payload)
    score = payload.get("overall_score") or payload.get("score")
    label = payload.get("overall_label") or payload.get("label")
    if score is not None or label:
        text = f"Business quality overall: {label or 'scored'}"
        if score is not None:
            text = f"{text} ({score})"
        blocks.append(
            make_block(
                text=text,
                module="FIRE-06",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
                kind="score_passthrough",
            )
        )
    pillars = _as_list(payload.get("pillars") or payload.get("pillar_scores") or payload.get("items"))
    for p in pillars[:12]:
        if not isinstance(p, dict):
            continue
        name = p.get("pillar") or p.get("name") or p.get("id") or "pillar"
        ps = p.get("score") or p.get("label") or p.get("status")
        text = f"{name}: {ps}"
        te = _as_list(p.get("evidence_ids")) or eids
        tc = p.get("confidence")
        blocks.append(
            make_block(
                text=text,
                module="FIRE-06",
                evidence_ids=[str(x) for x in te] if te else eids,
                confidence=float(tc) if isinstance(tc, (int, float)) else conf,
                reporting_period=period or _period(p),
            )
        )
    if not blocks and payload.get("summary"):
        blocks.append(
            make_block(
                text=str(payload["summary"]),
                module="FIRE-06",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    if not blocks:
        blocks.append(
            make_block(
                text="FIRE-06 business quality available; see evidence references.",
                module="FIRE-06",
                evidence_ids=eids,
                confidence=conf,
                reporting_period=period,
            )
        )
    return blocks


SUMMARIZERS = {
    "FIRE-01": _summarize_fire01,
    "FIRE-02": _summarize_fire02,
    "FIRE-03": _summarize_fire03,
    "FIRE-04": _summarize_fire04,
    "FIRE-05": _summarize_fire05,
    "FIRE-06": _summarize_fire06,
}


def blocks_for_module(module: str, wrap: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not wrap.get("ok"):
        return [
            make_block(
                text=f"{module} unavailable: {wrap.get('error') or 'collection failed'}",
                module=module,
                evidence_ids=[],
                confidence=0.0,
                kind="availability",
            )
        ]
    payload = wrap.get("payload") if isinstance(wrap.get("payload"), dict) else {}
    fn = SUMMARIZERS.get(module)
    if not fn:
        return []
    return _dedupe_blocks(fn(payload))


def merge_evidence_catalog(collected: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten evidence references across modules; dedupe by evidence id."""
    refs: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for mod, wrap in collected.items():
        payload = wrap.get("payload") if isinstance(wrap, dict) and isinstance(wrap.get("payload"), dict) else {}
        period = _period(payload)
        conf = _confidence(payload, 0.0)
        for eid in evidence_ids_from_payload(mod, payload):
            if eid in seen:
                continue
            seen.add(eid)
            refs.append(
                {
                    "evidence_id": eid,
                    "module": mod,
                    "confidence": conf,
                    "reporting_period": period,
                }
            )
    return refs


def confidence_summary(collected: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    vals = []
    for mod, wrap in collected.items():
        payload = wrap.get("payload") if isinstance(wrap, dict) and isinstance(wrap.get("payload"), dict) else {}
        c = _confidence(payload, 0.0) if wrap.get("ok") else 0.0
        rows.append({"module": mod, "confidence": c, "ok": bool(wrap.get("ok"))})
        if wrap.get("ok"):
            vals.append(c)
    return {
        "by_module": rows,
        "mean_confidence": (sum(vals) / len(vals)) if vals else 0.0,
        "modules_ok": sum(1 for r in rows if r["ok"]),
        "modules_total": len(rows),
    }
