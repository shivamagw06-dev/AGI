"""Build market-aware context panel from an honest quote."""

from __future__ import annotations

from typing import Any

from live_market_context.providers import fetch_best_quote
from live_market_context.schema import FRESHNESS_SLA_SEC


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _liquidity_score(volume: Any, *, seeded: bool) -> dict[str, Any]:
    vol = _num(volume)
    if vol is None:
        return {"score": None, "band": "unknown", "volume": None}
    # Soft institutional bands for NSE cash (not a trade instruction)
    if vol >= 5_000_000:
        band, score = "high", 0.9
    elif vol >= 1_000_000:
        band, score = "adequate", 0.7
    elif vol >= 100_000:
        band, score = "moderate", 0.5
    else:
        band, score = "thin", 0.3
    if seeded:
        score = max(0.2, score - 0.1)
    return {"score": score, "band": band, "volume": vol}


def _relative_strength(quote: dict[str, Any]) -> dict[str, Any]:
    rs = quote.get("relative_strength_52w")
    if rs is not None:
        return {
            "relative_strength_52w": rs,
            "fifty_two_week_high": quote.get("fifty_two_week_high"),
            "fifty_two_week_low": quote.get("fifty_two_week_low"),
            "band": (
                "upper"
                if rs >= 0.7
                else "mid"
                if rs >= 0.3
                else "lower"
            ),
        }
    # Derive from high/low/close if present on Groww OHLC
    hi, lo, ltp = _num(quote.get("high")), _num(quote.get("low")), _num(quote.get("ltp"))
    if hi and lo and ltp is not None and hi != lo:
        # Intraday range position — weaker than 52w but still context
        pos = (ltp - lo) / (hi - lo)
        return {"relative_strength_intraday": round(pos, 4), "band": "intraday_only"}
    return {"relative_strength_52w": None, "band": "unavailable"}


def _distance_to_intrinsic(ltp: float | None, intrinsic: float | None) -> dict[str, Any]:
    if ltp is None or intrinsic is None or intrinsic <= 0:
        return {
            "distance_to_intrinsic_pct": None,
            "intrinsic_value": intrinsic,
            "available": False,
            "note": "Intrinsic value not supplied — P2.2 will populate when available",
        }
    dist = (ltp - intrinsic) / intrinsic * 100.0
    return {
        "distance_to_intrinsic_pct": round(dist, 2),
        "intrinsic_value": intrinsic,
        "available": True,
        "note": "Positive = price above intrinsic; negative = below",
    }


def build_market_context(
    ticker: str,
    *,
    force: bool = False,
    intrinsic_value: float | None = None,
) -> dict[str, Any]:
    """Assemble P2.6 market context panel (standard engine outputs)."""
    quote = fetch_best_quote(ticker, force=force)
    ltp = _num(quote.get("ltp"))
    age = quote.get("age_sec")
    if age is None and quote.get("as_of"):
        from live_market_context.providers import _age_sec

        age = _age_sec(quote.get("as_of"))
    stale = bool(quote.get("stale")) or (age is not None and int(age) > FRESHNESS_SLA_SEC) or ltp is None
    fresh_ok = ltp is not None and not stale

    liquidity = _liquidity_score(quote.get("volume"), seeded=bool(quote.get("seeded")))
    rs = _relative_strength(quote)
    dist = _distance_to_intrinsic(ltp, intrinsic_value)

    evidence = []
    if ltp is not None:
        evidence.append(
            {
                "claim": f"{ticker.upper()} last price {ltp} via {quote.get('provider')}",
                "source": quote.get("provider"),
            }
        )
    if quote.get("fail_closed"):
        evidence.append(
            {
                "claim": "No honest live quote — fail closed (no index-seed attach)",
                "source": "live_market_context",
            }
        )
    if dist.get("available"):
        evidence.append(
            {
                "claim": f"Distance to intrinsic {dist['distance_to_intrinsic_pct']}%",
                "source": "valuation_hook",
            }
        )

    # Context quality score 0–1 (not company quality)
    conf_parts = []
    if fresh_ok:
        conf_parts.append(0.45)
    if liquidity.get("score") is not None:
        conf_parts.append(0.25 * float(liquidity["score"]))
    if rs.get("relative_strength_52w") is not None:
        conf_parts.append(0.2)
    elif rs.get("relative_strength_intraday") is not None:
        conf_parts.append(0.1)
    if dist.get("available"):
        conf_parts.append(0.1)
    confidence = round(min(1.0, sum(conf_parts)), 3) if ltp is not None else 0.0

    return {
        "ticker": ticker.upper(),
        "ok": ltp is not None,
        "ltp": ltp,
        "currency": quote.get("currency") or "INR",
        "change_pct": quote.get("change_pct"),
        "provider": quote.get("provider"),
        "failover_from": quote.get("failover_from"),
        "as_of": quote.get("as_of"),
        "age_sec": age,
        "price_freshness": {
            "age_sec": age,
            "sla_sec": FRESHNESS_SLA_SEC,
            "within_sla": bool(fresh_ok),
            "stale": stale,
        },
        "liquidity": liquidity,
        "relative_strength": rs,
        "distance_to_intrinsic": dist,
        "market_status": quote.get("market_status"),
        "seeded": bool(quote.get("seeded")),
        "score": confidence,  # context_quality
        "evidence": evidence,
        "confidence": confidence,
        "freshness": {
            "age_days": round(float(age) / 86400.0, 4) if age is not None else None,
            "age_sec": age,
            "stale": stale,
            "sla_days": 0,
            "sla_sec": FRESHNESS_SLA_SEC,
        },
        "lineage": list(quote.get("lineage") or []),
        "error": quote.get("error"),
        "fail_closed": bool(quote.get("fail_closed")) or ltp is None,
    }
