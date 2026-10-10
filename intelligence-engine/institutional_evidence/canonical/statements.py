"""Canonical Financial Statements — one schema; never expose provider-specific fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


CANONICAL_LINE_ITEMS = (
    "revenue",
    "ebitda",
    "ebit",
    "pat",
    "eps",
    "total_assets",
    "total_equity",
    "total_debt",
    "cash",
    "capex",
    "operating_cash_flow",
    "free_cash_flow",
    "gross_margin",
    "ebitda_margin",
    "pat_margin",
    "roe",
    "roce",
)


@dataclass
class CanonicalPeriod:
    period: str
    period_type: str  # quarterly | annual
    income_statement: Dict[str, Any] = field(default_factory=dict)
    balance_sheet: Dict[str, Any] = field(default_factory=dict)
    cash_flow: Dict[str, Any] = field(default_factory=dict)
    segment_revenue: Dict[str, Any] = field(default_factory=dict)
    segment_ebitda: Dict[str, Any] = field(default_factory=dict)
    ratios: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class CanonicalFinancialStatements:
    company: str
    ticker: str
    periods: List[Dict[str, Any]] = field(default_factory=list)
    income_statement: List[Dict[str, Any]] = field(default_factory=list)
    balance_sheet: List[Dict[str, Any]] = field(default_factory=list)
    cash_flow: List[Dict[str, Any]] = field(default_factory=list)
    segment_revenue: List[Dict[str, Any]] = field(default_factory=list)
    segment_ebitda: List[Dict[str, Any]] = field(default_factory=list)
    ratios: Dict[str, Any] = field(default_factory=dict)
    capex: List[Dict[str, Any]] = field(default_factory=list)
    debt: List[Dict[str, Any]] = field(default_factory=list)
    cash: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    evidence_references: List[str] = field(default_factory=list)
    published: bool = False
    period_count: int = 0
    schema: str = "CanonicalFinancialStatements.v1"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["period_count"] = len(self.periods)
        d["published"] = bool(self.published and self.periods)
        return d


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pick(row: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in row and row[k] is not None:
            return _num(row[k])
    # nested statements
    stmts = row.get("statements") if isinstance(row.get("statements"), dict) else {}
    for block in ("income_statement", "balance_sheet", "cash_flow", "pnl"):
        b = stmts.get(block) if isinstance(stmts.get(block), dict) else {}
        for k in keys:
            if k in b and b[k] is not None:
                return _num(b[k])
    for k in keys:
        if k in stmts and stmts[k] is not None:
            return _num(stmts[k])
    return None


def _normalize_row(row: Dict[str, Any], period_type: str) -> Dict[str, Any]:
    period = str(
        row.get("period")
        or row.get("period_label")
        or row.get("fiscal_period")
        or row.get("label")
        or "unknown"
    )
    income = {
        "revenue": _pick(row, "revenue", "total_income", "net_sales", "sales"),
        "ebitda": _pick(row, "ebitda", "operating_profit"),
        "ebit": _pick(row, "ebit", "operating_income"),
        "pat": _pick(row, "pat", "net_profit", "profit_after_tax", "np"),
        "eps": _pick(row, "eps", "diluted_eps", "basic_eps"),
        "gross_margin": _pick(row, "gross_margin"),
        "ebitda_margin": _pick(row, "ebitda_margin"),
        "pat_margin": _pick(row, "pat_margin", "npm"),
    }
    balance = {
        "total_assets": _pick(row, "total_assets", "assets"),
        "total_equity": _pick(row, "total_equity", "equity", "shareholders_equity"),
        "total_debt": _pick(row, "total_debt", "debt", "borrowings"),
        "cash": _pick(row, "cash", "cash_and_equivalents", "cash_equivalents"),
    }
    cash_flow = {
        "operating_cash_flow": _pick(row, "operating_cash_flow", "cfo", "cash_from_operations"),
        "free_cash_flow": _pick(row, "free_cash_flow", "fcf"),
        "capex": _pick(row, "capex", "capital_expenditure"),
    }
    ratios = {
        "roe": _pick(row, "roe"),
        "roce": _pick(row, "roce"),
        "gross_margin": income.get("gross_margin"),
        "ebitda_margin": income.get("ebitda_margin"),
        "pat_margin": income.get("pat_margin"),
    }
    seg_rev = row.get("segment_revenue") if isinstance(row.get("segment_revenue"), dict) else {}
    seg_ebitda = row.get("segment_ebitda") if isinstance(row.get("segment_ebitda"), dict) else {}
    return {
        "period": period,
        "period_type": period_type,
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cash_flow,
        "segment_revenue": seg_rev,
        "segment_ebitda": seg_ebitda,
        "ratios": ratios,
        "evidence_refs": list(row.get("evidence_refs") or row.get("source_ids") or []),
    }


def map_provider_to_canonical(
    provider_payload: Dict[str, Any],
    *,
    company: str,
    ticker: str,
    source: str = "unknown",
) -> CanonicalFinancialStatements:
    """Map any provider shape into CanonicalFinancialStatements."""
    periods: List[Dict[str, Any]] = []
    q_keys = ("quarter_history", "quarters", "quarterly", "q_history")
    a_keys = ("annual_history", "annuals", "annual", "yearly")

    for key in q_keys:
        rows = provider_payload.get(key)
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict):
                    periods.append(_normalize_row(r, "quarterly"))
            break

    for key in a_keys:
        rows = provider_payload.get(key)
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict):
                    periods.append(_normalize_row(r, "annual"))
            break

    # FSE published shape
    stmts = provider_payload.get("statements")
    if isinstance(stmts, dict) and not periods:
        for ptype, key in (("quarterly", "quarters"), ("annual", "annuals")):
            rows = stmts.get(key) or stmts.get(ptype) or []
            if isinstance(rows, list):
                for r in rows:
                    if isinstance(r, dict):
                        periods.append(_normalize_row(r, ptype))

    # Already-canonical periods list
    if not periods and isinstance(provider_payload.get("periods"), list):
        for r in provider_payload["periods"]:
            if isinstance(r, dict):
                periods.append(
                    _normalize_row(r, str(r.get("period_type") or "quarterly"))
                )

    income = [p["income_statement"] | {"period": p["period"]} for p in periods]
    balance = [p["balance_sheet"] | {"period": p["period"]} for p in periods]
    cf = [p["cash_flow"] | {"period": p["period"]} for p in periods]
    capex = [
        {"period": p["period"], "capex": p["cash_flow"].get("capex")}
        for p in periods
        if p["cash_flow"].get("capex") is not None
    ]
    debt = [
        {"period": p["period"], "total_debt": p["balance_sheet"].get("total_debt")}
        for p in periods
        if p["balance_sheet"].get("total_debt") is not None
    ]
    cash = [
        {"period": p["period"], "cash": p["balance_sheet"].get("cash")}
        for p in periods
        if p["balance_sheet"].get("cash") is not None
    ]
    seg_rev = [p["segment_revenue"] | {"period": p["period"]} for p in periods if p["segment_revenue"]]
    seg_ebitda = [p["segment_ebitda"] | {"period": p["period"]} for p in periods if p["segment_ebitda"]]
    refs = []
    for p in periods:
        refs.extend(p.get("evidence_refs") or [])
    if source:
        refs.append(f"source:{source}")

    published = bool(periods) and bool(
        provider_payload.get("published", True)
        if "published" in provider_payload
        else True
    )
    # If explicit published=false from FSE, honor it when periods empty
    if provider_payload.get("published") is False and not periods:
        published = False
    if provider_payload.get("ok") is False and not periods:
        published = False

    latest_ratios = periods[0]["ratios"] if periods else {}
    return CanonicalFinancialStatements(
        company=company,
        ticker=ticker.upper(),
        periods=periods,
        income_statement=income,
        balance_sheet=balance,
        cash_flow=cf,
        segment_revenue=seg_rev,
        segment_ebitda=seg_ebitda,
        ratios=latest_ratios,
        capex=capex,
        debt=debt,
        cash=cash,
        metadata={
            "source": source,
            "mapped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "provider_keys_seen": sorted(provider_payload.keys())[:40],
            "canonical_line_items": list(CANONICAL_LINE_ITEMS),
            "rule": "Never expose provider-specific fields downstream",
        },
        evidence_references=sorted(set(str(x) for x in refs)),
        published=published and bool(periods),
        period_count=len(periods),
    )


def build_canonical_statements(
    ticker: str,
    *,
    company: Optional[str] = None,
    trigger_publish: bool = False,
) -> Dict[str, Any]:
    """Build canonical FS from FSE + earnings pack (provider-agnostic output)."""
    t = str(ticker or "").upper().strip()
    name = company or t
    payloads: List[tuple[str, Dict[str, Any]]] = []

    if trigger_publish:
        try:
            from financial_statements_engine.production import run_publish  # type: ignore

            run_publish(t)
        except Exception:
            pass

    try:
        from financial_statements_engine.production import get_statements  # type: ignore

        fs = get_statements(t)
        if isinstance(fs, dict):
            payloads.append(("financial_statements_engine", fs))
    except Exception:
        pass

    try:
        from earnings_intelligence.pack import build_earnings_pack  # type: ignore

        ep = build_earnings_pack(t)
        if isinstance(ep, dict):
            payloads.append(("earnings_intelligence", ep))
    except Exception:
        try:
            from earnings_intelligence.production import get_earnings_pack  # type: ignore

            ep = get_earnings_pack(t)
            if isinstance(ep, dict):
                payloads.append(("earnings_intelligence", ep))
        except Exception:
            pass

    # Prefer the payload with the most periods
    best: Optional[CanonicalFinancialStatements] = None
    for src, payload in payloads:
        cand = map_provider_to_canonical(payload, company=name, ticker=t, source=src)
        if best is None or len(cand.periods) > len(best.periods):
            best = cand

    if best is None:
        best = CanonicalFinancialStatements(
            company=name,
            ticker=t,
            metadata={"source": "none", "note": "no provider payloads"},
            published=False,
        )

    out = best.to_dict()
    out["ok"] = True
    out["zero_periods"] = len(best.periods) == 0
    return out
