"""Valuation Intelligence Pack — synthesise market + financials + peers into opinion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from valuation_intelligence.growth import growth_from_earnings, profitability_from_earnings
from valuation_intelligence.history import historical_bands_for_symbol, historical_windows_for_symbol
from valuation_intelligence.conditioning import quality_matrix, reconcile_sources
from valuation_intelligence.market import (
    compute_multiples,
    estimate_market_cap,
    fetch_quote,
    light_fundamentals,
    _from_earnings_pack,
)
from valuation_intelligence.narrative import build_narrative
from valuation_intelligence.peers import resolve_peers
from valuation_intelligence.relative import build_relative, peer_medians
from valuation_intelligence.schema import (
    ENGINE_CODE,
    FRESHNESS_SLA_DAYS,
    VERSION,
    PeerSnapshot,
    SubjectMultiples,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _subject_earnings(
    ticker: str,
    *,
    force: bool,
    injected_earnings: dict[str, Any] | None,
    skip_earnings_fetch: bool,
) -> dict[str, Any] | None:
    if injected_earnings is not None:
        return injected_earnings
    if skip_earnings_fetch:
        return None
    try:
        from earnings_intelligence.production import analyse as earnings_analyse

        pack = earnings_analyse(
            ticker,
            force=force,
            quarterly_xbrl=4,
            annual_xbrl=5,
            persist=False,
        )
        return pack if pack.get("ok") else pack
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:160]}


def _peer_snapshot(
    peer: str,
    *,
    force: bool,
    injected_peer_quotes: dict[str, Any] | None,
    injected_peer_fundamentals: dict[str, Any] | None,
) -> PeerSnapshot:
    q_inj = (injected_peer_quotes or {}).get(peer)
    f_inj = (injected_peer_fundamentals or {}).get(peer)
    quote = fetch_quote(peer, force=force, injected=q_inj)
    fund = light_fundamentals(peer, injected_earnings=f_inj) if f_inj is not None else light_fundamentals(peer)
    # If peer injection is a full earnings-like dict without our light shape, normalise
    if f_inj is not None and "ttm_eps" not in fund and f_inj.get("ok") is not False:
        if "ttm" in f_inj or "annual_history" in f_inj:
            fund = _from_earnings_pack(peer, f_inj)
    price = quote.get("ltp")
    mcap = estimate_market_cap(price, fund)
    mult = compute_multiples(price=price, fundamentals=fund, market_cap=mcap)
    growth = growth_from_earnings(f_inj if isinstance(f_inj, dict) else None)
    return PeerSnapshot(
        ticker=peer,
        price=price,
        pe=mult.get("pe"),
        pb=mult.get("pb"),
        ev_ebitda=mult.get("ev_ebitda"),
        roe=_f(fund.get("roe_pct")),
        eps_cagr_3y=growth.eps_cagr_3y,
        net_debt=mult.get("net_debt"),
        market_cap=mcap,
        source=fund.get("source") or quote.get("provider"),
    )


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _annual_eps_pairs(earnings: dict[str, Any] | None) -> list[tuple[str, float]]:
    if not isinstance(earnings, dict):
        return []
    out: list[tuple[str, float]] = []
    for r in earnings.get("annual_history") or []:
        if not isinstance(r, dict):
            continue
        inc = r.get("income_statement") or {}
        eps = _f(inc.get("eps_basic") or inc.get("eps_diluted"))
        pe = r.get("period_end")
        if eps is not None and pe:
            out.append((str(pe)[:10], eps))
    if not out and isinstance(earnings.get("annual"), list):
        for r in earnings["annual"]:
            if not isinstance(r, dict):
                continue
            eps = _f(r.get("eps"))
            pe = r.get("period_end") or ""
            if eps is not None:
                out.append((str(pe)[:10], eps))
    return out


def _coverage_pct(
    *,
    peers_resolved: bool,
    subject: SubjectMultiples,
    relative: dict[str, Any],
    historical: dict[str, Any],
    narrative_n: int,
) -> float:
    score = 0.0
    if peers_resolved:
        score += 20
    if subject.pe is not None:
        score += 15
    if subject.pb is not None:
        score += 10
    if subject.ev_ebitda is not None:
        score += 10
    if subject.peg is not None:
        score += 5
    if relative.get("pe") and relative["pe"].get("peer_median") is not None:
        score += 15
    if historical.get("pe"):
        score += 15
    if narrative_n:
        score += 10
    return min(100.0, score)


def build_valuation_pack(
    ticker: str,
    *,
    force: bool = False,
    max_peers: int = 5,
    include_secondary: bool = False,
    skip_earnings_fetch: bool = False,
    skip_peer_fetch: bool = False,
    injected_quote: dict[str, Any] | None = None,
    injected_earnings: dict[str, Any] | None = None,
    injected_peer_quotes: dict[str, Any] | None = None,
    injected_peer_fundamentals: dict[str, Any] | None = None,
    injected_history: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    t0 = datetime.now(timezone.utc)
    key = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    if key == "ZOMATO":
        key = "ETERNAL"

    peer_meta = resolve_peers(key)
    peer_list = list(peer_meta.get("primary_peers") or [])
    if include_secondary:
        peer_list = peer_list + list(peer_meta.get("secondary_peers") or [])
    peer_list = peer_list[: max(0, int(max_peers))]

    earnings = _subject_earnings(
        key,
        force=force,
        injected_earnings=injected_earnings,
        skip_earnings_fetch=skip_earnings_fetch,
    )
    fund = (
        _from_earnings_pack(key, earnings)
        if isinstance(earnings, dict) and (earnings.get("ok") or earnings.get("ttm") or earnings.get("annual_history") or earnings.get("annual"))
        else light_fundamentals(key, injected_earnings=injected_earnings)
    )

    quote = fetch_quote(key, force=force, injected=injected_quote)
    price = quote.get("ltp")
    mcap = estimate_market_cap(price, fund)
    mult = compute_multiples(price=price, fundamentals=fund, market_cap=mcap)
    # Prefer growth-adjusted PEG using 3Y EPS CAGR when available
    growth = growth_from_earnings(earnings if isinstance(earnings, dict) else None)
    if mult.get("pe") is not None and growth.eps_cagr_3y not in (None, 0) and (growth.eps_cagr_3y or 0) > 0:
        mult["peg"] = round(float(mult["pe"]) / float(growth.eps_cagr_3y), 4)

    subject = SubjectMultiples(
        price=mult.get("price"),
        market_cap=mult.get("market_cap"),
        shares_outstanding=_f(fund.get("shares_outstanding")),
        enterprise_value=mult.get("enterprise_value"),
        net_debt=mult.get("net_debt"),
        pe=mult.get("pe"),
        forward_pe=mult.get("forward_pe"),
        pb=mult.get("pb"),
        ev_ebitda=mult.get("ev_ebitda"),
        ev_sales=mult.get("ev_sales"),
        price_to_sales=mult.get("price_to_sales"),
        price_to_cash_flow=mult.get("price_to_cash_flow"),
        peg=mult.get("peg"),
    )

    quality = profitability_from_earnings(earnings if isinstance(earnings, dict) else None)
    if quality.get("roe") is None:
        quality["roe"] = _f(fund.get("roe_pct"))
    if quality.get("roce") is None:
        quality["roce"] = _f(fund.get("roce_pct"))
    if quality.get("ebitda_margin") is None:
        quality["ebitda_margin"] = _f(fund.get("ebitda_margin_pct"))
    if quality.get("ebit_margin") is None:
        quality["ebit_margin"] = _f(fund.get("ebit_margin_pct"))
    if quality.get("pat_margin") is None:
        quality["pat_margin"] = _f(fund.get("pat_margin_pct"))

    peers: list[PeerSnapshot] = []
    peer_errors: list[dict[str, str]] = []
    if not skip_peer_fetch:
        for p in peer_list:
            try:
                peers.append(
                    _peer_snapshot(
                        p,
                        force=force,
                        injected_peer_quotes=injected_peer_quotes,
                        injected_peer_fundamentals=injected_peer_fundamentals,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                peer_errors.append({"ticker": p, "error": str(exc)[:120]})

    relative_objs = build_relative(
        subject,
        peers,
        subject_roe=quality.get("roe"),
        subject_eps_cagr=growth.eps_cagr_3y,
        subject_net_debt=subject.net_debt,
        subject_equity=_f(fund.get("equity")),
    )
    relative = {k: v.to_dict() for k, v in relative_objs.items()}
    medians = peer_medians(peers)

    hist_objs = historical_bands_for_symbol(
        key,
        current_pe=subject.pe,
        current_pb=subject.pb,
        current_ev_ebitda=subject.ev_ebitda,
        annual_eps=_annual_eps_pairs(earnings if isinstance(earnings, dict) else None),
        injected_series=injected_history,
    )
    historical = {k: v.to_dict() for k, v in hist_objs.items()}
    window_objs = historical_windows_for_symbol(
        key,
        current={"pe": subject.pe, "pb": subject.pb, "ev_ebitda": subject.ev_ebitda, "ev_sales": subject.ev_sales},
    )
    historical_windows = {
        metric: {window: band.to_dict() for window, band in windows.items()}
        for metric, windows in window_objs.items()
    }

    pe_rel = relative.get("pe") or {}
    pe_hist = historical.get("pe") or {}
    matrix = quality_matrix(
        historical_percentile=pe_hist.get("percentile"),
        peer_premium_pct=pe_rel.get("premium_pct"),
        roe=quality.get("roe"), peer_roe=medians.get("median_roe"),
        eps_cagr=growth.eps_cagr_3y, peer_eps_cagr=medians.get("median_eps_cagr_3y"),
    )
    # The workbook observation is fiscal-year-end evidence. Reconcile only when
    # another source explicitly represents the same current basis; otherwise
    # preserve it as historical context rather than manufacturing a conflict.
    reconciliation = {
        metric: reconcile_sources({"afe_current": current_value})
        for metric, current_value in {"pe": subject.pe, "pb": subject.pb, "ev_ebitda": subject.ev_ebitda}.items()
    }

    stance, observations = build_narrative(
        relative=relative_objs,
        historical=hist_objs,
        quality=quality,
        growth=growth.to_dict(),
    )

    # Freshness from quote / earnings
    as_of = quote.get("as_of")
    if not as_of and isinstance(earnings, dict):
        as_of = earnings.get("generated_at")
    if not as_of and isinstance(earnings, dict):
        lq = earnings.get("latest_quarter") if isinstance(earnings.get("latest_quarter"), dict) else {}
        as_of = lq.get("period_end") or lq.get("filing_date")
    age_days = None
    if isinstance(as_of, str) and len(as_of) >= 10:
        try:
            dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
        except ValueError:
            age_days = None

    coverage = _coverage_pct(
        peers_resolved=bool(peer_meta.get("resolved")),
        subject=subject,
        relative=relative,
        historical=historical,
        narrative_n=len(observations),
    )
    confidence = round(min(0.95, 0.35 + coverage / 100.0 * 0.6), 3)
    if subject.pe is None and subject.pb is None:
        confidence = round(confidence * 0.5, 3)

    ok = bool(peer_meta.get("resolved")) and (subject.pe is not None or subject.pb is not None or subject.ev_ebitda is not None)
    latency_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

    lineage = [
        {"source": "valuation_peer_registry", "ref": peer_meta.get("source"), "ticker": key},
        {"source": quote.get("provider") or "market", "ref": "ltp", "as_of": quote.get("as_of")},
        {
            "source": fund.get("source") or "earnings",
            "ref": "fundamentals",
            "coverage_pct": fund.get("coverage_pct"),
        },
    ]
    for row in quote.get("lineage") or []:
        if isinstance(row, dict):
            lineage.append(row)

    evidence = [
        {
            "evidence_type": "valuation_metrics",
            "source_id": ENGINE_CODE,
            "ticker": key,
            "payload": {
                "current": subject.to_dict(),
                "peers": medians,
                "historical": historical,
                "premium_discount": {
                    "pe_premium_pct": (relative.get("pe") or {}).get("premium_pct"),
                    "pb_premium_pct": (relative.get("pb") or {}).get("premium_pct"),
                    "ev_ebitda_premium_pct": (relative.get("ev_ebitda") or {}).get("premium_pct"),
                },
            },
            "confidence": confidence,
            "as_of": as_of or _now(),
        }
    ]

    valuation = {
        "current": subject.to_dict(),
        "historical": {
            "bands": historical,
            "windows": historical_windows,
            "percentile": (historical.get("pe") or {}).get("percentile"),
            "median": (historical.get("pe") or {}).get("median"),
            "premium": (relative.get("pe") or {}).get("premium_pct"),
        },
        "peers": {
            **medians,
            "universe": peer_meta.get("primary_peers") or [],
            "secondary": peer_meta.get("secondary_peers") or [],
            "snapshots": [p.to_dict() for p in peers],
            "sector": peer_meta.get("sector"),
            "industry": peer_meta.get("industry"),
            "sub_industry": peer_meta.get("sub_industry"),
            "source": peer_meta.get("source"),
        },
        "quality": quality,
        "growth": growth.to_dict(),
        "relative": relative,
        "conditioning": matrix,
        "source_reconciliation": reconciliation,
        "narrative": {
            "stance": stance,
            "observations": observations,
            "summary": " ".join(observations[:3]) if observations else stance,
        },
        "confidence": confidence,
        "freshness": {
            "as_of": as_of,
            "age_days": age_days,
            "stale": (age_days is not None and age_days > FRESHNESS_SLA_DAYS),
            "sla_days": FRESHNESS_SLA_DAYS,
        },
    }

    return {
        "ok": ok,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": key,
        "generated_at": _now(),
        "valuation": valuation,
        "current": subject.to_dict(),
        "peer_universe": peer_meta,
        "peer_snapshots": [p.to_dict() for p in peers],
        "relative": relative,
        "historical": historical,
        "historical_windows": historical_windows,
        "quality": quality,
        "growth": growth.to_dict(),
        "narrative": valuation["narrative"],
        "valuation_conditioning": matrix,
        "source_reconciliation": reconciliation,
        "observations": observations,
        "stance": stance,
        "evidence": evidence,
        "confidence": confidence,
        "valuation_confidence": confidence,
        "freshness": valuation["freshness"],
        "lineage": lineage,
        "coverage_pct": coverage,
        "valuation_coverage_pct": coverage,
        "cid_summary": {
            "valuation_coverage": coverage,
            "current_multiples": {
                "pe": subject.pe,
                "pb": subject.pb,
                "ev_ebitda": subject.ev_ebitda,
                "peg": subject.peg,
                "forward_pe": subject.forward_pe,
            },
            "peer_multiples": medians,
            "historical_bands": historical,
            "historical_windows": historical_windows,
            "premium_discount": {
                "pe_premium_pct": (relative.get("pe") or {}).get("premium_pct"),
                "pb_premium_pct": (relative.get("pb") or {}).get("premium_pct"),
                "ev_ebitda_premium_pct": (relative.get("ev_ebitda") or {}).get("premium_pct"),
            },
            "valuation_conditioning": matrix,
            "confidence": confidence,
            "freshness": valuation["freshness"],
            "narrative_stance": stance,
            "evidence_lineage": lineage,
        },
        "score": confidence,
        "latency_ms": latency_ms,
        "peer_errors": peer_errors,
        "errors": []
        if ok
        else [
            e
            for e in [
                None if peer_meta.get("resolved") else "peer_universe_unresolved",
                None if (subject.pe or subject.pb or subject.ev_ebitda) else "multiples_unavailable",
            ]
            if e
        ],
        "recommendation_policy": "observations_only_no_buy_sell",
    }
