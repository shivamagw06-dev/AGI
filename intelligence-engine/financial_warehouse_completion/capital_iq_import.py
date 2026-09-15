"""Capital IQ → warehouse import framework (via IKT / refresh stage)."""

from __future__ import annotations

from typing import Any, Optional

from financial_warehouse_completion.models import ENGINE_CODE, PROGRAMME_VERSION


def import_framework_status() -> dict[str, Any]:
    """Describe CapIQ import readiness without calling live vendors."""
    try:
        from financial_warehouse_completion.capiq_workbook import preview
        workbook = preview()
    except Exception as exc:
        workbook = {"ok": False, "error": str(exc)[:160]}
    return {
        "ok": bool(workbook.get("ok")),
        "source": "capital_iq",
        "pipeline_stage": "capital_iq_workbook",
        "imports": ["financials_annual"],
        "normalisation": {"currency": "INR", "units": "INR million",
                          "statement_preference": "CONSOLIDATED"},
        "never": ["historical_pe", "historical_pb", "historical_ev_ebitda"],
        "workbook": workbook,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
    }


def run_capital_iq_stage(
    *,
    limit: Optional[int] = None,
    actor: str = "fwcp",
) -> dict[str, Any]:
    """Import the checked-in annual workbook; retain IKT as a fallback."""
    try:
        from financial_warehouse_completion.capiq_workbook import import_completed_years
        result = import_completed_years(actor=actor)
        if result.get("ok"):
            return {
                "ok": True, "stage": "capital_iq_workbook", "result": result,
                "engine": ENGINE_CODE, "version": PROGRAMME_VERSION,
                "vendor_historical_multiples": False,
            }
    except Exception:
        pass
    try:
        from institutional_warehouse.refresh import stage_capital_iq
        try:
            out = stage_capital_iq(limit=limit, actor=actor)
        except TypeError:
            out = stage_capital_iq()
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:240], "engine": ENGINE_CODE,
                "version": PROGRAMME_VERSION}
    return {
        "ok": bool((out or {}).get("ok", True)), "stage": "capital_iq",
        "result": out, "engine": ENGINE_CODE, "version": PROGRAMME_VERSION,
        "vendor_historical_multiples": False,
    }
