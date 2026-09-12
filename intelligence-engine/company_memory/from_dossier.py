"""Build compiler injection from an existing CID dossier (avoid re-fetch)."""

from __future__ import annotations

from typing import Any


def injected_from_dossier(dossier: dict[str, Any]) -> dict[str, Any]:
    """Map CID soft-attached sections into compiler injected packs."""
    md = dossier.get("market_data") if isinstance(dossier.get("market_data"), dict) else {}
    lmc = md.get("live_market_context") if isinstance(md.get("live_market_context"), dict) else {}
    own = dossier.get("ownership") if isinstance(dossier.get("ownership"), dict) else {}
    oi = dossier.get("ownership_intelligence") if isinstance(dossier.get("ownership_intelligence"), dict) else {}
    fs = dossier.get("financial_statements") if isinstance(dossier.get("financial_statements"), dict) else {}
    fin = dossier.get("financials") if isinstance(dossier.get("financials"), dict) else {}
    val = dossier.get("valuation") if isinstance(dossier.get("valuation"), dict) else {}
    vi = dossier.get("valuation_intelligence") if isinstance(dossier.get("valuation_intelligence"), dict) else {}

    ownership_pack = {
        "ok": own.get("promoter") is not None or own.get("fii") is not None or oi.get("ok"),
        "promoter": own.get("promoter"),
        "fii": own.get("fii"),
        "dii": own.get("dii"),
        "mutual_funds": own.get("mutual_funds"),
        "insurance": own.get("insurance"),
        "promoter_pledge_pct": own.get("pledged") if own.get("pledged") is not None else own.get("promoter_pledge"),
        "as_of_quarter": own.get("as_of_quarter") or own.get("quarter_label"),
        "quarter_history": own.get("history") or (own.get("quarter_history") or []),
        "qoq": own.get("qoq"),
        "source": own.get("source") or "cid.ownership",
        "freshness": own.get("freshness"),
    }

    # Reconstruct a minimal earnings pack from CID financial_statements / metrics
    annual = []
    quarterly = []
    inc = fs.get("income_statement") if isinstance(fs.get("income_statement"), dict) else {}
    bal = fs.get("balance_sheet") if isinstance(fs.get("balance_sheet"), dict) else {}
    cf = fs.get("cash_flow") if isinstance(fs.get("cash_flow"), dict) else {}
    for row in (inc.get("annual") or [])[:15]:
        if not isinstance(row, dict):
            continue
        accounts = row.get("accounts") if isinstance(row.get("accounts"), dict) else {}
        annual.append(
            {
                "period_end": row.get("period_end"),
                "fiscal_year_label": row.get("label"),
                "income_statement": accounts,
                "balance_sheet": {},
                "cash_flow": {},
            }
        )
    # Attach matching BS/CF by period when present
    bal_by = {r.get("period_end"): (r.get("accounts") or {}) for r in (bal.get("annual") or []) if isinstance(r, dict)}
    cf_by = {r.get("period_end"): (r.get("accounts") or {}) for r in (cf.get("annual") or []) if isinstance(r, dict)}
    for a in annual:
        pe = a.get("period_end")
        if pe in bal_by:
            a["balance_sheet"] = bal_by[pe]
        if pe in cf_by:
            a["cash_flow"] = cf_by[pe]
    for row in (inc.get("quarterly") or [])[:20]:
        if not isinstance(row, dict):
            continue
        quarterly.append(
            {
                "period_end": row.get("period_end"),
                "quarter_label": row.get("label"),
                "income_statement": row.get("accounts") or {},
            }
        )

    ttm = fs.get("ttm") if isinstance(fs.get("ttm"), dict) else {}
    earnings_pack = {
        "ok": bool(annual or quarterly or fin.get("revenue") is not None),
        "coverage_pct": fin.get("coverage_pct") or (100 if annual else 0),
        "annual_history": annual,
        "quarter_history": quarterly,
        "ttm": ttm if ttm else {"available": fin.get("revenue") is not None, "income_statement": {
            "revenue_from_operations": fin.get("revenue") or fin.get("total_revenue"),
            "ebitda": fin.get("ebitda"),
            "pat": fin.get("net_income"),
            "eps_basic": fin.get("eps"),
        }},
        "metrics": {
            "yoy_growth": {
                "revenue_growth_pct": fin.get("revenue_growth"),
                "pat_growth_pct": fin.get("earnings_growth"),
            },
            "latest_annual": {
                "roe_pct": fin.get("roe"),
                "roce_pct": fin.get("roce"),
                "ebitda_margin_pct": fin.get("ebitda_margin"),
                "pat_margin_pct": fin.get("pat_margin"),
                "debt_to_equity": fin.get("debt_to_equity"),
            },
            "latest_quarter": {
                "ebitda_margin_pct": fin.get("ebitda_margin"),
                "pat_margin_pct": fin.get("pat_margin"),
            },
        },
        "source": "cid.financial_statements",
    }

    valuation_pack = {
        "ok": val.get("pe") is not None or vi.get("ok"),
        "current": val.get("current") or {
            "pe": val.get("pe"),
            "pb": val.get("pb"),
            "ev_ebitda": val.get("ev_ebitda"),
            "peg": val.get("peg"),
            "forward_pe": val.get("forward_pe"),
        },
        "historical": {"pe": val.get("pe_range")} if val.get("pe_range") else (val.get("historical") or {}),
        "relative": val.get("relative") or {},
        "peer_universe": {
            "resolved": bool((val.get("peers") or {}).get("universe") or (vi.get("peer_universe") or {}).get("primary_peers")),
            "primary_peers": (val.get("peers") or {}).get("universe")
            or (vi.get("peer_universe") or {}).get("primary_peers")
            or [],
            "sector": (val.get("peers") or {}).get("sector"),
            "industry": (val.get("peers") or {}).get("industry"),
            "source": (val.get("peers") or {}).get("source"),
        },
        "stance": (val.get("narrative") or {}).get("stance") if isinstance(val.get("narrative"), dict) else vi.get("stance"),
        "observations": (val.get("narrative") or {}).get("observations")
        if isinstance(val.get("narrative"), dict)
        else vi.get("observations"),
        "lineage": val.get("lineage") or [],
        "freshness": val.get("freshness"),
        "source": "cid.valuation",
    }

    market_pack = {
        "ok": md.get("current_price") is not None or lmc.get("ok"),
        "ltp": md.get("current_price") or lmc.get("ltp"),
        "provider": md.get("provider") or lmc.get("provider"),
        "as_of": md.get("as_of") or lmc.get("as_of"),
    }

    return {
        "market": market_pack,
        "ownership": ownership_pack,
        "earnings": earnings_pack,
        "valuation": valuation_pack,
    }
