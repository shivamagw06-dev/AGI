"""Production API for Valuation Intelligence — Institutional Consensus Dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from valuation_consensus.agi_panel import agi_panel
from valuation_consensus.parser import decode_content, diff_against_live, parse_sheet
from valuation_consensus.schema import SECTOR_CARDS
from valuation_consensus import store


def health() -> dict[str, Any]:
    live = store.load_live()
    n = int(live.get("row_count") or len(live.get("rows") or {}))
    status = "ok" if n > 0 else "empty"
    if n > 0 and n < 100:
        status = "degraded"
    return {
        "ok": True,
        "status": status,
        "engine": "valuation_consensus",
        "page": "Valuation Intelligence",
        "subtitle": "Institutional Consensus Dashboard",
        "row_count": n,
        "version_id": live.get("version_id"),
        "updated_at": live.get("updated_at"),
        "source_file": live.get("source_file"),
        "store_root": str(store.store_root()),
        "principle": {
            "market_consensus": "Capital IQ",
            "institutional_intelligence": "AGI",
            "excel_role": "import_source_only",
        },
    }


def _num(v: Any) -> Optional[float]:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def analytics() -> dict[str, Any]:
    live = store.load_live()
    rows = list((live.get("rows") or {}).values())
    upsides = [u for u in (_num(r.get("upside")) for r in rows) if u is not None]
    coverages = [c for c in (_num(r.get("coverage")) for r in rows) if c is not None]
    buys = sum(1 for r in rows if (_num(r.get("buy_count")) or 0) > (_num(r.get("hold_count")) or 0)
               and (_num(r.get("buy_count")) or 0) >= (_num(r.get("sell_count")) or 0)
               and (_num(r.get("buy_count")) or 0) > 0)
    holds = sum(1 for r in rows if (_num(r.get("hold_count")) or 0) > (_num(r.get("buy_count")) or 0)
                and (_num(r.get("hold_count")) or 0) >= (_num(r.get("sell_count")) or 0)
                and (_num(r.get("hold_count")) or 0) > 0)
    sells = sum(1 for r in rows if (_num(r.get("sell_count")) or 0) > (_num(r.get("buy_count")) or 0)
                and (_num(r.get("sell_count")) or 0) > (_num(r.get("hold_count")) or 0)
                and (_num(r.get("sell_count")) or 0) > 0)

    def _best(key, reverse=True):
        scored = [( _num(r.get(key)), r) for r in rows if _num(r.get(key)) is not None]
        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=reverse)
        r = scored[0][1]
        return {
            "ticker": r.get("ticker"),
            "company_name": r.get("company_name"),
            "value": scored[0][0],
        }

    sector_counts: dict[str, int] = {}
    for r in rows:
        s = str(r.get("sector") or "Unclassified").strip() or "Unclassified"
        sector_counts[s] = sector_counts.get(s, 0) + 1

    # Exact-label cards for the CapIQ GICS primary sectors, then any other
    # sector label the export actually contains. Counts always sum to the
    # row total — no sector is counted twice.
    cards: list[dict[str, Any]] = []
    named_lower = {n.lower() for n in SECTOR_CARDS}
    lower_counts = {s.lower(): (s, c) for s, c in sector_counts.items()}
    for name in SECTOR_CARDS:
        hit = lower_counts.get(name.lower())
        cards.append({"sector": name, "count": hit[1] if hit else 0})
    for s, c in sorted(sector_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if s.lower() not in named_lower:
            cards.append({"sector": s, "count": c})

    return {
        "ok": True,
        "total_companies": len(rows),
        "average_target_upside": round(sum(upsides) / len(upsides), 2) if upsides else None,
        "average_coverage": round(sum(coverages) / len(coverages), 2) if coverages else None,
        "buy_rated": buys,
        "hold_rated": holds,
        "sell_rated": sells,
        "highest_upside": _best("upside", True),
        "lowest_upside": _best("upside", False),
        "largest_market_cap": _best("market_cap", True),
        "most_covered": _best("coverage", True),
        "updated_at": live.get("updated_at"),
        "version_id": live.get("version_id"),
        "sector_cards": cards,
        "industries": sorted(
            {str(r.get("industry")).strip() for r in rows if r.get("industry")}
        ),
        "sectors": sorted({str(r.get("sector")).strip() for r in rows if r.get("sector")}),
    }


def _match_search(row: dict[str, Any], q: str) -> bool:
    if not q:
        return True
    blob = " ".join(
        str(row.get(k) or "")
        for k in (
            "ticker",
            "company_name",
            "security_name",
            "sector",
            "industry",
            "products",
            "description",
            "competitors",
            "parent",
            "investors",
        )
    ).lower()
    return q in blob


def _passes_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    if not filters:
        return True
    # CapIQ primary sectors are exact GICS labels — match exactly so
    # "Consumer Discretionary" never also pulls in "Consumer Staples".
    sector = filters.get("sector")
    if sector and str(row.get("sector") or "").strip().lower() != str(sector).strip().lower():
        return False
    industry = filters.get("industry")
    if industry and str(industry).lower() not in str(row.get("industry") or "").lower():
        return False
    country = filters.get("country")
    if country and str(country).lower() not in str(row.get("country") or "").lower():
        return False
    exchange = filters.get("exchange")
    if exchange and str(exchange).lower() not in str(
        row.get("exchange") or row.get("primary_exchange") or ""
    ).lower():
        return False

    def _range(field: str, lo_key: str, hi_key: str) -> bool:
        v = _num(row.get(field))
        lo, hi = _num(filters.get(lo_key)), _num(filters.get(hi_key))
        if lo is not None and (v is None or v < lo):
            return False
        if hi is not None and (v is None or v > hi):
            return False
        return True

    if not _range("market_cap", "market_cap_min", "market_cap_max"):
        return False
    if not _range("coverage", "coverage_min", "coverage_max"):
        return False
    if not _range("upside", "upside_min", "upside_max"):
        return False
    if not _range("buy_count", "buy_min", "buy_max"):
        return False
    if not _range("hold_count", "hold_min", "hold_max"):
        return False
    if not _range("sell_count", "sell_min", "sell_max"):
        return False
    if not _range("return_1y", "return_min", "return_max"):
        return False

    reco = str(filters.get("recommendation") or "").strip().lower()
    if reco:
        b = _num(row.get("buy_count")) or 0
        h = _num(row.get("hold_count")) or 0
        s = _num(row.get("sell_count")) or 0
        o = _num(row.get("outperform_count")) or 0
        if reco == "buy" and not (b >= h and b >= s and b > 0):
            return False
        if reco == "outperform" and not (o > 0 and o >= h):
            return False
        if reco == "hold" and not (h >= b and h >= s and h > 0):
            return False
        if reco == "sell" and not (s > b and s > h):
            return False
    return True


_SORT_KEYS = {
    "alphabetical": ("company_name", False),
    "company": ("company_name", False),
    "ticker": ("ticker", False),
    "sector": ("sector", False),
    "industry": ("industry", False),
    "market_cap": ("market_cap", True),
    "target": ("target_price", True),
    "target_price": ("target_price", True),
    "upside": ("upside", True),
    "buy": ("buy_count", True),
    "hold": ("hold_count", True),
    "sell": ("sell_count", True),
    "coverage": ("coverage", True),
    "revenue": ("revenue", True),
    "ebitda": ("ebitda", True),
    "return_1y": ("return_1y", True),
    "1y_return": ("return_1y", True),
    "return_5y": ("return_5y", True),
    "5y_return": ("return_5y", True),
    "cmp": ("cmp", True),
    "updated": ("updated_at", True),
}


def query_rows(
    *,
    q: str = "",
    page: int = 1,
    page_size: int = 50,
    sort: str = "coverage",
    sort_dir: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    live = store.load_live()
    rows = list((live.get("rows") or {}).values())
    qn = str(q or "").strip().lower()
    filt = filters or {}
    filtered = [r for r in rows if _match_search(r, qn) and _passes_filters(r, filt)]

    key, default_desc = _SORT_KEYS.get(str(sort or "coverage").lower(), ("coverage", True))
    descending = default_desc if sort_dir is None else str(sort_dir).lower() in {"desc", "descending", "-1"}

    # Rows without a value for the sort column always sink to the bottom,
    # in both directions — a null market cap must never outrank a real one.
    def sort_val(r: dict[str, Any]):
        v = r.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        if v is None or v == "":
            return None
        return str(v).lower()

    with_value = [r for r in filtered if sort_val(r) is not None]
    without_value = [r for r in filtered if sort_val(r) is None]
    with_value.sort(key=sort_val, reverse=descending)
    without_value.sort(key=lambda r: str(r.get("company_name") or r.get("ticker") or "").lower())
    filtered = with_value + without_value

    page = max(1, int(page or 1))
    page_size = max(1, min(500, int(page_size or 50)))
    total = len(filtered)
    start = (page - 1) * page_size
    chunk = filtered[start : start + page_size]

    # Compact list projection for table
    items = []
    for r in chunk:
        items.append(
            {
                "ticker": r.get("ticker"),
                "company_name": r.get("company_name"),
                "sector": r.get("sector"),
                "industry": r.get("industry"),
                "cmp": r.get("cmp"),
                "target_price": r.get("target_price"),
                "upside": r.get("upside"),
                "buy_count": r.get("buy_count"),
                "outperform_count": r.get("outperform_count"),
                "hold_count": r.get("hold_count"),
                "sell_count": r.get("sell_count"),
                "coverage": r.get("coverage"),
                "market_cap": r.get("market_cap"),
                "updated_at": r.get("updated_at"),
            }
        )

    return {
        "ok": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
        "sort": sort,
        "sort_dir": "desc" if descending else "asc",
        "items": items,
        "updated_at": live.get("updated_at"),
        "version_id": live.get("version_id"),
    }


def company_detail(ticker: str) -> dict[str, Any]:
    row = store.get_row(ticker)
    if not row:
        return {"ok": False, "error": "not_found", "ticker": str(ticker or "").upper()}
    panel = agi_panel(str(ticker))
    return {
        "ok": True,
        "ticker": row.get("ticker"),
        "market_consensus": {
            "source": "capital_iq",
            "label": "Market Consensus",
            "row": row,
        },
        "overview": {
            "business_description": row.get("description"),
            "sector": row.get("sector"),
            "industry": row.get("industry"),
            "country": row.get("country"),
            "exchange": row.get("exchange") or row.get("primary_exchange"),
            "parent": row.get("parent"),
            "company_type": row.get("company_type"),
            "trading_status": row.get("trading_status"),
            "website": row.get("website"),
        },
        "performance": {
            "ytd": row.get("return_ytd"),
            "1d": row.get("return_1d"),
            "1w": row.get("return_1w"),
            "1m": row.get("return_1m"),
            "3m": row.get("return_3m"),
            "6m": row.get("return_6m"),
            "9m": row.get("return_9m"),
            "1y": row.get("return_1y"),
            "3y": row.get("return_3y"),
            "5y": row.get("return_5y"),
            "average_volume": row.get("avg_volume"),
        },
        "valuation": {
            "current_price": row.get("cmp"),
            "consensus_target": row.get("target_price"),
            "high_target": row.get("target_high"),
            "low_target": row.get("target_low"),
            "target_std_dev": row.get("target_std_dev"),
            "upside": row.get("upside"),
            "buy": row.get("buy_count"),
            "outperform": row.get("outperform_count"),
            "hold": row.get("hold_count"),
            "sell": row.get("sell_count"),
            "no_opinion": row.get("no_opinion_count"),
            "coverage_count": row.get("coverage"),
        },
        "business": {
            "business_description": row.get("description"),
            "products": row.get("products"),
            "competitors": row.get("competitors"),
            "investors": row.get("investors"),
            "subsidiaries": row.get("subsidiaries"),
            "industry_classification": row.get("industry_classification"),
        },
        "research": {
            "recent_research": panel.get("latest_research"),
            "open_agi_research": panel["links"].get("research_intelligence"),
            "investment_intelligence": panel["links"].get("investment_intelligence"),
            "business_intelligence": panel["links"].get("business_intelligence"),
            "industry_intelligence": panel["links"].get("industry_intelligence"),
            "research_intelligence": panel["links"].get("research_intelligence"),
        },
        "agi_intelligence": panel,
        "integrations": panel.get("links"),
    }


def import_preview(
    *,
    filename: str,
    content_base64: str | None = None,
    content_bytes: bytes | None = None,
    sheet_name: Any = 0,
    column_names: list[str] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    raw = decode_content(content_base64, content_bytes)
    parsed = parse_sheet(raw, filename, sheet_name=sheet_name, column_names=column_names)
    if not parsed.get("ok"):
        return parsed
    live = store.load_live()
    diff = diff_against_live(parsed["rows"], live.get("rows") or {})
    draft = store.save_import_draft(
        {
            "status": "preview",
            "filename": filename,
            "imported_by": actor or "admin",
            "row_count": parsed["row_count"],
            "unresolved_count": parsed["unresolved_count"],
            "unresolved": parsed.get("unresolved"),
            "columns_mapped": parsed.get("columns_mapped"),
            "columns_unmapped": parsed.get("columns_unmapped"),
            "resolve_stats": parsed.get("resolve_stats"),
            "diff": diff,
            "rows": parsed["rows"],
            "validated": False,
        }
    )
    # Don't echo full rows in HTTP response — keep preview compact
    return {
        "ok": True,
        "import_id": draft["import_id"],
        "filename": filename,
        "row_count": parsed["row_count"],
        "unresolved_count": parsed["unresolved_count"],
        "unresolved": parsed.get("unresolved"),
        "columns_mapped": parsed.get("columns_mapped"),
        "columns_unmapped": parsed.get("columns_unmapped"),
        "resolve_stats": parsed.get("resolve_stats"),
        "diff": diff,
        "status": "preview",
        "sample": list(parsed["rows"].values())[:5],
    }


def import_validate(import_id: str) -> dict[str, Any]:
    draft = store.load_import_draft(import_id)
    if not draft:
        return {"ok": False, "error": "import_not_found"}
    rows = draft.get("rows") or {}
    errors: list[str] = []
    if not rows:
        errors.append("no_rows")
    missing_name = sum(1 for r in rows.values() if not (r.get("company_name") or r.get("security_name")))
    if missing_name:
        errors.append(f"missing_company_name:{missing_name}")
    draft["validated"] = len(errors) == 0
    draft["validation_errors"] = errors
    draft["status"] = "validated" if not errors else "invalid"
    store.save_import_draft(draft)
    return {
        "ok": len(errors) == 0,
        "import_id": import_id,
        "validated": draft["validated"],
        "errors": errors,
        "row_count": draft.get("row_count"),
        "diff": draft.get("diff"),
    }


def import_publish(import_id: str, *, actor: str | None = None) -> dict[str, Any]:
    draft = store.load_import_draft(import_id)
    if not draft:
        return {"ok": False, "error": "import_not_found"}
    if draft.get("status") == "invalid":
        return {"ok": False, "error": "import_invalid", "errors": draft.get("validation_errors")}
    # Auto-validate if not yet validated
    if not draft.get("validated"):
        v = import_validate(import_id)
        if not v.get("ok"):
            return v
        draft = store.load_import_draft(import_id) or draft
    rows = draft.get("rows") or {}
    if not isinstance(rows, dict) or not rows:
        return {"ok": False, "error": "no_rows"}
    published = store.publish_rows(
        {k: dict(v) for k, v in rows.items()},
        source_file=str(draft.get("filename") or "upload.xlsx"),
        imported_by=actor or draft.get("imported_by") or "admin",
        import_id=import_id,
    )
    draft["status"] = "published"
    draft["published_version_id"] = published.get("version_id")
    store.save_import_draft(draft)
    return {
        "ok": True,
        "import_id": import_id,
        "version_id": published.get("version_id"),
        "row_count": published.get("row_count"),
        "diff": published.get("diff"),
        "updated_at": published.get("updated_at"),
    }


def import_rollback(version_id: str, *, actor: str | None = None) -> dict[str, Any]:
    try:
        published = store.rollback_to(version_id, actor=actor)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "version_id": published.get("version_id"),
        "rolled_back_to": version_id,
        "row_count": published.get("row_count"),
        "updated_at": published.get("updated_at"),
    }


def list_imports() -> dict[str, Any]:
    return {"ok": True, "imports": store.list_import_drafts()}


def list_versions() -> dict[str, Any]:
    return {"ok": True, "versions": store.list_versions(), "audit": store.read_audit(40)}


def export_snapshot() -> dict[str, Any]:
    live = store.load_live()
    return {
        "ok": True,
        "version_id": live.get("version_id"),
        "updated_at": live.get("updated_at"),
        "source_file": live.get("source_file"),
        "row_count": live.get("row_count"),
        "rows": live.get("rows") or {},
    }


def seed_from_path(path: str | Path, *, actor: str = "seed") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": f"file_not_found:{p}"}
    preview = import_preview(
        filename=p.name,
        content_bytes=p.read_bytes(),
        actor=actor,
    )
    if not preview.get("ok"):
        return preview
    return import_publish(preview["import_id"], actor=actor)
