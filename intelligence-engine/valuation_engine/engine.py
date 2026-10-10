"""The one place a valuation multiple is computed.

Before this, three surfaces produced valuation numbers independently: the
terminal read a committed Yahoo JSON snapshot, Ask composed live quotes against
NSE filings, and the warehouse computed a third series that nothing displayed.
They could disagree, and nothing on screen explained why.

This engine reads the warehouse and only the warehouse. Vendors write into the
warehouse through the DQIV gateway, so a vendor change never reaches a formula:

    Upstox / Yahoo / Capital IQ -> DQIV -> Warehouse -> engine -> consumers

Every value carries where it came from and what it was computed from. A null
names the input it lacked rather than rendering as an empty cell, because on a
valuation screen a blank and a zero are very different claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from institutional_warehouse import units
from valuation_engine import graph

#: Metrics whose value is a currency amount rather than a multiple.
_MONEY_NODES = frozenset({
    "cmp", "market_cap", "enterprise_value", "book_value_per_share", "eps",
    "dividend_per_share", "target_price", "forward_eps",
})


@dataclass
class Value:
    """One computed figure with the evidence behind it."""

    metric: str
    value: Optional[float] = None
    inputs: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def available(self) -> bool:
        return self.value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "available": self.available,
            "inputs": self.inputs,
            "sources": sorted(set(self.sources)),
            "missing": self.missing,
            "note": self.note,
        }


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out else out  # reject NaN


def _source_of(row: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(row, dict):
        return None
    meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
    return row.get("source") or meta.get("source")


def read_inputs(record: dict[str, Any]) -> dict[str, Value]:
    """Warehouse record into engine input nodes, in one scale.

    Statement aggregates are stored in INR million while price and share count
    are in rupees, so the aggregates are converted here. Every multiple below
    then divides rupees by rupees.
    """
    price = record.get("latest_price") or {}
    annual = record.get("latest_annual") or {}
    consensus = record.get("consensus") or {}
    ratios = record.get("ratios") or {}

    price_source = _source_of(price)
    annual_source = _source_of(annual)
    consensus_source = _source_of(consensus)

    def leaf(metric: str, value: Any, source: Optional[str]) -> Value:
        number = _num(value)
        return Value(
            metric=metric,
            value=number,
            sources=[source] if source else [],
            missing=[] if number is not None else [metric],
        )

    cmp_price = _num(price.get("close")) or _num(price.get("adjusted_close"))
    shares = _num(price.get("shares_outstanding")) or _num(annual.get("shares_outstanding"))

    return {
        "cmp": leaf("cmp", cmp_price, price_source),
        "shares_outstanding": leaf("shares_outstanding", shares, price_source or annual_source),
        "eps": leaf("eps", annual.get("eps"), annual_source),
        "book_value_per_share": leaf("book_value_per_share", annual.get("book_value"), annual_source),
        # Aggregates: INR million in the warehouse, rupees in the engine.
        "revenue": leaf("revenue", units.to_rupees(annual.get("revenue")), annual_source),
        "ebitda": leaf("ebitda", units.to_rupees(annual.get("ebitda")), annual_source),
        "debt": leaf("debt", units.to_rupees(annual.get("debt")), annual_source),
        "cash": leaf("cash", units.to_rupees(annual.get("cash")), annual_source),
        "equity": leaf("equity", units.to_rupees(annual.get("equity")), annual_source),
        "pat": leaf("pat", units.to_rupees(annual.get("pat")), annual_source),
        "dividend_per_share": leaf("dividend_per_share", price.get("dividend"), price_source),
        "target_price": leaf("target_price", consensus.get("target_price"), consensus_source),
        "forward_eps": leaf("forward_eps", consensus.get("forward_eps") or ratios.get("forward_eps"),
                            consensus_source or _source_of(ratios)),
    }


def _combine(metric: str, values: dict[str, Value]) -> tuple[list[str], list[str]]:
    """Sources and missing inputs inherited from a node's dependencies."""
    sources: list[str] = []
    missing: list[str] = []
    for dependency in graph.inputs_of(metric):
        upstream = values.get(dependency)
        if upstream is None or not upstream.available:
            missing.append(dependency)
            continue
        sources.extend(upstream.sources)
    return sources, missing


