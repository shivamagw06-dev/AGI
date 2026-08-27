"""Business quality distribution — reuse FIRE-06 only; never rescore."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


def _payload_from_fire06(ticker: str, prebuilt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if prebuilt is not None:
        return dict(prebuilt)
    try:
        from business_quality import analyze_company

        out = analyze_company(ticker=ticker)
        return out if isinstance(out, dict) else {}
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"{type(exc).__name__}: {exc}", "ticker": ticker}


def _overall(payload: Mapping[str, Any]) -> Optional[float]:
    for k in ("overall_score", "quality_score", "score"):
        if isinstance(payload.get(k), (int, float)):
            return float(payload[k])
    overall = payload.get("overall")
    if isinstance(overall, dict) and isinstance(overall.get("score"), (int, float)):
        return float(overall["score"])
    if isinstance(overall, (int, float)):
        return float(overall)
    return None


def _pillars(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("pillars") or payload.get("pillar_scores") or []
    if isinstance(rows, dict):
        out = []
        for k, v in rows.items():
            if isinstance(v, dict):
                out.append({"pillar": k, **v})
            elif isinstance(v, (int, float)):
                out.append({"pillar": k, "score": float(v)})
        return out
    return [dict(r) for r in rows if isinstance(r, dict)]


def _evidence_ids(payload: Mapping[str, Any]) -> list[str]:
    ids = []
    for x in payload.get("evidence_ids") or []:
        ids.append(str(x))
    for p in _pillars(payload):
        for e in p.get("evidence_ids") or []:
            ids.append(str(e))
    return list(dict.fromkeys(ids))


def aggregate_quality(
    portfolio: Mapping[str, Any],
    *,
    fire06_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Weight-average FIRE-06 scores by holding weight.
    Pass-through only — never recalculates business quality.
    """
    holdings = list(portfolio.get("holdings") or [])
    pre = fire06_map or {}
    per_holding: List[dict[str, Any]] = []
    pillar_acc: dict[str, list[tuple[float, float]]] = {}  # pillar -> [(score, weight)]
    weighted_score = 0.0
    weight_with_score = 0.0
    conf_acc = 0.0
    conf_w = 0.0
    refs: List[dict[str, Any]] = []

    for h in holdings:
        t = str(h.get("ticker") or "").upper()
        w = float(h.get("weight") or 0.0)
        payload = _payload_from_fire06(t, pre.get(t))
        score = _overall(payload)
        conf = float(payload.get("confidence") or 0.0) if isinstance(payload.get("confidence"), (int, float)) else 0.0
        eids = _evidence_ids(payload)
        row = {
            "ticker": t,
            "weight": w,
            "score": score,
            "label": payload.get("overall_label") or payload.get("label"),
            "confidence": conf,
            "module": "FIRE-06",
            "evidence_ids": eids,
            "ok": score is not None and "_error" not in payload,
            "error": payload.get("_error"),
        }
        per_holding.append(row)
        if score is not None and w > 0:
            weighted_score += score * w
            weight_with_score += w
        if conf and w > 0:
            conf_acc += conf * w
            conf_w += w
        for p in _pillars(payload):
            name = str(p.get("pillar") or p.get("name") or p.get("id") or "unknown")
            ps = p.get("score")
            if isinstance(ps, (int, float)) and w > 0:
                pillar_acc.setdefault(name, []).append((float(ps), w))
        for eid in eids:
            refs.append(
                {
                    "evidence_id": eid,
                    "module": "FIRE-06",
                    "ticker": t,
                    "confidence": conf,
                    "reporting_period": payload.get("period") or payload.get("reporting_period"),
                }
            )

    pillar_avgs = []
    for name, pairs in pillar_acc.items():
        tw = sum(w for _, w in pairs)
        avg = sum(s * w for s, w in pairs) / tw if tw else None
        pillar_avgs.append({"pillar": name, "weight_average_score": avg, "weight_coverage": tw})
    pillar_avgs.sort(key=lambda r: str(r["pillar"]))

    covered = sum(1 for r in per_holding if r.get("ok"))
    return {
        "schema": "po01.quality_distribution.v1",
        "module": "FIRE-06",
        "rescores": False,
        "portfolio_quality_score": (weighted_score / weight_with_score) if weight_with_score else None,
        "weight_coverage": weight_with_score,
        "holdings_covered": covered,
        "holdings_total": len(per_holding),
        "pillar_averages": pillar_avgs,
        "per_holding": per_holding,
        "evidence_coverage": {
            "unique_evidence_ids": len({r["evidence_id"] for r in refs}),
            "references": len(refs),
        },
        "confidence": (conf_acc / conf_w) if conf_w else 0.0,
        "evidence_references": refs,
        "note": "Aggregated from FIRE-06 pass-through scores weighted by portfolio weights.",
    }
