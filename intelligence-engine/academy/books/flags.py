"""Academy Books feature flags."""

from __future__ import annotations

from typing import Any


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:
        return None


def is_academy_enabled() -> bool:
    s = _settings()
    return True if s is None else bool(getattr(s, "academy", True))


def is_books_enabled() -> bool:
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "academy", True)) and bool(getattr(s, "academy_books", True))


def flag_frameworks() -> bool:
    s = _settings()
    return True if s is None else bool(getattr(s, "academy_frameworks", True))


def flag_formulas() -> bool:
    s = _settings()
    return True if s is None else bool(getattr(s, "academy_formulas", True))


def flag_graph() -> bool:
    s = _settings()
    return True if s is None else bool(getattr(s, "academy_graph", True))


def flag_spreadsheets() -> bool:
    s = _settings()
    return True if s is None else bool(getattr(s, "academy_spreadsheets", True))


def flag_books_v3() -> bool:
    """Academy Books V3 — institutional knowledge transformation (soft layer)."""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "academy", True)) and bool(getattr(s, "academy_books_v3", True))


def flag_validation_suite() -> bool:
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "academy", True)) and bool(
        getattr(s, "academy_validation_suite", True)
    )


def flag_certification_suite() -> bool:
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "academy", True)) and bool(
        getattr(s, "academy_certification_suite", True)
    )


def flag_regression_suite() -> bool:
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "academy", True)) and bool(
        getattr(s, "institutional_regression_suite", True)
    )


def flag_evidence_intelligence_layer() -> bool:
    """Evidence Intelligence Layer — source attribution / peer+history / explainable confidence."""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "academy", True)) and bool(
        getattr(s, "evidence_intelligence_layer", True)
    )


def flag_peer_intelligence() -> bool:
    """Peer Intelligence Layer — relative peer/history/percentile comparison."""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "peer_intelligence", True))


def flag_filing_intelligence() -> bool:
    """Filing Intelligence Layer — institutional memory from official filings."""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "filing_intelligence", True))


def flag_filing_diff_engine() -> bool:
    """Filing Diff Engine — what materially changed since the previous filing?"""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "filing_diff_engine", True))


def flag_management_intelligence() -> bool:
    """Management Intelligence Engine — can management be trusted?"""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "management_intelligence", True))


def flag_institutional_stack() -> bool:
    """Institutional Intelligence Stack — soft FIL→FDI→MII→EIL→PIL integration."""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "institutional_stack", True))


def flag_accounting_intelligence() -> bool:
    """Accounting Intelligence Engine — can the financial statements be trusted?"""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "accounting_intelligence", True))


def flag_portfolio_intelligence() -> bool:
    """Portfolio Intelligence Office — does this improve this specific portfolio?"""
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "portfolio_intelligence", True))


def flags_dict() -> dict[str, Any]:
    return {
        "ACADEMY": is_academy_enabled(),
        "ACADEMY_BOOKS": is_books_enabled(),
        "ACADEMY_BOOKS_V3": flag_books_v3(),
        "ACADEMY_VALIDATION_SUITE": flag_validation_suite(),
        "ACADEMY_CERTIFICATION_SUITE": flag_certification_suite(),
        "INSTITUTIONAL_REGRESSION_SUITE": flag_regression_suite(),
        "EVIDENCE_INTELLIGENCE_LAYER": flag_evidence_intelligence_layer(),
        "PEER_INTELLIGENCE": flag_peer_intelligence(),
        "FILING_INTELLIGENCE": flag_filing_intelligence(),
        "FILING_DIFF_ENGINE": flag_filing_diff_engine(),
        "MANAGEMENT_INTELLIGENCE": flag_management_intelligence(),
        "ACCOUNTING_INTELLIGENCE": flag_accounting_intelligence(),
        "PORTFOLIO_INTELLIGENCE": flag_portfolio_intelligence(),
        "INSTITUTIONAL_STACK": flag_institutional_stack(),
        "ACADEMY_FRAMEWORKS": flag_frameworks(),
        "ACADEMY_FORMULAS": flag_formulas(),
        "ACADEMY_GRAPH": flag_graph(),
        "ACADEMY_SPREADSHEETS": flag_spreadsheets(),
    }
