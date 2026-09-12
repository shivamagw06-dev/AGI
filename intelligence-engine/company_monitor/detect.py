"""Change detection between previous and current snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from company_monitor.schema import CHANGE_TYPES


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _delta(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None:
        return None
    return curr - prev


def _pct_change(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return (curr / prev - 1.0) * 100.0


def detect_changes(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    ticker: str | None = None,
) -> list[dict[str, Any]]:
    """Return structured change events. Empty if no previous snapshot."""
    if not previous:
        return []

    t = (ticker or current.get("ticker") or previous.get("ticker") or "").upper()
    cm = current.get("metrics") or {}
    pm = previous.get("metrics") or {}
    now = datetime.now(timezone.utc).isoformat()
    out: list[dict[str, Any]] = []

    def emit(
        change_type: str,
        *,
        metric: str,
        current_value: Any,
        previous_value: Any,
        direction: str,
        detail: str,
        magnitude: float | None = None,
    ) -> None:
        if change_type not in CHANGE_TYPES and change_type not in {
            "revenue_acceleration",
            "revenue_deceleration",
            "margin_expansion",
            "margin_compression",
            "debt_increase",
            "debt_reduction",
            "cash_flow_deterioration",
            "cash_flow_improvement",
            "valuation_expansion",
            "valuation_compression",
            "roe_improvement",
            "roe_deterioration",
            "house_view_label_change",
            "evidence_influx",
        }:
            pass
        out.append(
            {
                "ticker": t,
                "change_type": change_type,
                "metric": metric,
                "current": current_value,
                "previous": previous_value,
                "direction": direction,
                "magnitude": magnitude,
                "detail": detail,
                "detected_at": now,
            }
        )

    # Revenue growth acceleration / deceleration
    rg_c, rg_p = _num(cm.get("revenue_growth")), _num(pm.get("revenue_growth"))
    d = _delta(rg_c, rg_p)
    if d is not None and abs(d) >= 0.01:
        emit(
            "revenue_acceleration" if d > 0 else "revenue_deceleration",
            metric="revenue_growth",
            current_value=rg_c,
            previous_value=rg_p,
            direction="up" if d > 0 else "down",
            magnitude=round(d * 100 if abs(rg_c or 0) < 2 else d, 2),
            detail=f"Revenue growth {'accelerated' if d > 0 else 'slowed'} to {rg_c} from {rg_p}",
        )

    # Margin expansion / compression
    m_c, m_p = _num(cm.get("operating_margin")), _num(pm.get("operating_margin"))
    md = _delta(m_c, m_p)
    if md is not None and abs(md) >= 0.002:
        emit(
            "margin_expansion" if md > 0 else "margin_compression",
            metric="operating_margin",
            current_value=m_c,
            previous_value=m_p,
            direction="expanded" if md > 0 else "compressed",
            magnitude=round(md * 100 if abs(m_c or 0) < 2 else md, 2),
            detail=f"Operating margin {'expanded' if md > 0 else 'compressed'} to {m_c} from {m_p}",
        )

    # Debt
    debt_c, debt_p = _num(cm.get("debt")), _num(pm.get("debt"))
    pct = _pct_change(debt_c, debt_p)
    if pct is not None and abs(pct) >= 5:
        emit(
            "debt_increase" if pct > 0 else "debt_reduction",
            metric="debt",
            current_value=debt_c,
            previous_value=debt_p,
            direction="up" if pct > 0 else "down",
            magnitude=round(pct, 1),
            detail=f"Debt {'increased' if pct > 0 else 'reduced'} {abs(round(pct, 1))}%",
        )

    # Cash flow
    cf_c, cf_p = _num(cm.get("cash_flow")), _num(pm.get("cash_flow"))
    cfd = _delta(cf_c, cf_p)
    if cfd is not None and abs(cfd) > 0 and (cf_p or 0) != 0:
        emit(
            "cash_flow_improvement" if cfd > 0 else "cash_flow_deterioration",
            metric="cash_flow",
            current_value=cf_c,
            previous_value=cf_p,
            direction="up" if cfd > 0 else "down",
            magnitude=round(_pct_change(cf_c, cf_p) or 0, 1),
            detail=f"Cash flow {'improved' if cfd > 0 else 'deteriorated'} vs prior snapshot",
        )

    # ROE
    roe_c, roe_p = _num(cm.get("roe")), _num(pm.get("roe"))
    rd = _delta(roe_c, roe_p)
    if rd is not None and abs(rd) >= 0.002:
        emit(
            "roe_improvement" if rd > 0 else "roe_deterioration",
            metric="roe",
            current_value=roe_c,
            previous_value=roe_p,
            direction="improved" if rd > 0 else "deteriorated",
            magnitude=round(rd * 100 if abs(roe_c or 0) < 2 else rd, 2),
            detail=f"ROE {'improved' if rd > 0 else 'deteriorated'} to {roe_c} from {roe_p}",
        )

    # Valuation vs history + expansion/compression
    pe_c, pe_p = _num(cm.get("pe")), _num(pm.get("pe"))
    pe_d = _delta(pe_c, pe_p)
    if pe_d is not None and abs(pe_d) >= 0.5:
        emit(
            "valuation_expansion" if pe_d > 0 else "valuation_compression",
            metric="pe",
            current_value=pe_c,
            previous_value=pe_p,
            direction="up" if pe_d > 0 else "down",
            magnitude=round(pe_d, 2),
            detail=f"PE {'expanded' if pe_d > 0 else 'compressed'} to {pe_c} from {pe_p}",
        )

    hist_pe = _num(cm.get("historical_pe"))
    if pe_c is not None and hist_pe is not None and hist_pe > 0:
        vs = (pe_c / hist_pe - 1.0) * 100.0
        if abs(vs) >= 8:
            emit(
                "valuation_expansion" if vs > 0 else "valuation_compression",
                metric="pe_vs_history",
                current_value=pe_c,
                previous_value=hist_pe,
                direction="above_history" if vs > 0 else "below_history",
                magnitude=round(vs, 1),
                detail=f"Current PE {'above' if vs > 0 else 'below'} historical average by {abs(round(vs, 1))}%",
            )

    # House view label change (monitor only — never auto-mutate)
    hv_c = current.get("house_view_label")
    hv_p = previous.get("house_view_label")
    if hv_c and hv_p and str(hv_c) != str(hv_p):
        emit(
            "house_view_label_change",
            metric="house_view",
            current_value=hv_c,
            previous_value=hv_p,
            direction="changed",
            detail=f"House view label moved {hv_p} → {hv_c}",
        )

    # Evidence influx
    lec = int(current.get("leo_evidence_count") or 0)
    lep = int(previous.get("leo_evidence_count") or 0)
    if lec > lep + 2:
        emit(
            "evidence_influx",
            metric="leo_evidence_count",
            current_value=lec,
            previous_value=lep,
            direction="up",
            magnitude=lec - lep,
            detail=f"LEO evidence objects increased {lep} → {lec}",
        )

    return out