def _derive(metric: str, values: dict[str, Value]) -> Value:
    sources, missing = _combine(metric, values)
    if missing:
        return Value(metric=metric, sources=sources, missing=missing,
                     note=f"needs {', '.join(missing)}")

    def v(name: str) -> float:
        return float(values[name].value)  # type: ignore[arg-type]

    result: Optional[float] = None
    note = ""

    if metric == "market_cap":
        result = v("cmp") * v("shares_outstanding")
    elif metric == "enterprise_value":
        result = v("market_cap") + v("debt") - v("cash")
    elif metric == "pe":
        result = v("cmp") / v("eps") if v("eps") > 0 else None
        note = "" if result is not None else "earnings not positive"
    elif metric == "forward_pe":
        result = v("cmp") / v("forward_eps") if v("forward_eps") > 0 else None
        note = "" if result is not None else "forward earnings not positive"
    elif metric == "pb":
        result = v("cmp") / v("book_value_per_share") if v("book_value_per_share") > 0 else None
        note = "" if result is not None else "book value not positive"
    elif metric == "ev_ebitda":
        result = v("enterprise_value") / v("ebitda") if v("ebitda") > 0 else None
        note = "" if result is not None else "EBITDA not positive"
    elif metric == "ev_sales":
        result = v("enterprise_value") / v("revenue") if v("revenue") > 0 else None
        note = "" if result is not None else "revenue not positive"
    elif metric == "ps":
        result = v("market_cap") / v("revenue") if v("revenue") > 0 else None
        note = "" if result is not None else "revenue not positive"
    elif metric == "dividend_yield":
        result = 100.0 * v("dividend_per_share") / v("cmp") if v("cmp") > 0 else None
    elif metric == "roe":
        result = 100.0 * v("pat") / v("equity") if v("equity") > 0 else None
        note = "" if result is not None else "equity not positive"
    elif metric == "upside":
        result = 100.0 * (v("target_price") - v("cmp")) / v("cmp") if v("cmp") > 0 else None

    rounded = None if result is None else round(result, 2 if metric in _MONEY_NODES else 4)
    return Value(metric=metric, value=rounded, sources=sources,
                 inputs={d: values[d].value for d in graph.inputs_of(metric)},
                 missing=[] if rounded is not None else list(graph.inputs_of(metric)),
                 note=note)


def _overlay_provider_ratios(values: dict[str, Value], record: dict[str, Any]) -> None:
    """Prefer Upstox key-ratios for PE/PB/ROA/ROE/ROCE/EV-EBITDA when present.

    Provider values are authoritative. AGI still computes market cap, EV,
    price/sales, dividend yield, percentiles and relative scores.
    """
    pack = record.get("provider_ratios") or {}
    ratios = pack.get("ratios") if isinstance(pack.get("ratios"), dict) else pack
    if not isinstance(ratios, dict):
        return
    for metric in graph.PROVIDER_OWNED_RATIOS:
        block = ratios.get(metric)
        if block is None:
            continue
        if isinstance(block, dict):
            number = _num(block.get("company_value") if "company_value" in block else block.get("value"))
            source = block.get("source") or "upstox"
        else:
            number = _num(block)
            source = "upstox"
        if number is None:
            continue
        values[metric] = Value(
            metric=metric,
            value=round(number, 4),
            sources=[str(source)],
            missing=[],
            note="provider",
            inputs={"provider": source},
        )


def compute(record: dict[str, Any], *, metrics: Optional[list[str]] = None) -> dict[str, Value]:
    """Every valuation figure for one company, in dependency order."""
    values = read_inputs(record)
    _overlay_provider_ratios(values, record)
    for metric in graph.topological():
        if metric in values:
            continue  # an input or provider ratio, already set
        if metric in ("sector_premium", "historical_percentile", "relative_score"):
            continue  # need peers or history; the service layer supplies them
        values[metric] = _derive(metric, values)

    if metrics:
        wanted = set(metrics)
        return {k: v for k, v in values.items() if k in wanted}
    return values


def recompute_after(record: dict[str, Any], changed: str) -> dict[str, Value]:
    """Only the nodes downstream of ``changed``.

    A quote refresh touches ``cmp``, which should not rebuild statement-derived
    inputs that did not move.
    """
    values = read_inputs(record)
    for metric in graph.dependents_of(changed):
        if metric in ("sector_premium", "historical_percentile", "relative_score"):
            continue
        values[metric] = _derive(metric, values)
    dirty = set(graph.dependents_of(changed)) | {changed}
    return {k: v for k, v in values.items() if k in dirty}
