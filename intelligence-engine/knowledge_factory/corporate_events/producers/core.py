"""Produce Corporate Event Objects from soft context — never invent."""

from __future__ import annotations

from typing import Any

from knowledge_factory.corporate_events.objects.event import build_event, event_fingerprint
from knowledge_factory.corporate_events.schema import canonicalize_type


def _importance_for(event_type: str, default: str = "Medium") -> str:
    et = canonicalize_type(event_type)
    critical = {"ceo_appointment", "ceo_resignation", "ceo_change", "merger", "acquisition", "covid", "litigation"}
    high = {"ipo", "buyback", "guidance", "quarterly_results", "annual_results", "major_contract", "rbi", "sebi"}
    low = {"sustainability", "csr", "carbon", "safety"}
    info = {"incorporation", "listing"}
    if et in critical:
        return "Critical"
    if et in high:
        return "High"
    if et in low:
        return "Low"
    if et in info:
        return "Informational"
    return default


def _normalize_date(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.upper() == "UNKNOWN":
        return None
    if len(s) == 4 and s.isdigit():
        return f"{s}-01-01"
    if len(s) >= 10:
        return s[:10]
    if len(s) == 7 and s[4] == "-":
        return f"{s}-01"
    return None


def _from_seed(ticker: str, seed: dict[str, Any], sector: str | None) -> dict[str, Any]:
    return build_event(
        company=ticker,
        event_type=seed["type"],
        announcement_date=seed["announcement_date"],
        effective_date=seed.get("effective_date"),
        available_from=seed.get("available_from"),
        title=seed["title"],
        source=seed.get("source") or "institutional_event_seed",
        collector="icei.collectors.seed",
        importance=seed.get("importance") or _importance_for(seed["type"]),
        confidence=float(seed.get("confidence") or 0.9),
        evidence=seed.get("evidence"),
        impact=seed.get("impact"),
        affected_companies=seed.get("affected_companies"),
        affected_sectors=seed.get("affected_sectors") or ([sector] if sector else None),
        affected_macro=seed.get("affected_macro"),
        sector=sector,
        derived_from=["institutional_event_seed"],
    )


def _from_soft_row(
    ticker: str,
    row: dict[str, Any],
    *,
    sector: str | None,
    collector: str,
    source_fallback: str,
    derived_from: str,
) -> dict[str, Any] | None:
    ann = _normalize_date(row.get("announcement_date") or row.get("date") or row.get("period"))
    if not ann:
        return None
    et = row.get("event_type") or row.get("type") or "strategy"
    title = row.get("title") or row.get("name") or f"{et} event"
    source = row.get("source") or source_fallback
    evidence = row.get("evidence")
    if isinstance(evidence, str):
        evidence = [evidence]
    if not evidence:
        evidence = [f"{ticker}-{canonicalize_type(str(et))}-{ann}"]
    return build_event(
        company=ticker,
        event_type=str(et),
        announcement_date=ann,
        effective_date=_normalize_date(row.get("effective_date")) or ann,
        available_from=_normalize_date(row.get("available_from")) or ann,
        title=str(title),
        source=str(source),
        collector=collector,
        importance=_importance_for(str(et)),
        confidence=float(row.get("confidence") or 0.7),
        evidence=evidence,
        sector=sector,
        affected_sectors=[sector] if sector else None,
        derived_from=[derived_from],
    )


def produce_events(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Deduped event list. Seeds first, then soft upstream (no invention)."""
    t = ctx["ticker"]
    sector = ctx.get("sector")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def _add(ev: dict[str, Any] | None) -> None:
        if not ev:
            return
        fp = event_fingerprint(
            company=ev["company"],
            event_type=ev["type"],
            announcement_date=ev["announcement_date"],
            title=ev["title"],
            source=ev["source"],
        )
        if fp in seen or ev["event_id"] in seen:
            return
        seen.add(fp)
        seen.add(ev["event_id"])
        out.append(ev)

    for seed in ctx.get("seeds") or []:
        _add(_from_seed(t, seed, sector))

    # Soft ICI curated seed timeline (may overlap; fingerprint dedupes)
    for row in ctx.get("ici_seed_timeline") or []:
        _add(
            _from_soft_row(
                t,
                row,
                sector=sector,
                collector="icei.collectors.company_intelligence_seed",
                source_fallback="company_intelligence_seed",
                derived_from="company_intelligence_seed_timeline",
            )
        )

    for row in ctx.get("ici_timeline") or []:
        _add(
            _from_soft_row(
                t,
                row,
                sector=sector,
                collector="icei.collectors.company_intelligence",
                source_fallback="company_intelligence",
                derived_from="company_intelligence_timeline",
            )
        )

    for row in ctx.get("hd_timeline") or []:
        _add(
            _from_soft_row(
                t,
                row,
                sector=sector,
                collector="icei.collectors.historical_depth",
                source_fallback="historical_depth",
                derived_from="historical_depth_timeline",
            )
        )

    out.sort(key=lambda e: (e.get("announcement_date") or "", e.get("event_id") or ""))
    return out
