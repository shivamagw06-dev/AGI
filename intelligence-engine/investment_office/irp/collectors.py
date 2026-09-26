"""Soft collectors for FIRE-01…06 — never recalculate; call existing façades only."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def _safe(label: str, fn: Callable[[], Any]) -> Dict[str, Any]:
    try:
        out = fn()
        if isinstance(out, dict):
            return {"ok": True, "module": label, "payload": out}
        return {"ok": True, "module": label, "payload": {"value": out}}
    except Exception as exc:  # noqa: BLE001 — soft boundary
        return {"ok": False, "module": label, "error": f"{type(exc).__name__}: {exc}", "payload": {}}


def collect_fire_01(
    ticker: str,
    *,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    from financial_trends import analyze_company

    kwargs: Dict[str, Any] = {"ticker": ticker}
    if series_map is not None:
        kwargs["series_map"] = series_map
    return _safe("FIRE-01", lambda: analyze_company(**kwargs))


def collect_fire_02(
    ticker: str,
    *,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    from financial_relationships import analyze_company

    kwargs: Dict[str, Any] = {"ticker": ticker}
    if series_map is not None:
        kwargs["series_map"] = series_map
    return _safe("FIRE-02", lambda: analyze_company(**kwargs))


def collect_fire_03(
    ticker: str,
    *,
    documents: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    from business_intelligence import analyze_company

    kwargs: Dict[str, Any] = {"ticker": ticker}
    if documents is not None:
        kwargs["documents"] = documents
    return _safe("FIRE-03", lambda: analyze_company(**kwargs))


def collect_fire_04(
    ticker: str,
    *,
    documents: Optional[List[Dict[str, Any]]] = None,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    from evidence_fusion import analyze_company

    kwargs: Dict[str, Any] = {"ticker": ticker}
    if documents is not None:
        kwargs["documents"] = documents
    if series_map is not None:
        kwargs["series_map"] = series_map
    return _safe("FIRE-04", lambda: analyze_company(**kwargs))


def collect_fire_05(
    ticker: str,
    *,
    documents: Optional[List[Dict[str, Any]]] = None,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    from management_execution import analyze_company

    kwargs: Dict[str, Any] = {"ticker": ticker}
    if documents is not None:
        kwargs["documents"] = documents
    if series_map is not None:
        kwargs["series_map"] = series_map
    return _safe("FIRE-05", lambda: analyze_company(**kwargs))


def collect_fire_06(
    ticker: str,
    *,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    fire01: Optional[Dict[str, Any]] = None,
    fire02: Optional[Dict[str, Any]] = None,
    fire03: Optional[Dict[str, Any]] = None,
    fire04: Optional[Dict[str, Any]] = None,
    fire05: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from business_quality import analyze_company

    kwargs: Dict[str, Any] = {"ticker": ticker}
    if series_map is not None:
        kwargs["series_map"] = series_map
    if documents is not None:
        kwargs["documents"] = documents
    if fire01 is not None:
        kwargs["fire01"] = fire01
    if fire02 is not None:
        kwargs["fire02"] = fire02
    if fire03 is not None:
        kwargs["fire03"] = fire03
    if fire04 is not None:
        kwargs["fire04"] = fire04
    if fire05 is not None:
        kwargs["fire05"] = fire05
    return _safe("FIRE-06", lambda: analyze_company(**kwargs))


COLLECTORS = {
    "FIRE-01": collect_fire_01,
    "FIRE-02": collect_fire_02,
    "FIRE-03": collect_fire_03,
    "FIRE-04": collect_fire_04,
    "FIRE-05": collect_fire_05,
    "FIRE-06": collect_fire_06,
}


def collect_modules(
    ticker: str,
    modules: List[str],
    *,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    prebuilt: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Collect module payloads in dependency-friendly order.
    FIRE-06 reuses earlier packs when present (no re-analysis of prior engines).
    """
    out: Dict[str, Dict[str, Any]] = {}
    pre = prebuilt or {}
    ordered = [m for m in ("FIRE-01", "FIRE-02", "FIRE-03", "FIRE-04", "FIRE-05", "FIRE-06") if m in modules]

    for mod in ordered:
        if mod in pre and isinstance(pre[mod], dict):
            out[mod] = {"ok": True, "module": mod, "payload": pre[mod], "source": "prebuilt"}
            continue
        if mod == "FIRE-01":
            out[mod] = collect_fire_01(ticker, series_map=series_map)
        elif mod == "FIRE-02":
            out[mod] = collect_fire_02(ticker, series_map=series_map)
        elif mod == "FIRE-03":
            out[mod] = collect_fire_03(ticker, documents=documents)
        elif mod == "FIRE-04":
            out[mod] = collect_fire_04(ticker, documents=documents, series_map=series_map)
        elif mod == "FIRE-05":
            out[mod] = collect_fire_05(ticker, documents=documents, series_map=series_map)
        elif mod == "FIRE-06":
            out[mod] = collect_fire_06(
                ticker,
                series_map=series_map,
                documents=documents,
                fire01=_payload(out.get("FIRE-01")),
                fire02=_payload(out.get("FIRE-02")),
                fire03=_payload(out.get("FIRE-03")),
                fire04=_payload(out.get("FIRE-04")),
                fire05=_payload(out.get("FIRE-05")),
            )
    return out


def _payload(wrap: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not wrap or not wrap.get("ok"):
        return None
    p = wrap.get("payload")
    return p if isinstance(p, dict) else None
