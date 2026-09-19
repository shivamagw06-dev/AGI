"""Soft Knowledge Foundation attach from Yahoo financial intelligence (no KF redesign)."""

from __future__ import annotations

from typing import Any, Dict, List

from yfp.history import kpi_trends, summarize_changes
from yfp.schema import YFP_VERSION


def soft_attach_kf(
    ticker: str,
    *,
    financial_history: Dict[str, Any] | None = None,
    valuation_snapshot: Dict[str, Any] | None = None,
    kf: Any | None = None,
) -> Dict[str, Any]:
    """
    Soft-merge financial history summaries into Company Knowledge Object.
    Uses merge_list / bump_version only — never redesigns KF.
    """
    t = (ticker or "").upper()
    if not t:
        return {"attached": False, "reason": "no_ticker"}

    try:
        from app.kf.merge import bump_version, merge_list, merge_string
        from app.kf.models import CompanyKnowledgeObject
        from app.kf.service import KfService
    except Exception as exc:  # noqa: BLE001
        return {"attached": False, "error": f"kf_unavailable:{str(exc)[:120]}"}

    service = kf
    if service is None:
        try:
            service = KfService()
        except Exception as exc:  # noqa: BLE001
            return {"attached": False, "error": str(exc)[:200]}

    try:
        # Prefer existing company object; build if missing
        existing = None
        try:
            if hasattr(service, "pipeline"):
                existing = service.pipeline.build_company(t)
            elif hasattr(service, "get_company"):
                existing = service.get_company(t)
        except Exception:
            existing = None
        if existing is None:
            return {"attached": False, "reason": "no_company_object"}

        data = existing.model_dump(mode="json") if hasattr(existing, "model_dump") else dict(existing)

        fh = financial_history or {}
        vs = valuation_snapshot or {}
        trends = kpi_trends(fh)
        changes = summarize_changes(fh)

        history_lines: List[str] = []
        for field, series in list(trends.items())[:12]:
            if not series:
                continue
            latest = series[0]
            history_lines.append(
                f"{field}:{latest.get('period_end')}={latest.get('value')} (n={len(series)})"
            )
        if changes.get("revenue_growth_pct") is not None:
            history_lines.append(f"revenue_growth_yoy={changes.get('revenue_growth_pct')}%")

        data["financial_history"] = merge_list(data.get("financial_history"), history_lines, limit=40)

        metrics = vs.get("metrics") or {}
        if metrics:
            val_bits = [f"{k}={v}" for k, v in list(metrics.items())[:10]]
            data["valuation"] = merge_string(data.get("valuation") or "", "; ".join(val_bits))

        # Soft scalars when empty
        income = ((fh.get("income_statement") or {}).get("annual") or [])
        if income:
            items = income[0].get("line_items") or {}
            if items.get("net_income") is not None and not data.get("roe"):
                # leave roe empty unless we have it — don't invent
                pass
            margins = list(data.get("margins") or [])
            if items.get("operating_income") is not None and items.get("revenue"):
                try:
                    om = round(float(items["operating_income"]) / float(items["revenue"]) * 100.0, 2)
                    margins = merge_list(margins, [f"operating_margin≈{om}%"], limit=20)
                except Exception:
                    pass
            data["margins"] = margins

        cash = ((fh.get("cash_flow") or {}).get("annual") or [])
        if cash and not data.get("cash_flow"):
            ocf = (cash[0].get("line_items") or {}).get("operating_cash_flow")
            fcf = (cash[0].get("line_items") or {}).get("free_cash_flow")
            data["cash_flow"] = merge_string(
                data.get("cash_flow") or "",
                f"OCF={ocf}; FCF={fcf}",
            )

        bal = ((fh.get("balance_sheet") or {}).get("annual") or [])
        if bal and not data.get("debt"):
            debt = (bal[0].get("line_items") or {}).get("total_debt")
            if debt is not None:
                data["debt"] = merge_string(data.get("debt") or "", f"total_debt={debt}")

        meta = dict(data.get("meta") or {})
        meta = bump_version(meta, reason="yfp_financial_intelligence")
        sources = list(meta.get("sources") or [])
        if "yahoo_canonical" not in sources:
            sources.append("yahoo_canonical")
        meta["sources"] = sources[:20]
        data["meta"] = meta

        obj = CompanyKnowledgeObject.model_validate(data)
        if hasattr(service, "store") and hasattr(service.store, "upsert_company"):
            service.store.upsert_company(obj)
        elif hasattr(service, "upsert_company"):
            service.upsert_company(obj)

        return {
            "attached": True,
            "ticker": t,
            "financial_history_lines": len(history_lines),
            "valuation_fields": len(metrics),
            "yfp_version": YFP_VERSION,
        }
    except Exception as exc:  # noqa: BLE001
        return {"attached": False, "error": str(exc)[:240]}
