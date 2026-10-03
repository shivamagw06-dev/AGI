"""Management execution distribution — reuse FIRE-05 only; never rescore."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


def _payload_from_fire05(ticker: str, prebuilt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if prebuilt is not None:
        return dict(prebuilt)
    try:
        from management_execution import analyze_company

        out = analyze_company(ticker=ticker)
        return out if isinstance(out, dict) else {}
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"{type(exc).__name__}: {exc}", "ticker": ticker}


def _objectives(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("objectives") or payload.get("assessments") or payload.get("items") or []
    return [dict(r) for r in rows if isinstance(r, dict)]


def aggregate_execution(
    portfolio: Mapping[str, Any],
    *,
    fire05_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> dict[str, Any]:
    holdings = list(portfolio.get("holdings") or [])
    pre = fire05_map or {}
    per_holding: List[dict[str, Any]] = []
    status_weights: dict[str, float] = {}
    delivered_w = 0.0
    outstanding_w = 0.0
    conf_acc = 0.0
    conf_w = 0.0
    refs: List[dict[str, Any]] = []
    score_acc = 0.0
    score_w = 0.0

    outstanding_tokens = ("not yet", "partial", "cannot", "open", "outstanding")
    delivered_tokens = ("delivered", "complete", "met", "achieved")

    for h in holdings:
        t = str(h.get("ticker") or "").upper()
        w = float(h.get("weight") or 0.0)
        payload = _payload_from_fire05(t, pre.get(t))
        objs = _objectives(payload)
        conf = float(payload.get("confidence") or 0.0) if isinstance(payload.get("confidence"), (int, float)) else 0.0
        eids = [str(x) for x in (payload.get("evidence_ids") or [])]
        for o in objs:
            for e in o.get("evidence_ids") or []:
                eids.append(str(e))
            if o.get("objective_id") or o.get("id"):
                eids.append(str(o.get("objective_id") or o.get("id")))
        eids = list(dict.fromkeys(eids))

        status_counts: dict[str, int] = {}
        for o in objs:
            st = str(o.get("status") or o.get("execution_status") or o.get("label") or "assessed")
            status_counts[st] = status_counts.get(st, 0) + 1
            status_weights[st] = status_weights.get(st, 0.0) + w
            st_l = st.lower()
            if any(tok in st_l for tok in delivered_tokens):
                delivered_w += w
            if any(tok in st_l for tok in outstanding_tokens):
                outstanding_w += w

        # Optional pass-through score if FIRE-05 exposes one
        score = None
        for k in ("score", "execution_score", "overall_score"):
            if isinstance(payload.get(k), (int, float)):
                score = float(payload[k])
                break
        if score is not None and w > 0:
            score_acc += score * w
            score_w += w

        ok = "_error" not in payload and bool(objs or score is not None)
        per_holding.append(
            {
                "ticker": t,
                "weight": w,
                "score": score,
                "status_counts": status_counts,
                "objectives_n": len(objs),
                "confidence": conf,
                "module": "FIRE-05",
                "evidence_ids": eids,
                "ok": ok,
                "error": payload.get("_error"),
            }
        )
        if conf and w > 0:
            conf_acc += conf * w
            conf_w += w
        for eid in eids:
            refs.append(
                {
                    "evidence_id": eid,
                    "module": "FIRE-05",
                    "ticker": t,
                    "confidence": conf,
                    "reporting_period": payload.get("period") or payload.get("reporting_period"),
                }
            )

    covered = sum(1 for r in per_holding if r.get("ok"))
    return {
        "schema": "po01.execution_distribution.v1",
        "module": "FIRE-05",
        "rescores": False,
        "portfolio_execution_score": (score_acc / score_w) if score_w else None,
        "status_weight_distribution": [
            {"status": k, "weight": v} for k, v in sorted(status_weights.items(), key=lambda x: -x[1])
        ],
        "delivered_weight": delivered_w,
        "outstanding_weight": outstanding_w,
        "holdings_covered": covered,
        "holdings_total": len(per_holding),
        "per_holding": per_holding,
        "confidence": (conf_acc / conf_w) if conf_w else 0.0,
        "evidence_references": refs,
        "note": "Aggregated from FIRE-05 pass-through objectives/scores; never rescored.",
    }
