"""Soft module probes for IST — never invent analysis; report contribution only."""

from __future__ import annotations

from typing import Any, Callable, Optional


def _safe(module: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        out = fn()
        if isinstance(out, dict):
            contributing = bool(
                out.get("available") is True
                or out.get("ok") is True
                or out.get("enabled") is True
                or out.get("status") == "ok"
                or (out.get("contributing") is True)
            )
            # Explicit non-availability wins
            if out.get("available") is False and out.get("ok") is not True and out.get("status") != "ok":
                contributing = False
            return {
                "module": module,
                "ok": True,
                "contributing": contributing,
                "payload": out,
                "error": out.get("error"),
            }
        if out is None:
            return {"module": module, "ok": False, "contributing": False, "payload": {}, "error": "null"}
        return {
            "module": module,
            "ok": True,
            "contributing": True,
            "payload": {"value": out},
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "module": module,
            "ok": False,
            "contributing": False,
            "payload": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def probe_fse(ticker: str) -> dict[str, Any]:
    def _run():
        try:
            from financial_statements_engine.production import health

            h = health()
        except Exception:
            h = {"status": "unavailable"}
        return {
            "status": h.get("status"),
            "enabled": h.get("enabled", h.get("status") == "ok"),
            "ticker": ticker,
            "role": "statements_before_after_rbi",
            "ok": h.get("status") == "ok" or h.get("enabled") is True,
        }

    return _safe("FSE", _run)


def probe_fil(ticker: str) -> dict[str, Any]:
    def _run():
        try:
            from filing_intelligence.production import dashboard

            d = dashboard()
            status = d.get("status") or ("ok" if d.get("enabled", True) else "disabled")
        except Exception:
            # Module importable counts as wired for orchestration inventory
            try:
                import filing_intelligence  # noqa: F401

                status = "ok"
                d = {"status": "ok", "enabled": True}
            except Exception:
                status = "unavailable"
                d = {"status": "unavailable"}
        return {
            "status": status,
            "enabled": d.get("enabled", status == "ok"),
            "ticker": ticker,
            "role": "regulatory_filings_disclosures",
            "ok": status == "ok" or d.get("enabled") is True,
        }

    return _safe("FIL", _run)


def probe_fire(module: str, ticker: str, *, prebuilt: Optional[dict] = None) -> dict[str, Any]:
    """FIRE contribution via CW pass-through cache / prebuilt — never rescores."""

    def _run():
        if prebuilt and module in prebuilt:
            return {"available": True, "ok": True, "source": "prebuilt", "payload": prebuilt[module]}
        try:
            from company_workspace.collectors import collect_module

            coll = collect_module(ticker, module, prebuilt=prebuilt)
            return {
                "available": bool(coll.get("available")),
                "ok": bool(coll.get("available")),
                "source": coll.get("source"),
                "payload": coll.get("payload") or {},
            }
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "ok": False, "error": str(exc)}

    return _safe(module, _run)


def probe_cio(ticker: str, peers: list[str], *, prebuilt: Optional[dict] = None) -> dict[str, Any]:
    def _run():
        if prebuilt and "CIO-01" in prebuilt:
            return {"ok": True, "available": True, "source": "prebuilt", "payload": prebuilt["CIO-01"]}
        try:
            from comparative_intelligence.production import health

            h = health()
            return {
                "ok": h.get("status") == "ok" or h.get("enabled") is True,
                "available": True,
                "status": h.get("status"),
                "ticker": ticker,
                "peers": peers,
                "role": "cross_company_comparison",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "available": False, "error": str(exc)}

    return _safe("CIO-01", _run)


def probe_wo(ticker: str) -> dict[str, Any]:
    def _run():
        try:
            from company_workspace.collectors import collect_watchlists

            w = collect_watchlists(ticker)
            # Presence of WO store / health counts even with zero memberships
            from watchlist_office.production import health

            h = health()
            return {
                "ok": h.get("status") == "ok" or h.get("enabled") is True,
                "available": True,
                "memberships": w.get("entries") or [],
                "count": w.get("count") or 0,
                "role": "monitoring_timeline",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "available": False, "error": str(exc)}

    return _safe("WO-01", _run)


def probe_po(ticker: str) -> dict[str, Any]:
    def _run():
        try:
            from company_workspace.collectors import collect_portfolios
            from portfolio_office.production import health

            p = collect_portfolios(ticker)
            h = health()
            return {
                "ok": h.get("status") == "ok" or h.get("enabled") is True,
                "available": True,
                "optional": True,
                "memberships": p.get("memberships") or [],
                "count": p.get("count") or 0,
                "role": "portfolio_exposure",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "available": False, "optional": True, "error": str(exc)}

    return _safe("PO-01", _run)


def probe_cw(ticker: str, *, prebuilt: Optional[dict] = None) -> dict[str, Any]:
    def _run():
        from company_workspace.production import workspace

        pack = workspace(ticker, prebuilt=prebuilt, use_cache=False)
        resp = pack.get("office_response") or {}
        return {
            "ok": bool(pack.get("ok")),
            "available": bool(pack.get("ok")),
            "sections_n": len(pack.get("sections") or resp.get("sections") or []),
            "modules_ok": (resp.get("provenance") or {}).get("modules_ok") or [],
            "presentation_only": True,
        }

    return _safe("CW-01", _run)


def probe_io(ticker: str) -> dict[str, Any]:
    def _run():
        try:
            from investment_office.production import health

            h = health()
            return {
                "ok": True,
                "available": bool(h.get("enabled", True)),
                "status": h.get("status"),
                "io01": h.get("io01") or {},
                "role": "irp_orchestration",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "available": False, "error": str(exc)}

    return _safe("IO-01", _run)


def probe_ask_agi(ticker: str, *, institutional_view: Optional[dict] = None) -> dict[str, Any]:
    """Ask AGI contribution = presence of final institutional view assembly (not BUY/SELL)."""

    def _run():
        view = institutional_view or {}
        has_view = bool(view.get("investment_thesis")) and bool(view.get("remaining_unknowns"))
        return {
            "ok": has_view,
            "available": has_view,
            "role": "final_institutional_answer",
            "has_buy_sell_collapse": bool(view.get("collapsed_to_buy_sell")),
            "view_keys": list(view.keys()),
        }

    return _safe("AskAGI", _run)


def probe_all(
    ticker: str,
    peers: list[str],
    *,
    prebuilt: Optional[dict] = None,
    institutional_view: Optional[dict] = None,
    modules_filter: Optional[list[str]] = None,
) -> dict[str, dict[str, Any]]:
    """Probe full stack. modules_filter restricts which probes run (for single-module fail tests)."""
    allow = {m.upper() for m in (modules_filter or [])} if modules_filter else None

    def want(mod: str) -> bool:
        if allow is None:
            return True
        return mod.upper() in allow or mod.replace("-", "").upper() in {a.replace("-", "") for a in allow}

    out: dict[str, dict[str, Any]] = {}
    if want("FSE"):
        out["FSE"] = probe_fse(ticker)
    if want("FIL"):
        out["FIL"] = probe_fil(ticker)
    for fire in ("FIRE-01", "FIRE-02", "FIRE-03", "FIRE-04", "FIRE-05", "FIRE-06"):
        if want(fire):
            out[fire] = probe_fire(fire, ticker, prebuilt=prebuilt)
    if want("CIO-01"):
        out["CIO-01"] = probe_cio(ticker, peers, prebuilt=prebuilt)
    if want("WO-01"):
        out["WO-01"] = probe_wo(ticker)
    if want("PO-01"):
        out["PO-01"] = probe_po(ticker)
    if want("CW-01"):
        out["CW-01"] = probe_cw(ticker, prebuilt=prebuilt)
    if want("IO-01"):
        out["IO-01"] = probe_io(ticker)
    if want("AskAGI") or want("ASKAGI"):
        out["AskAGI"] = probe_ask_agi(ticker, institutional_view=institutional_view)
    return out
