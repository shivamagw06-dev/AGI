"""Step 4 — Valuation intelligence (interpret multiples; do not only display them)."""

from __future__ import annotations

from typing import Any

from company_analysis.cid_bridge import normalise_valuation, unwrap_validated
from company_analysis.flags import flag_valuation


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def analyse_valuation(
    *,
    identity: dict[str, Any],
    cid: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    dvc_pkg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not flag_valuation():
        return {"enabled": False, "bypassed": True}

    cid = cid or {}
    val = normalise_valuation(cid)
    ve = valuation_pack or {}
    company_ve = ve.get("company") if isinstance(ve.get("company"), dict) else {}
    # Prefer P2.2 Valuation Intelligence soft-attached on CID (synthesis layer)
    p22 = cid.get("valuation_intelligence") if isinstance(cid.get("valuation_intelligence"), dict) else {}
    p22_summary = p22.get("cid_summary") if isinstance(p22.get("cid_summary"), dict) else {}
    p22_current = p22_summary.get("current_multiples") if isinstance(p22_summary.get("current_multiples"), dict) else {}
    p22_peers = p22_summary.get("peer_multiples") if isinstance(p22_summary.get("peer_multiples"), dict) else {}
    p22_hist = p22_summary.get("historical_bands") if isinstance(p22_summary.get("historical_bands"), dict) else {}
    validated = unwrap_validated((dvc_pkg or {}).get("validated_fields") or cid.get("validated_fields") or {})

    pe = _num(
        p22_current.get("pe")
        or val.get("pe")
        or val.get("trailing_pe")
        or validated.get("pe")
        or validated.get("trailing_pe")
        or company_ve.get("pe")
        or company_ve.get("trailing_pe")
    )
    pb = _num(
        p22_current.get("pb")
        or val.get("pb")
        or val.get("price_to_book")
        or validated.get("pb")
        or validated.get("price_to_book")
        or company_ve.get("pb")
    )
    forward_pe = _num(p22_current.get("forward_pe") or val.get("forward_pe") or validated.get("forward_pe"))
    peg = _num(p22_current.get("peg") or val.get("peg") or validated.get("peg"))
    ev_ebitda = _num(p22_current.get("ev_ebitda") or val.get("ev_ebitda") or validated.get("ev_ebitda"))
    hist_pe = _num(
        ((p22_hist.get("pe") or {}) if isinstance(p22_hist.get("pe"), dict) else {}).get("median")
        or val.get("historical_pe")
        or val.get("pe_median")
        or val.get("avg_pe")
    )
    peer_pe = _num(p22_peers.get("median_pe") or val.get("peer_pe") or val.get("sector_pe"))
    expected_growth = (
        val.get("expected_growth")
        or company_ve.get("growth")
        or validated.get("earnings_growth")
        or validated.get("revenue_growth")
    )
    intrinsic = company_ve.get("intrinsic_value") or val.get("intrinsic_value")
    mos = company_ve.get("margin_of_safety") or val.get("margin_of_safety")
    dividend_yield = _num(val.get("dividend_yield"))

    premium_discount = None
    implication = []
    if pe is not None and hist_pe is not None and hist_pe > 0:
        premium_discount = round((pe / hist_pe - 1.0) * 100.0, 1)
        if premium_discount > 10:
            implication.append(
                f"Current PE {pe} is ~{premium_discount}% above historical PE {hist_pe} — market embeds above-average expectations."
            )
        elif premium_discount < -10:
            implication.append(
                f"Current PE {pe} is ~{abs(premium_discount)}% below historical PE {hist_pe} — either a discount opportunity or lower embedded growth/quality."
            )
        else:
            implication.append(f"Current PE {pe} is near historical PE {hist_pe} — valuation close to own history.")
    elif pe is not None:
        implication.append(
            f"Current PE {pe} is observed; without a complete historical PE band, avoid single-multiple conclusions and triangulate with growth and returns."
        )
    else:
        implication.append("Trailing PE coverage is incomplete — valuation relies on alternate institutional multiples and intrinsic references where available.")

    if forward_pe is not None and pe is not None and forward_pe > 0:
        if forward_pe < pe:
            implication.append(
                f"Forward PE {forward_pe} sits below trailing PE {pe}, consistent with expected earnings improvement already partly in the price."
            )
        else:
            implication.append(f"Forward PE {forward_pe} remains elevated versus trailing PE {pe} — embedded optimism should be stress-tested.")

    if peg is not None:
        implication.append(
            f"PEG around {peg:.2f} helps judge whether growth fully justifies the multiple — treat PEG as a cross-check, not a verdict."
        )
    if ev_ebitda is not None:
        implication.append(
            f"EV/EBITDA around {ev_ebitda:.1f}x adds an enterprise-value lens beyond equity multiples."
        )
    if dividend_yield is not None:
        dy = dividend_yield * 100 if dividend_yield <= 1.5 else dividend_yield
        implication.append(
            f"Dividend yield near {dy:.1f}% informs shareholder-return capacity alongside buybacks and retained earnings."
        )

    if peer_pe is not None and pe is not None and peer_pe > 0:
        vs_peer = round((pe / peer_pe - 1.0) * 100.0, 1)
        implication.append(
            f"Vs peer/sector PE {peer_pe}: company trades {vs_peer}% {'premium' if vs_peer > 0 else 'discount'} — justify via growth, ROE/ROIC and risk."
        )

    if expected_growth is not None:
        implication.append(f"Embedded / expected growth signal: {expected_growth}.")
    if intrinsic is not None:
        implication.append(f"Intrinsic value reference from the valuation stack: {intrinsic}.")
    if mos is not None:
        implication.append(f"Margin of safety reference: {mos}.")

    sector = str(identity.get("sector_id") or "").lower()
    if "bank" in sector:
        implication.append("For banks, prefer P/B + ROE/COE framing beside PE; PE alone misleads across credit cycles.")
    if "fmcg" in sector or "staple" in sector:
        implication.append("For premium FMCG, PE premium must be earned by ROIC durability, pricing power and cash conversion.")

    # Fold P2.2 observations (never BUY/SELL) ahead of interpretive implications
    p22_obs = list(p22.get("observations") or [])
    if p22_obs:
        implication = [str(x) for x in p22_obs if x] + implication

    coverage = 0
    for v in (pe, hist_pe, peer_pe, intrinsic, mos, forward_pe, ev_ebitda):
        if v is not None:
            coverage += 15
    if p22.get("ok"):
        coverage = max(coverage, int(float(p22.get("coverage_pct") or 0)))

    peer_universe = identity.get("peers") or (p22.get("peer_universe") or {}).get("primary_peers") or []
    premium_vs_peers = None
    if isinstance(p22_summary.get("premium_discount"), dict):
        premium_vs_peers = p22_summary["premium_discount"].get("pe_premium_pct")
    elif pe is not None and peer_pe not in (None, 0):
        premium_vs_peers = round((pe / peer_pe - 1.0) * 100.0, 1)

    return {
        "enabled": True,
        "current_pe": pe,
        "forward_pe": forward_pe,
        "historical_pe": hist_pe,
        "pb": pb,
        "peg": peg,
        "ev_ebitda": ev_ebitda,
        "dividend_yield": dividend_yield,
        "enterprise_value": val.get("enterprise_value") or p22_current.get("enterprise_value"),
        "premium_discount_vs_history_pct": premium_discount,
        "premium_discount_vs_peers_pct": premium_vs_peers,
        "expected_growth": expected_growth,
        "embedded_expectations": implication[:6],
        "peer_valuation": {
            "peer_pe": peer_pe,
            "peers": peer_universe,
            "median_pb": p22_peers.get("median_pb"),
            "median_ev_ebitda": p22_peers.get("median_ev_ebitda"),
        },
        "historical_valuation_range": val.get("pe_range")
        or val.get("historical_range")
        or p22_hist.get("pe"),
        "intrinsic_value": intrinsic,
        "margin_of_safety": mos,
        "narrative": " ".join(implication),
        "stance": p22.get("stance") or (p22.get("cid_summary") or {}).get("narrative_stance"),
        "coverage_pct": min(100, coverage),
        "sources": ["valuation_intelligence", "cid.valuation", "cid.market_data", "dvc.validated_fields", "ve.consult"],
        "p22_attached": bool(p22.get("ok")),
    }
