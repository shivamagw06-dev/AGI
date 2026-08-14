"""API surface for Forecast Intelligence Engine (Phase 8.5)."""

from __future__ import annotations

from typing import Any, Optional

from forecast_intelligence_engine.composer import build_forecast, build_module
from forecast_intelligence_engine.models import ENGINE_CODE, ENGINE_LABEL, MODULES, VERSION
from forecast_intelligence_engine import runtime as fie_runtime


def _stored_rows(tab: str, symbol: str, *, limit: int = 50) -> tuple[list[dict[str, Any]], int]:
    """Read one company's persisted forecast without running forecast builders.

    Public GET endpoints must remain cheap. Building a forecast can read several
    large warehouse tabs and belongs to the background runtime, not a request
    handler.
    """
    try:
        from institutional_warehouse import store

        page = store.fetch(
            tab,
            filters={"symbol": str(symbol or "").strip().upper()},
            sort="as_of",
            order="desc",
            limit=limit,
        )
        return list(page.get("rows") or []), int(page.get("total") or 0)
    except Exception:
        return [], 0


def stored_company(symbol: str) -> dict[str, Any]:
    """Return the latest materialised forecast; never compute on the HTTP path."""
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "symbol_required", "engine": ENGINE_CODE, "version": VERSION}
    summaries, _ = _stored_rows("forecast_company", ticker, limit=1)
    if not summaries:
        return {
            "ok": False,
            "symbol": ticker,
            "status": "NOT_READY",
            "error": "stored_forecast_not_found",
            "retryable": True,
            "engine": ENGINE_CODE,
            "version": VERSION,
        }
    summary = summaries[0]
    scenario_rows, _ = _stored_rows("forecast_scenarios", ticker, limit=10)
    assumption_rows, _ = _stored_rows("forecast_assumptions", ticker, limit=50)
    probabilities = {
        "bull": summary.get("bull_pct"),
        "base": summary.get("base_pct"),
        "bear": summary.get("bear_pct"),
    }
    return {
        "ok": True,
        "cached": True,
        "symbol": ticker,
        "status": summary.get("status"),
        "as_of": summary.get("as_of"),
        "executive_summary": summary.get("executive_summary"),
        "forecast_quality": {
            "forecast_confidence": summary.get("forecast_confidence"),
            "score": summary.get("score"),
            "coverage_pct": summary.get("coverage_pct"),
        },
        "probabilities": probabilities,
        "scenarios": scenario_rows,
        "assumptions": assumption_rows,
        "modules_ok": summary.get("modules_ok"),
        "dqiv": summary.get("dqiv"),
        "generated_at": summary.get("last_updated") or (summary.get("_meta") or {}).get("updated_at"),
        "recommendation": None,
        "target_price": None,
        "vendor_calls": False,
        "engine": ENGINE_CODE,
        "version": summary.get("version") or VERSION,
    }


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "label": ENGINE_LABEL,
        "version": VERSION,
        "role": "institutional_forecast_consumer",
        "vendor_calls": False,
        "ui_calculations": False,
        "recommendation_language": False,
        "target_prices": False,
        "modules": list(MODULES),
        "reads_from": [
            "institutional_warehouse",
            "uve",
            "hvie",
            "varie",
            "vpae",
            "rie",
        ],
        "endpoints": [
            "/v1/fie/health",
            "/v1/fie/company/{symbol}",
            "/v1/fie/business/{symbol}",
            "/v1/fie/growth/{symbol}",
            "/v1/fie/profitability/{symbol}",
            "/v1/fie/balance-sheet/{symbol}",
            "/v1/fie/valuation/{symbol}",
            "/v1/fie/scenarios/{symbol}",
            "/v1/fie/sensitivity/{symbol}",
            "/v1/fie/risks/{symbol}",
            "/v1/fie/catalysts/{symbol}",
            "/v1/fie/confidence/{symbol}",
            "/v1/fie/history/{symbol}",
            "/v1/fie/accuracy/{symbol}",
            "/v1/fie/runtime/status",
            "/v1/fie/runtime/board",
            "/v1/fie/runtime/start",
            "/v1/fie/runtime/stop",
            "/v1/fie/runtime/resume",
        ],
        "note": "Canonical Phase 8.5 prefix is /v1/fie/* (legacy /v1/forecast/* retained for older scenario layer).",
    }


def company(symbol: str) -> dict[str, Any]:
    return stored_company(symbol)


def module(symbol: str, name: str) -> dict[str, Any]:
    return build_module(symbol, name)


def business(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "business")


def growth(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "growth")


def profitability(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "profitability")


def balance_sheet(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "balance_sheet")


def valuation(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "valuation")


def scenarios(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "scenarios")


def sensitivity(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "sensitivity")


def risks(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "risks")


def catalysts(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "catalysts")


