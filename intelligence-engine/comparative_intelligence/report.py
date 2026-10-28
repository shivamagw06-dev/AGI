"""Build Institutional Comparison Report (ICR) from collected FIRE packs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from comparative_intelligence.compare import (
    evidence_ids,
    key_differences,
    side_by_side,
)
from comparative_intelligence.schema import ICR_SECTION_TITLES, ICR_SECTIONS


def _block(
    text: str,
    *,
    module: str,
    evidence_ids_list: List[str],
    confidence: float,
    reporting_period: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    kind: str = "comparison",
) -> Dict[str, Any]:
    """Build a provenance block via Office SDK EvidenceBlock (soft shared contract)."""
    try:
        from office_sdk.contracts import evidence_block

        return evidence_block(
            text,
            module=module,
            evidence_ids=evidence_ids_list,
            confidence=confidence,
            reporting_period=reporting_period,
            tickers=tickers,
            kind=kind,
        )
    except Exception:  # noqa: BLE001 — never break CIO if SDK unavailable
        return {
            "text": text,
            "module": module,
            "evidence_ids": list(evidence_ids_list),
            "confidence": float(confidence),
            "reporting_period": reporting_period,
            "tickers": list(tickers or []),
            "kind": kind,
        }


def _section(key: str, blocks: List[Dict[str, Any]], *, order: int, board: Any = None) -> Dict[str, Any]:
    return {
        "key": key,
        "title": ICR_SECTION_TITLES.get(key, key),
        "order": order,
        "blocks": blocks,
        "block_count": len(blocks),
        "board": board,
    }


def _mean_confidence(universe: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
    rows = []
    vals = []
    for ticker, mods in universe.items():
        for mod, wrap in mods.items():
            payload = wrap.get("payload") if wrap.get("ok") and isinstance(wrap.get("payload"), dict) else {}
            c = float(payload.get("confidence") or 0.0) if wrap.get("ok") else 0.0
            rows.append({"ticker": ticker, "module": mod, "confidence": c, "ok": bool(wrap.get("ok"))})
            if wrap.get("ok"):
                vals.append(c)
    return {
        "by_company_module": rows,
        "mean_confidence": (sum(vals) / len(vals)) if vals else 0.0,
        "ok_count": sum(1 for r in rows if r["ok"]),
        "total": len(rows),
    }


def _refs(universe: Dict[str, Dict[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    seen = set()
    for ticker, mods in universe.items():
        for mod, wrap in mods.items():
            payload = wrap.get("payload") if wrap.get("ok") and isinstance(wrap.get("payload"), dict) else {}
            conf = float(payload.get("confidence") or 0.0)
            period = payload.get("period") or payload.get("reporting_period")
            for eid in evidence_ids(mod, payload):
                key = f"{ticker}:{mod}:{eid}"
                if key in seen:
                    continue
                seen.add(key)
                refs.append(
                    {
                        "evidence_id": eid,
                        "module": mod,
                        "ticker": ticker,
                        "confidence": conf,
                        "reporting_period": period,
                    }
                )
    return refs


def build_icr(
    *,
    tickers: Sequence[str],
    comparison_type: str,
    question: Optional[str],
    modules: Sequence[str],
    universe: Dict[str, Dict[str, Dict[str, Any]]],
    routing: Dict[str, Any],
    assembly_ms: float,
) -> Dict[str, Any]:
    tickers_l = list(tickers)
    conf = _mean_confidence(universe)
    refs = _refs(universe)
    diffs = key_differences(tickers_l, universe)

    dim_keys = [
        "business_quality_comparison",
        "growth",
        "margins",
        "cash_flow",
        "balance_sheet",
        "capital_allocation",
        "management_execution",
        "evidence_alignment",
    ]

    boards: Dict[str, Any] = {k: side_by_side(tickers_l, universe, k) for k in dim_keys}

    exec_text = (
        f"Institutional Comparison Report for {', '.join(tickers_l)} "
        f"(type={comparison_type}). "
        f"Assembled from modules {', '.join(modules)}. "
        f"Mean confidence={conf['mean_confidence']:.2f}. "
        "Comparative Intelligence Office compares existing FIRE evidence only; "
        "it does not create new analysis."
    )
    eids: List[str] = []
    for r in refs[:20]:
        eids.append(r["evidence_id"])

    section_map: Dict[str, tuple[List[Dict[str, Any]], Any]] = {}
    section_map["executive_summary"] = (
        [
            _block(
                exec_text,
                module="CIO-01",
                evidence_ids_list=list(dict.fromkeys(eids))[:20],
                confidence=float(conf["mean_confidence"]),
                tickers=tickers_l,
                kind="executive",
            )
        ],
        None,
    )

    for key in dim_keys:
        board = boards[key]
        blocks = [
            _block(
                str(row.get("text") or ""),
                module=str(row.get("module") or "CIO-01"),
                evidence_ids_list=[str(x) for x in (row.get("evidence_ids") or [])],
                confidence=float(row.get("confidence") or 0.0),
                reporting_period=row.get("period"),
                tickers=[row.get("ticker")] if row.get("ticker") else tickers_l,
            )
            for row in board.get("rows") or []
        ]
        section_map[key] = (blocks, board)

    section_map["key_differences"] = (
        [
            _block(
                d["text"],
                module=str(d.get("module") or "CIO-01"),
                evidence_ids_list=[str(x) for x in (d.get("evidence_ids") or [])],
                confidence=float(d.get("confidence") or 0.0),
                tickers=[d.get("higher"), d.get("lower")],
                kind="difference",
            )
            for d in diffs
        ]
        or [
            _block(
                "No numeric score gaps available from invoked modules.",
                module="CIO-01",
                evidence_ids_list=[],
                confidence=0.0,
                tickers=tickers_l,
                kind="difference",
            )
        ],
        {"differences": diffs},
    )

    # Evidence coverage
    coverage_blocks = []
    for t in tickers_l:
        mods = universe.get(t) or {}
        ok = [m for m, w in mods.items() if w.get("ok")]
        missing = [m for m, w in mods.items() if not w.get("ok")]
        coverage_blocks.append(
            _block(
                f"{t}: modules_ok={ok or 'none'}; missing={missing or 'none'}",
                module="CIO-01",
                evidence_ids_list=[],
                confidence=1.0 if ok and not missing else 0.5,
                tickers=[t],
                kind="coverage",
            )
        )
    section_map["evidence_coverage"] = (coverage_blocks, None)

    section_map["confidence"] = (
        [
            _block(
                f"Mean confidence {conf['mean_confidence']:.2f} "
                f"({conf['ok_count']}/{conf['total']} company-module packs OK).",
                module="CIO-01",
                evidence_ids_list=[],
                confidence=float(conf["mean_confidence"]),
                tickers=tickers_l,
                kind="confidence",
            )
        ]
        + [
            _block(
                f"{r['ticker']}/{r['module']}: confidence={r['confidence']:.2f} ok={r['ok']}",
                module=r["module"],
                evidence_ids_list=[],
                confidence=float(r["confidence"]),
                tickers=[r["ticker"]],
                kind="confidence",
            )
            for r in conf["by_company_module"]
        ],
        conf,
    )

    section_map["references"] = (
        [
            _block(
                f"{r['ticker']}: {r['evidence_id']} ← {r['module']}"
                + (f" period={r['reporting_period']}" if r.get("reporting_period") else "")
                + f" confidence={r['confidence']:.2f}",
                module=r["module"],
                evidence_ids_list=[r["evidence_id"]],
                confidence=float(r["confidence"]),
                reporting_period=r.get("reporting_period"),
                tickers=[r["ticker"]],
                kind="reference",
            )
            for r in refs
        ]
        or [
            _block(
                "No evidence references available.",
                module="CIO-01",
                evidence_ids_list=[],
                confidence=0.0,
                tickers=tickers_l,
                kind="reference",
            )
        ],
        None,
    )

    sections: List[Dict[str, Any]] = []
    for i, key in enumerate(ICR_SECTIONS, start=1):
        blocks, board = section_map.get(key, ([], None))
        sections.append(_section(key, blocks, order=i, board=board))

    return {
        "schema": "cio01.institutional_comparison_report.v1",
        "tickers": tickers_l,
        "question": question,
        "comparison_type": comparison_type,
        "modules_invoked": list(modules),
        "routing": routing,
        "assembly_ms": round(float(assembly_ms), 3),
        "confidence": conf,
        "evidence_references": refs,
        "key_differences": diffs,
        "sections": sections,
        "guardrails": {
            "recalculates": False,
            "rescores": False,
            "invents_conclusions": False,
            "buy_sell": False,
            "valuation": False,
            "compares_only": True,
        },
    }
