"""Classify every recommendation change with a reason code."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.drift.schema import REASON_CODES


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _decision(row: dict[str, Any]) -> str:
    return str(row.get("decision") or row.get("action") or "").strip()


def _version_blob(row: dict[str, Any]) -> dict[str, Any]:
    v = row.get("versions") if isinstance(row.get("versions"), dict) else {}
    return v


def classify_reason(
    prev: dict[str, Any] | None,
    cur: dict[str, Any],
    *,
    hint: str | None = None,
) -> dict[str, Any]:
    """
    Return reason code + human explanation.

    Priority: explicit hint → DATA → MARKET → GOVERNANCE → MODEL → BUGFIX → UNKNOWN
    """
    if not prev:
        return {
            "code": "DATA",
            "meaning": REASON_CODES["DATA"],
            "detail": "New to benchmark / no prior baseline",
            "explainable": True,
        }

    prev_d = _decision(prev)
    cur_d = _decision(cur)
    changed = prev_d != cur_d
    if not changed:
        return {
            "code": "NONE",
            "meaning": REASON_CODES["NONE"],
            "detail": "No change",
            "explainable": True,
        }

    if hint and hint.upper() in REASON_CODES and hint.upper() != "NONE":
        code = hint.upper()
        return {
            "code": code,
            "meaning": REASON_CODES[code],
            "detail": f"Operator/hint classified as {code}",
            "explainable": code != "UNKNOWN",
        }

    # DATA — evidence / failure / pack signals moved
    prev_ev = str(prev.get("evidence_class") or "")
    cur_ev = str(cur.get("evidence_class") or "")
    prev_fail = (prev.get("failure") or {}).get("reason") if isinstance(prev.get("failure"), dict) else None
    cur_fail = (cur.get("failure") or {}).get("reason") if isinstance(cur.get("failure"), dict) else None
    prev_pack = bool(prev.get("pack_present"))
    cur_pack = bool(cur.get("pack_present"))
    prev_ready = _f(prev.get("recommendation_readiness"))
    cur_ready = _f(cur.get("recommendation_readiness"))
    ready_delta = None
    if prev_ready is not None and cur_ready is not None:
        ready_delta = abs(cur_ready - prev_ready)

    data_signals = []
    if prev_ev and cur_ev and prev_ev != cur_ev:
        data_signals.append(f"Evidence {prev_ev} → {cur_ev}")
    if prev_fail != cur_fail and (prev_fail or cur_fail):
        data_signals.append(f"Failure {prev_fail or 'none'} → {cur_fail or 'none'}")
    if prev_pack != cur_pack:
        data_signals.append(f"Pack present {prev_pack} → {cur_pack}")
    if ready_delta is not None and ready_delta >= 5:
        data_signals.append(f"Readiness Δ {ready_delta:.1f}pp")
    if data_signals:
        return {
            "code": "DATA",
            "meaning": REASON_CODES["DATA"],
            "detail": "; ".join(data_signals[:4]),
            "explainable": True,
        }

    # MARKET — price / valuation moved
    prev_px = _f(prev.get("price_ltp"))
    cur_px = _f(cur.get("price_ltp"))
    prev_val = _f(prev.get("valuation"))
    cur_val = _f(cur.get("valuation"))
    market_signals = []
    if prev_px is not None and cur_px is not None and prev_px > 0:
        px_chg = abs(cur_px - prev_px) / prev_px
        if px_chg >= 0.02:
            market_signals.append(f"Price {prev_px} → {cur_px} ({px_chg*100:.1f}%)")
    if prev.get("price_available") != cur.get("price_available") or prev.get("live_price") != cur.get("live_price"):
        market_signals.append("Live price availability changed")
    if prev_val is not None and cur_val is not None and abs(cur_val - prev_val) >= 0.5:
        market_signals.append(f"Valuation {prev_val} → {cur_val}")
    if market_signals:
        return {
            "code": "MARKET",
            "meaning": REASON_CODES["MARKET"],
            "detail": "; ".join(market_signals[:4]),
            "explainable": True,
        }

    # GOVERNANCE — gate / thesis / band / constitution version
    gov_signals = []
    if prev.get("gate") != cur.get("gate"):
        gov_signals.append(f"Gate {prev.get('gate')} → {cur.get('gate')}")
    if prev.get("readiness_band") != cur.get("readiness_band"):
        gov_signals.append(f"Band {prev.get('readiness_band')} → {cur.get('readiness_band')}")
    if prev.get("investment_thesis_status") != cur.get("investment_thesis_status"):
        gov_signals.append(
            f"Thesis {prev.get('investment_thesis_status')} → {cur.get('investment_thesis_status')}"
        )
    pv, cv = _version_blob(prev), _version_blob(cur)
    if pv.get("constitution_version") and cv.get("constitution_version"):
        if pv.get("constitution_version") != cv.get("constitution_version"):
            gov_signals.append(
                f"Constitution {pv.get('constitution_version')} → {cv.get('constitution_version')}"
            )
    if pv.get("readiness_gate_version") and cv.get("readiness_gate_version"):
        if pv.get("readiness_gate_version") != cv.get("readiness_gate_version"):
            gov_signals.append(
                f"Readiness gate {pv.get('readiness_gate_version')} → {cv.get('readiness_gate_version')}"
            )
    if gov_signals:
        return {
            "code": "GOVERNANCE",
            "meaning": REASON_CODES["GOVERNANCE"],
            "detail": "; ".join(gov_signals[:4]),
            "explainable": True,
        }

    # MODEL — decision engine / runner / eval version changed
    model_signals = []
    for key, label in (
        ("decision_engine_version", "IDE"),
        ("runner_version", "Runner"),
        ("eval_version", "Eval"),
    ):
        if pv.get(key) and cv.get(key) and pv.get(key) != cv.get(key):
            model_signals.append(f"{label} {pv.get(key)} → {cv.get(key)}")
    # Soft quality score drift without evidence/price change also suggests model
    cq_p, cq_c = _f(prev.get("company_quality")), _f(cur.get("company_quality"))
    if cq_p is not None and cq_c is not None and abs(cq_c - cq_p) >= 0.3 and ready_delta is not None and ready_delta < 3:
        model_signals.append(f"Company quality {cq_p} → {cq_c} without readiness shift")
    if model_signals:
        return {
            "code": "MODEL",
            "meaning": REASON_CODES["MODEL"],
            "detail": "; ".join(model_signals[:4]),
            "explainable": True,
        }

    # BUGFIX — previous status FAILED/error cleared with same evidence class
    if prev.get("status") == "FAILED" and cur.get("status") == "COMPLETED" and prev_ev == cur_ev:
        return {
            "code": "BUGFIX",
            "meaning": REASON_CODES["BUGFIX"],
            "detail": "Prior failed run completed with stable evidence class",
            "explainable": True,
        }

    # UNKNOWN — unexplained recommendation flip
    return {
        "code": "UNKNOWN",
        "meaning": REASON_CODES["UNKNOWN"],
        "detail": (
            f"Decision {prev_d} → {cur_d} without material DATA/MARKET/MODEL/GOVERNANCE signal"
        ),
        "explainable": False,
    }