def confidence(symbol: str) -> dict[str, Any]:
    pack = build_forecast(symbol)
    return {
        "ok": pack.get("ok"),
        "symbol": pack.get("symbol"),
        "forecast_quality": pack.get("forecast_quality"),
        "module": (pack.get("modules") or {}).get("confidence"),
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def history(symbol: str) -> dict[str, Any]:
    return build_module(symbol, "history")


def accuracy(symbol: str) -> dict[str, Any]:
    from forecast_intelligence_engine.accuracy import evaluate_symbol

    evaluation = evaluate_symbol(symbol)
    out = build_module(symbol, "accuracy")
    out["evaluation"] = evaluation
    return out


def coverage(*, limit: int = 200) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    try:
        from institutional_warehouse import store

        page = store.fetch(
            "forecast_company",
            sort="last_updated",
            order="desc",
            limit=min(max(int(limit), 1), 2000),
        )
        rows = list(page.get("rows") or [])
        total = int(page.get("total") or 0)
    except Exception:
        rows = []
        total = 0
    # This is the high-confidence count in the returned page, not a fabricated
    # universe-wide aggregate. Name it explicitly so consumers cannot confuse it.
    high = sum(1 for r in rows if r.get("forecast_confidence") == "High")
    return {
        "ok": True,
        "count": total,
        "returned": len(rows),
        "high_confidence_returned": high,
        "rows": rows[:limit],
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def dashboard() -> dict[str, Any]:
    return {
        "ok": True,
        "health": health(),
        "runtime": fie_runtime.board(),
        "coverage": coverage(limit=50),
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def calibration_board() -> dict[str, Any]:
    from forecast_intelligence_engine.accuracy import calibration_summary
    try:
        from institutional_warehouse import store
        accuracy_rows = store.all_rows("forecast_accuracy", limit=100000)
        evaluations = store.all_rows("forecast_evaluations", limit=100000)
        predictions = store.all_rows("forecast_metric_predictions", limit=100000)
        summary = calibration_summary(accuracy_rows, evaluations, prediction_count=len(predictions))
        return {"ok": True, "engine": ENGINE_CODE, "version": VERSION, **summary}
    except Exception as exc:
        return {"ok": False, "engine": ENGINE_CODE, "version": VERSION,
                "status": "UNAVAILABLE", "execution_eligible": False, "error": str(exc)[:240]}


def ask_slice(question: str, *, symbol: Optional[str] = None) -> dict[str, Any]:
    """Soft Ask surface — route question to the most relevant FIE module."""
    q = (question or "").lower()
    ticker = (symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "symbol_required"}
    if any(w in q for w in ("bull", "bear", "base case", "scenario")):
        name = "scenarios"
    elif any(w in q for w in ("sensitivity", "assumptions matter", "what if")):
        name = "sensitivity"
    elif any(w in q for w in ("risk", "invalidate")):
        name = "risks"
    elif any(w in q for w in ("catalyst",)):
        name = "catalysts"
    elif any(w in q for w in ("confidence", "why is confidence")):
        name = "confidence"
    elif any(w in q for w in ("history", "changed", "revision")):
        name = "history"
    elif any(w in q for w in ("accuracy", "missed", "error")):
        name = "accuracy"
    elif any(w in q for w in ("valuation", "expensive", "multiple")):
        name = "valuation"
    elif any(w in q for w in ("growth", "cagr")):
        name = "growth"
    elif any(w in q for w in ("margin", "roe", "profit")):
        name = "profitability"
    elif any(w in q for w in ("balance", "debt", "cash", "leverage")):
        name = "balance_sheet"
    elif any(w in q for w in ("forecast", "outlook", "next 3", "fy+")):
        # Full pack executive
        pack = build_forecast(ticker)
        exec_sec = (pack.get("modules") or {}).get("executive") or {}
        return {
            "ok": pack.get("ok"),
            "symbol": ticker,
            "module": "executive",
            "summary": exec_sec.get("summary") or pack.get("executive_summary"),
            "findings": exec_sec.get("findings") or [],
            "confidence": exec_sec.get("confidence"),
            "explainability": exec_sec.get("explainability"),
            "probabilities": pack.get("probabilities"),
            "recommendation": None,
            "engine": ENGINE_CODE,
            "version": VERSION,
        }
    else:
        name = "executive"
    sec = build_module(ticker, name)
    return {
        "ok": sec.get("ok"),
        "symbol": ticker,
        "module": name,
        "summary": sec.get("summary"),
        "findings": sec.get("findings") or [],
        "confidence": sec.get("confidence"),
        "explainability": sec.get("explainability"),
        "recommendation": None,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def runtime_status() -> dict[str, Any]:
    return fie_runtime.status()


def runtime_board() -> dict[str, Any]:
    return fie_runtime.board()


def runtime_start() -> dict[str, Any]:
    return fie_runtime.start()


def runtime_stop() -> dict[str, Any]:
    return fie_runtime.stop()


def runtime_resume() -> dict[str, Any]:
    return fie_runtime.resume()


def runtime_run(batch: int = 3) -> dict[str, Any]:
    return fie_runtime.process_batch(batch=batch)
