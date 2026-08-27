"""Build Institutional Research Package (IRP) sections from assembled blocks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from investment_office.irp.assemble import (
    blocks_for_module,
    confidence_summary,
    evidence_ids_from_payload,
    make_block,
    merge_evidence_catalog,
)
from investment_office.irp.packages import sections_for_package
from investment_office.schema import IRP_SECTION_TITLES, IRP_SECTIONS


SECTION_MODULES = {
    "company_snapshot": ("FIRE-03", "FIRE-06"),
    "business_quality": ("FIRE-06",),
    "financial_trends": ("FIRE-01",),
    "financial_relationships": ("FIRE-02",),
    "business_strategy": ("FIRE-03",),
    "management_execution": ("FIRE-05",),
    "evidence_consistency": ("FIRE-04",),
}


def _section(key: str, blocks: List[Dict[str, Any]], *, order: int) -> Dict[str, Any]:
    return {
        "key": key,
        "title": IRP_SECTION_TITLES.get(key, key),
        "order": order,
        "blocks": blocks,
        "block_count": len(blocks),
    }


def _pick_strengths_risks(collected: Dict[str, Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    strengths: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    pos_tokens = ("strong", "improving", "delivered", "supported", "high", "stable", "positive")
    neg_tokens = ("weak", "deteriorat", "not supported", "not yet", "cannot", "low", "risk", "negative", "partial")

    for mod in ("FIRE-06", "FIRE-05", "FIRE-04", "FIRE-01", "FIRE-02", "FIRE-03"):
        wrap = collected.get(mod) or {}
        for b in blocks_for_module(mod, wrap):
            text = str(b.get("text") or "").lower()
            if any(t in text for t in pos_tokens) and len(strengths) < 8:
                strengths.append(b)
            elif any(t in text for t in neg_tokens) and len(risks) < 8:
                risks.append(b)
    return strengths, risks


def _outstanding_questions(collected: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    qs: List[Dict[str, Any]] = []
    for mod, wrap in collected.items():
        if not wrap.get("ok"):
            qs.append(
                make_block(
                    text=f"Could not load {mod}; re-run when module evidence is available.",
                    module=mod,
                    evidence_ids=[],
                    confidence=0.0,
                    kind="question",
                )
            )
            continue
        payload = wrap.get("payload") if isinstance(wrap.get("payload"), dict) else {}
        for item in payload.get("outstanding_questions") or payload.get("open_questions") or []:
            if isinstance(item, str) and item.strip():
                qs.append(
                    make_block(
                        text=item.strip(),
                        module=mod,
                        evidence_ids=[],
                        confidence=float(payload.get("confidence") or 0.0)
                        if isinstance(payload.get("confidence"), (int, float))
                        else 0.0,
                        kind="question",
                    )
                )
            elif isinstance(item, dict) and (item.get("text") or item.get("question")):
                qs.append(
                    make_block(
                        text=str(item.get("text") or item.get("question")),
                        module=mod,
                        evidence_ids=[str(x) for x in (item.get("evidence_ids") or [])],
                        confidence=float(item["confidence"])
                        if isinstance(item.get("confidence"), (int, float))
                        else 0.0,
                        kind="question",
                    )
                )
    if not qs:
        qs.append(
            make_block(
                text="No outstanding questions recorded by invoked modules.",
                module="IO-01",
                evidence_ids=[],
                confidence=1.0,
                kind="question",
            )
        )
    return qs[:12]


def _executive_summary(
    ticker: str,
    package_type: str,
    collected: Dict[str, Dict[str, Any]],
    conf: Dict[str, Any],
) -> List[Dict[str, Any]]:
    ok_mods = [m for m, w in collected.items() if w.get("ok")]
    text = (
        f"Institutional Research Package for {ticker} "
        f"(package={package_type}). "
        f"Assembled from {len(ok_mods)}/{len(collected)} module(s): {', '.join(ok_mods) or 'none'}. "
        f"Mean confidence={conf.get('mean_confidence', 0.0):.2f}. "
        "Investment Office orchestrates existing FIRE evidence only; it does not create new analysis."
    )
    eids: List[str] = []
    for mod in ok_mods:
        payload = collected[mod].get("payload") if isinstance(collected[mod].get("payload"), dict) else {}
        eids.extend(evidence_ids_from_payload(mod, payload)[:3])
    return [
        make_block(
            text=text,
            module="IO-01",
            evidence_ids=list(dict.fromkeys(eids))[:20],
            confidence=float(conf.get("mean_confidence") or 0.0),
            kind="executive",
        )
    ]


def build_irp(
    *,
    ticker: str,
    package_type: str,
    question: Optional[str],
    modules: Sequence[str],
    collected: Dict[str, Dict[str, Any]],
    routing: Dict[str, Any],
    assembly_ms: float,
) -> Dict[str, Any]:
    wanted = set(sections_for_package(package_type))
    for must in (
        "executive_summary",
        "confidence_summary",
        "evidence_references",
    ):
        wanted.add(must)

    conf = confidence_summary(collected)
    refs = merge_evidence_catalog(collected)
    strengths, risks = _pick_strengths_risks(collected)

    section_map: Dict[str, List[Dict[str, Any]]] = {}
    section_map["executive_summary"] = _executive_summary(ticker, package_type, collected, conf)

    for key, mods in SECTION_MODULES.items():
        blocks: List[Dict[str, Any]] = []
        for mod in mods:
            if mod not in collected:
                continue
            blocks.extend(blocks_for_module(mod, collected[mod]))
        section_map[key] = blocks

    section_map["key_strengths"] = strengths or [
        make_block(
            text="No strength statements extracted from invoked module outputs.",
            module="IO-01",
            evidence_ids=[],
            confidence=0.0,
            kind="strength",
        )
    ]
    section_map["key_risks"] = risks or [
        make_block(
            text="No risk statements extracted from invoked module outputs.",
            module="IO-01",
            evidence_ids=[],
            confidence=0.0,
            kind="risk",
        )
    ]
    section_map["outstanding_questions"] = _outstanding_questions(collected)
    section_map["confidence_summary"] = [
        make_block(
            text=(
                f"Modules OK {conf['modules_ok']}/{conf['modules_total']}; "
                f"mean confidence {conf['mean_confidence']:.2f}."
            ),
            module="IO-01",
            evidence_ids=[],
            confidence=float(conf["mean_confidence"]),
            kind="confidence",
        )
    ] + [
        make_block(
            text=f"{row['module']}: confidence={row['confidence']:.2f} ok={row['ok']}",
            module=row["module"],
            evidence_ids=[],
            confidence=float(row["confidence"]),
            kind="confidence",
        )
        for row in conf["by_module"]
    ]
    section_map["evidence_references"] = [
        make_block(
            text=f"{r['evidence_id']} ← {r['module']}"
            + (f" period={r['reporting_period']}" if r.get("reporting_period") else "")
            + f" confidence={r['confidence']:.2f}",
            module=r["module"],
            evidence_ids=[r["evidence_id"]],
            confidence=float(r["confidence"]),
            reporting_period=r.get("reporting_period"),
            kind="reference",
        )
        for r in refs
    ] or [
        make_block(
            text="No evidence references available from invoked modules.",
            module="IO-01",
            evidence_ids=[],
            confidence=0.0,
            kind="reference",
        )
    ]

    sections: List[Dict[str, Any]] = []
    for i, key in enumerate(IRP_SECTIONS, start=1):
        if key not in wanted:
            continue
        blocks = section_map.get(key) or []
        sections.append(_section(key, blocks, order=i))

    return {
        "schema": "io01.institutional_research_package.v1",
        "ticker": ticker,
        "question": question,
        "package_type": package_type,
        "modules_invoked": list(modules),
        "modules_ok": [m for m, w in collected.items() if w.get("ok")],
        "routing": routing,
        "assembly_ms": round(float(assembly_ms), 3),
        "confidence": conf,
        "evidence_references": refs,
        "sections": sections,
        "guardrails": {
            "recalculates": False,
            "rescores": False,
            "invents_conclusions": False,
            "buy_sell": False,
            "valuation": False,
        },
    }
