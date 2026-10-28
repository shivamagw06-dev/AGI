"""Soft structured inputs from EVE / IIE / FLE / MEE — never raw documents."""

from __future__ import annotations

from typing import Any

from app.ve.config import DEFAULT_ASSUMPTIONS, DEFAULT_MARKET_PRICE, DEFAULT_PEERS, PEER_MULTIPLES
from app.ve.models import Assumption


def _soft(fn, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def _num(val: Any, default: float) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def resolve_symbol(key: str, *, aoi: Any = None, iie: Any = None) -> tuple[str, str]:
    """Return (company_id, company_symbol)."""
    symbol = (key or "").strip().upper()
    company_id = symbol
    if aoi is not None:
        try:
            co = aoi.registry.resolve(key)
            if co:
                company_id = co.company_id or symbol
                symbol = (co.nse_symbol or symbol).upper()
        except Exception:
            pass
    if iie is not None:
        pack = _soft(iie.company, key, analyse_if_missing=False, default=None)
        if isinstance(pack, dict):
            company_id = pack.get("company_id") or company_id
            symbol = str(pack.get("symbol") or symbol).upper()
    if not symbol:
        symbol = "UNKNOWN"
    return company_id, symbol


def gather_inputs(
    key: str,
    *,
    eve: Any = None,
    iie: Any = None,
    fle: Any = None,
    mee: Any = None,
    aoi: Any = None,
    market_price: float | None = None,
) -> dict[str, Any]:
    """Build structured valuation inputs exclusively from engine soft reads."""
    company_id, symbol = resolve_symbol(key, aoi=aoi, iie=iie)
    assumptions: dict[str, float] = dict(DEFAULT_ASSUMPTIONS)
    assumption_meta: list[Assumption] = []
    evidence_ids: list[str] = []
    forecast_ids: list[str] = []
    event_ids: list[str] = []
    risks: list[str] = []
    base_revenue_cr = 150000.0
    confidence_bits: list[float] = []
    academy_assumption_note: dict[str, Any] = {}

    # FAPI — derive WACC / cost of equity methodology from Finance Academy (additive)
    try:
        from academy.fapi.production import apply_ve_assumptions

        academy_applied = apply_ve_assumptions(assumptions)
        if academy_applied.get("changed") or academy_applied.get("uses_academy_wacc_objects"):
            assumptions = dict(academy_applied.get("assumptions") or assumptions)
            academy_assumption_note = academy_applied.get("academy") or {}
            for name in ("wacc", "cost_of_equity", "cost_of_debt", "beta"):
                if name in assumptions:
                    assumption_meta.append(
                        Assumption(
                            name,
                            float(assumptions[name]),
                            source="finance_academy.methodology",
                            confidence=0.8,
                        )
                    )
    except Exception:
        academy_assumption_note = {}

    # IIE — quality / growth / risks / capital allocation
    iie_pack = _soft(iie.company, key, analyse_if_missing=True, default=None) if iie else None
    if isinstance(iie_pack, dict):
        company_id = iie_pack.get("company_id") or company_id
        symbol = str(iie_pack.get("symbol") or symbol).upper()
        thesis = iie_pack.get("thesis") or iie_pack.get("investment_thesis") or {}
        if isinstance(thesis, dict):
            g = thesis.get("growth_rate") or thesis.get("revenue_growth")
            if g is not None:
                assumptions["revenue_growth"] = _num(g, assumptions["revenue_growth"])
                assumption_meta.append(
                    Assumption("revenue_growth", assumptions["revenue_growth"], source="iie.thesis", confidence=0.7)
                )
            conf = _num(thesis.get("confidence"), 0.6)
            confidence_bits.append(conf)
        dna = iie_pack.get("dna") or {}
        if isinstance(dna, dict):
            quality = dna.get("business_quality") or dna.get("quality")
            if isinstance(quality, dict) and quality.get("score") is not None:
                # Map quality score 0-1 into margin uplift
                q = _num(quality.get("score"), 0.5)
                assumptions["ebit_margin"] = min(0.4, DEFAULT_ASSUMPTIONS["ebit_margin"] * (0.85 + 0.3 * q))
                assumption_meta.append(
                    Assumption("ebit_margin", assumptions["ebit_margin"], source="iie.dna", confidence=0.65)
                )
        for r in (iie_pack.get("risks") or [])[:8]:
            if isinstance(r, dict):
                risks.append(str(r.get("title") or r.get("risk") or r.get("assessment") or r))
            else:
                risks.append(str(r))
        for e in (iie_pack.get("evidence") or iie_pack.get("supporting_evidence") or [])[:12]:
            if isinstance(e, dict) and e.get("evidence_id"):
                evidence_ids.append(str(e["evidence_id"]))

    # FLE — forecasts / calibration
    fle_pack = _soft(fle.company, key, generate_if_empty=True, default=None) if fle else None
    if isinstance(fle_pack, dict):
        pending = fle_pack.get("pending_forecasts") or fle_pack.get("forecasts") or []
        for f in pending[:10]:
            if not isinstance(f, dict):
                continue
            if f.get("forecast_id"):
                forecast_ids.append(str(f["forecast_id"]))
            metric = str(f.get("metric") or "").lower()
            pred = f.get("predicted_numeric")
            if pred is None and f.get("predicted_value") is not None:
                try:
                    pred = float(f.get("predicted_value"))
                except (TypeError, ValueError):
                    pred = None
            if pred is None:
                continue
            if "revenue" in metric or "growth" in metric:
                # treat as growth fraction if < 1.5 else percent
                g = float(pred)
                if g > 1.5:
                    g = g / 100.0
                assumptions["revenue_growth"] = max(0.0, min(0.4, g))
                assumption_meta.append(
                    Assumption(
                        "revenue_growth",
                        assumptions["revenue_growth"],
                        source="fle.forecast",
                        confidence=_num(f.get("confidence"), 0.65),
                    )
                )
            if "margin" in metric:
                m = float(pred)
                if m > 1.5:
                    m = m / 100.0
                assumptions["ebit_margin"] = max(0.01, min(0.5, m))
                assumption_meta.append(
                    Assumption("ebit_margin", assumptions["ebit_margin"], source="fle.forecast", confidence=0.65)
                )
        cal = fle_pack.get("calibration") or {}
        if isinstance(cal, dict) and cal.get("label"):
            confidence_bits.append(0.7 if "well" in str(cal.get("label")).lower() else 0.55)

    # EVE — verified financial statements (structured only)
    eve_pack = _soft(eve.consult, key, limit=8, default=None) if eve else None
    if isinstance(eve_pack, dict):
        company = eve_pack.get("company") or {}
        for e in (company.get("evidence") or eve_pack.get("evidence") or [])[:20]:
            if isinstance(e, dict):
                if e.get("evidence_id"):
                    evidence_ids.append(str(e["evidence_id"]))
                field = str(e.get("field") or "").lower()
                # Parse crude numeric hints from verified text when present
                vt = str(e.get("value_text") or e.get("value") or "")
                digits = "".join(ch if (ch.isdigit() or ch == ".") else " " for ch in vt).split()
                num = _num(digits[0], 0.0) if digits else 0.0
                if num and "revenue" in field and num > 1000:
                    base_revenue_cr = num if num < 1_000_000 else num / 100.0
                    assumption_meta.append(
                        Assumption("base_revenue_cr", base_revenue_cr, source="eve.verified", confidence=0.8)
                    )

    # MEE — material events
    mee_pack = _soft(mee.consult, key, limit=8, default=None) if mee else None
    if isinstance(mee_pack, dict):
        company = mee_pack.get("company") or {}
        for ev in (company.get("events") or mee_pack.get("events") or [])[:10]:
            if isinstance(ev, dict):
                if ev.get("event_id"):
                    event_ids.append(str(ev["event_id"]))
                et = str(ev.get("event_type") or "").lower()
                title = str(ev.get("title") or "")
                if et in {"buyback", "dividend"} or "buyback" in title.lower():
                    assumptions["dividend_payout"] = min(0.8, assumptions["dividend_payout"] + 0.05)
                    assumption_meta.append(
                        Assumption(
                            "dividend_payout",
                            assumptions["dividend_payout"],
                            source="mee.event",
                            confidence=0.6,
                            notes=title,
                        )
                    )
                if et in {"guidance_cut", "downgrade"} or "miss" in title.lower():
                    assumptions["revenue_growth"] = max(0.0, assumptions["revenue_growth"] - 0.02)
                    assumption_meta.append(
                        Assumption(
                            "revenue_growth",
                            assumptions["revenue_growth"],
                            source="mee.event",
                            confidence=0.6,
                            notes=title,
                        )
                    )

    # Fill missing assumption metadata from defaults
    present = {a.name for a in assumption_meta}
    for name, value in assumptions.items():
        if name not in present:
            assumption_meta.append(
                Assumption(name, float(value), source="default", confidence=0.45)
            )

    peers = DEFAULT_PEERS.get(symbol) or DEFAULT_PEERS["DEFAULT"]
    peer_mult = PEER_MULTIPLES.get(symbol) or PEER_MULTIPLES["DEFAULT"]
    price = _num(market_price, DEFAULT_MARKET_PRICE)
    # Heuristic market price from peer PE * eps proxy
    if market_price is None:
        eps_proxy = (base_revenue_cr * assumptions["ebit_margin"] * (1 - assumptions["tax_rate"])) / max(
            0.01, assumptions["shares_outstanding_cr"]
        )
        price = round(eps_proxy * peer_mult["pe"], 2)

    conf = sum(confidence_bits) / len(confidence_bits) if confidence_bits else 0.55
    return {
        "company_id": company_id,
        "company_symbol": symbol,
        "assumptions": assumptions,
        "assumption_meta": assumption_meta,
        "base_revenue_cr": base_revenue_cr,
        "market_price": price,
        "peers": peers,
        "peer_multiples": peer_mult,
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
        "forecast_ids": list(dict.fromkeys(forecast_ids)),
        "event_ids": list(dict.fromkeys(event_ids)),
        "risks": risks[:12],
        "input_confidence": conf,
        "finance_academy": academy_assumption_note,
    }
