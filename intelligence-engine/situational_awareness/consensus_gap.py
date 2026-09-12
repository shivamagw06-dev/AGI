"""Where AGI's own forward EPS disagrees with the Street's.

The question this asks is deliberately not the one the revision engine asks.
`hedge_fund_lab/estimate_revision` ranks on whether the Street is *changing its
mind*, and that signal is already built and already fails out of sample: a 2024+
information coefficient of 0.022 and a long-short of -29% annualised. Momentum
in consensus estimates is not the edge.

This asks instead whether the Street is *still wrong* relative to a forecast we
made ourselves. That is a different quantity. A revision is the Street's own
trend; a gap is a disagreement between two independent estimates of the same
future number. The first can be extracted by anyone holding the same vendor
feed, which is roughly why it stopped working. The second cannot exist without a
fundamental model of our own, which is the whole point of the exercise.

Three things this module refuses to do:

* Mix a modelled estimate with a mechanical one. Every row is tagged
  `fundamental_model` or `mechanical_fallback`, and the fallback exists to prove
  the plumbing and to serve as a control, never to pad coverage. A gap computed
  between consensus and a growth formula is a comparison of two formulas, and
  reporting it beside a genuine model estimate would make the engine look like
  it covers three times the universe it actually covers.
* Look ahead. A row dated 2025-06-30 reads only vintages published on or before
  2025-06-30, on both sides. The Street vintages carry real publication dates,
  so point-in-time is available here in a way it is not for `financials_annual`.
* Compare different fiscal years. AGI writes `FY27`; Capital IQ writes `FY2027`.
  Joining the raw labels returns nothing at all, and joining them carelessly
  after a partial fix would compare next year's estimate to this year's and
  report a gap that is really one year of growth.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Optional

GAP_VERSION = "sa-consensus-gap-1"

AGI_TAB = "forecast_metric_predictions"
STREET_TAB = "consensus_metric_vintages"

AGI_METRIC = "eps"
STREET_METRIC = "eps_estimate"
REPORTED_METRIC = "eps_reported"
BASE_SCENARIO = "base"

SOURCE_MODEL = "fundamental_model"
SOURCE_FALLBACK = "mechanical_fallback"

# Horizon labels to years out, for checking a forecast against its own formula.
_HORIZON_YEARS = {"FY+1": 1, "FY+2": 2, "FY+3": 3, "FY+4": 4, "FY+5": 5}

# A forecast that lands within this of base_value x (1+cagr)^n *is* that
# formula. One percent is loose enough for rounding and far tighter than any
# genuine analytical judgement would leave.
EXTRAPOLATION_TOLERANCE = 0.01

# Stored forecasts are rounded to two decimals, so at an EPS of 0.39 a rounding
# difference alone is 1.3% -- above the relative tolerance. Without an absolute
# floor the smallest-EPS names slip through and get reported as fundamental
# estimates purely because they round badly.
EXTRAPOLATION_ABS_TOLERANCE = 0.011

# A Street EPS of 0.02 is not a forecast anyone acts on, and dividing by it turns
# a two-paisa modelling difference into a 900% gap that would dominate every
# ranking. Capital IQ also writes 0 for "no data", so anything at or below this
# floor is treated as absent rather than as a tiny earnings forecast.
MIN_ABS_STREET_EPS = 0.10

# Beyond this the two sides are not describing the same information set. Six
# months is already generous for a quarterly-reporting market.
MAX_AGE_DAYS = 400

REVISION_LOOKBACK_DAYS = 92          # ~3 months, matching the revision engine
MATERIAL_GAP_PCT = 10.0              # below this a gap is not a disagreement
MATERIAL_REVISION_PCT = 3.0          # below this the Street is effectively flat


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("Z", "")
    for cut in (10, 19):
        try:
            return datetime.fromisoformat(text[:cut]).date()
        except ValueError:
            continue
    return None


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def normalise_period(label: Any) -> Optional[str]:
    """`FY27`, `FY2027`, `2027` and `fy 27` all mean FY2027.

    The two warehouses disagree on this and nothing enforces either convention,
    so the canonical form is produced here rather than assumed anywhere. Two
    digits are read as 20xx, which is safe for a forward-estimate table and
    would need revisiting long after everything else here has been replaced.
    """
    text = str(label or "").strip().upper().replace(" ", "")
    if not text:
        return None
    if text.startswith("FY"):
        text = text[2:]
    if not text.isdigit():
        return None
    if len(text) == 2:
        return f"FY20{text}"
    if len(text) == 4:
        return f"FY{text}"
    return None


def _latest_on_or_before(rows: list[tuple[date, Any]], cutoff: date) -> Optional[tuple[date, Any]]:
    """The newest row published on or before the cutoff, or nothing.

    This is the only place point-in-time is enforced, so it returns the stamp
    alongside the payload and callers record the age rather than assuming it.
    """
    best: Optional[tuple[date, Any]] = None
    for stamp, payload in rows:
        if stamp > cutoff:
            continue
        if best is None or stamp > best[0]:
            best = (stamp, payload)
    return best


def index_street(rows: Iterable[dict[str, Any]], *,
                 metric: str = STREET_METRIC) -> dict[tuple[str, str], list[tuple[date, float]]]:
    """{(symbol, FY2027): [(consensus_date, mean_estimate), ...]} sorted by date."""
    out: dict[tuple[str, str], list[tuple[date, float]]] = {}
    for row in rows or []:
        if str(row.get("metric") or "") != metric:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        period = normalise_period(row.get("target_period"))
        stamp = _as_date(row.get("consensus_date"))
        value = _number(row.get("mean_estimate"))
        if not symbol or not period or stamp is None or value is None:
            continue
        out.setdefault((symbol, period), []).append((stamp, value))
    for key in out:
        out[key].sort(key=lambda pair: pair[0])
    return out


def index_agi(rows: Iterable[dict[str, Any]], *,
              scenario: str = BASE_SCENARIO,
              metric: str = AGI_METRIC) -> dict[tuple[str, str], list[tuple[date, dict[str, Any]]]]:
    """{(symbol, FY2027): [(forecast_as_of, row), ...]} for one scenario."""
    out: dict[tuple[str, str], list[tuple[date, dict[str, Any]]]] = {}
    for row in rows or []:
        if str(row.get("metric") or "") != metric:
            continue
        if str(row.get("scenario") or "") != scenario:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        period = normalise_period(row.get("target_period"))
        stamp = _as_date(row.get("forecast_as_of")) or _as_date(row.get("generated_at"))
        value = _number(row.get("forecast_value"))
        if not symbol or not period or stamp is None or value is None:
            continue
        out.setdefault((symbol, period), []).append((stamp, {**row, "_value": value}))
    for key in out:
        out[key].sort(key=lambda pair: pair[0])
    return out


def street_revision_pct(series: list[tuple[date, float]], as_of: date, *,
                        lookback_days: int = REVISION_LOOKBACK_DAYS) -> Optional[float]:
    """How the Street moved on this exact fiscal year over the lookback.

    The target period is fixed by the caller's key, which is the discipline the
    revision engine documents: Indian fiscal years roll in April, so comparing
    across periods reports a year of growth as though it were a revision.
    Returns nothing when there is no earlier vintage, rather than zero, because
    "no prior estimate" and "no change" are different facts.
    """
    now = _latest_on_or_before(series, as_of)
    if now is None:
        return None
    cutoff = date.fromordinal(as_of.toordinal() - int(lookback_days))
    then = _latest_on_or_before(series, cutoff)
    if then is None or then[0] == now[0]:
        return None
    if abs(then[1]) < MIN_ABS_STREET_EPS:
        return None
    return round((now[1] / then[1] - 1.0) * 100.0, 4)


def classify(gap_pct: Optional[float], revision_pct: Optional[float]) -> str:
    """The four states: a gap means little without knowing if the Street is moving."""
    if gap_pct is None:
        return "no_gap"
    big = abs(gap_pct) >= MATERIAL_GAP_PCT
    if revision_pct is None:
        return "gap_no_revision_history" if big else "small_gap"
    rising = revision_pct >= MATERIAL_REVISION_PCT
    if gap_pct >= MATERIAL_GAP_PCT and not rising:
        # We disagree upward and the Street has not started to follow.
        return "early_variant_perception"
    if gap_pct >= MATERIAL_GAP_PCT and rising:
        return "thesis_being_discovered"
    if not big and rising:
        return "consensus_momentum"
    if gap_pct <= -MATERIAL_GAP_PCT and rising:
        return "street_may_be_over_extrapolating"
    return "small_gap"


def _period_year(period: str) -> Optional[int]:
    try:
        return int(period[2:])
    except (TypeError, ValueError):
        return None


def reported_by_symbol(rows: Iterable[dict[str, Any]], as_of: date
                       ) -> dict[str, dict[int, float]]:
    """{symbol: {fiscal_year: reported_eps}} using only what was known by as_of.

    Reported EPS is indexed by the fiscal year it describes, not by the vintage
    date it arrived on. A CAGR wants earnings ordered by the year they were
    earned; ordering by publication date instead measures the speed of the data
    feed. Where the same year appears in several vintages the latest one known
    by `as_of` wins, which is how a restatement should be handled.
    """
    out: dict[str, dict[int, tuple[date, float]]] = {}
    for row in rows or []:
        if str(row.get("metric") or "") != REPORTED_METRIC:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        period = normalise_period(row.get("target_period"))
        stamp = _as_date(row.get("consensus_date"))
        value = _number(row.get("mean_estimate"))
        if not symbol or not period or stamp is None or value is None:
            continue
        if stamp > as_of:
            continue
        year = _period_year(period)
        if year is None:
            continue
        prev = out.setdefault(symbol, {}).get(year)
        if prev is None or stamp > prev[0]:
            out[symbol][year] = (stamp, value)
    return {sym: {yr: val for yr, (_, val) in years.items()}
            for sym, years in out.items()}


def mechanical_eps(history: dict[int, float], period: str, *,
                   min_years: int = 3) -> Optional[tuple[float, float]]:
    """A growth-formula EPS, for plumbing and controls only.

    Explicitly not a forecast. It extrapolates the last reported EPS at its own
    historical CAGR, which is what a spreadsheet does when nobody has thought
    about the company. It exists so the engine can be exercised end to end on
    names the fundamental model has not reached, and so an ablation has a null
    model to beat. Rows built from it are tagged `mechanical_fallback` and are
    never averaged in with modelled rows.

    Returns (value, confidence), with confidence capped low on purpose.
    """
    years = sorted(y for y, v in (history or {}).items() if v is not None)
    if len(years) < min_years:
        return None
    first_year, last_year = years[0], years[-1]
    first_value, last_value = history[first_year], history[last_year]
    target_year = _period_year(period)
    if target_year is None:
        return None
    # A CAGR through zero or across a sign change is meaningless. Refuse rather
    # than produce a confident-looking number out of an arithmetic accident.
    if first_value <= 0 or last_value <= 0:
        return None
    span = last_year - first_year
    if span < 1:
        return None
    cagr = (last_value / first_value) ** (1.0 / span) - 1.0
    # Cap it. A company that doubled earnings once should not be projected to
    # double again every year out to FY2028.
    cagr = max(-0.25, min(0.25, cagr))
    years_out = target_year - last_year
    if years_out < 0 or years_out > 6:
        return None
    value = last_value * ((1.0 + cagr) ** years_out)
    confidence = round(max(0.10, 0.35 - 0.04 * years_out), 4)
    return (round(value, 4), confidence)


def agi_source_of(row: dict[str, Any]) -> str:
    """Decide by arithmetic whether a stored forecast is a model or a formula.

    `forecast_metric_predictions` is the table a fundamental estimate would live
    in, and its name asserts nothing about how the number was produced. As of
    the 2026-08-17 run, 97.2% of its base-case EPS rows are reproduced to within
    a rounding error by

        forecast_value = base_value * (1 + historical_cagr_pct/100) ** years_out

    which is a trend extrapolation wearing a forecast's clothes. Comparing that
    against consensus does not measure a differentiated belief; it measures the
    difference between two formulas, and it would be ranked and traded as though
    it were insight.

    So the tag is derived from the row's own numbers rather than from the tab it
    was read out of. If the model later produces genuine estimates into the same
    table, they stop matching the identity and are tagged as models without any
    change here.
    """
    base = _number(row.get("base_value"))
    cagr = _number(row.get("historical_cagr_pct"))
    value = _number(row.get("forecast_value"))
    years = _HORIZON_YEARS.get(str(row.get("horizon") or "").strip().upper())
    if base is None or cagr is None or value is None or years is None:
        return SOURCE_MODEL
    if abs(base) < 1e-9 or abs(value) < 1e-9:
        return SOURCE_MODEL
    predicted = base * ((1.0 + cagr / 100.0) ** years)
    multiplier = _number(row.get("scenario_multiplier"))
    candidates = [predicted]
    if multiplier is not None and multiplier != 0:
        candidates.append(predicted * multiplier)
    for candidate in candidates:
        diff = abs(candidate - value)
        if (diff / abs(value) <= EXTRAPOLATION_TOLERANCE
                or diff <= EXTRAPOLATION_ABS_TOLERANCE):
            return SOURCE_FALLBACK
    return SOURCE_MODEL


def _gap_confidence(forecast_conf: Optional[float], causal_conf: Optional[float]) -> float:
    """How much to trust the disagreement, not the direction of it.

    A gap is only as good as the forecast behind it, so the forecast confidence
    is the ceiling. Causal confidence can lower it but never raise it: knowing
    the transmission channel well does not make a weak earnings model strong.
    Absent causal state leaves the forecast confidence untouched rather than
    halving it, because no causal link is not the same as a broken one.
    """
    base = forecast_conf if forecast_conf is not None else 0.5
    base = max(0.0, min(1.0, base))
    if causal_conf is None:
        return round(base, 4)
    return round(base * max(0.0, min(1.0, causal_conf)) ** 0.5, 4)


def build_rows(as_of: date, *,
               agi_rows: Iterable[dict[str, Any]],
               street_rows: Iterable[dict[str, Any]],
               causal_impacts: Optional[dict[str, dict[str, Any]]] = None,
               periods: Optional[Iterable[str]] = None,
               allow_fallback: bool = False) -> dict[str, Any]:
    """One frozen row per symbol x as_of x fiscal period.

    `causal_impacts` is what `graph.company_impacts` returned for the world
    state on this date, keyed by symbol. It is optional: the gap stands on its
    own, and the causal layer is the thing being tested for added information,
    so it must be possible to run without it.
    """
    street_all = list(street_rows or [])
    street = index_street(street_all)
    reported = reported_by_symbol(street_all, as_of)
    agi = index_agi(agi_rows)
    causal_impacts = causal_impacts or {}

    wanted = {normalise_period(p) for p in periods} if periods else None
    wanted = {p for p in (wanted or set()) if p} or None

    rows: list[dict[str, Any]] = []
    counts = {"joined": 0, "modelled": 0, "fallback": 0,
              "no_street": 0, "no_agi": 0, "street_too_small": 0, "stale": 0,
              "extrapolated_not_modelled": 0}
    keys = set(agi) | (set(street) if allow_fallback else set())

    for symbol, period in sorted(keys):
        if wanted and period not in wanted:
            continue
        street_series = street.get((symbol, period)) or []
        street_hit = _latest_on_or_before(street_series, as_of)
        if street_hit is None:
            counts["no_street"] += 1
            continue
        street_stamp, street_eps = street_hit
        if abs(street_eps) < MIN_ABS_STREET_EPS:
            # Capital IQ's zero-for-no-data sentinel, or a forecast so small the
            # percentage gap would be meaningless.
            counts["street_too_small"] += 1
            continue

        agi_hit = _latest_on_or_before(agi.get((symbol, period)) or [], as_of)
        if agi_hit is not None:
            agi_stamp, agi_row = agi_hit
            agi_eps = agi_row["_value"]
            agi_source = agi_source_of(agi_row)
            forecast_conf = _number(agi_row.get("confidence_score"))
            if agi_source == SOURCE_FALLBACK:
                if not allow_fallback:
                    # The stored "forecast" is a trend formula. Without the
                    # fallback explicitly enabled this is not a gap worth
                    # reporting, and reporting it would overstate coverage.
                    counts["extrapolated_not_modelled"] += 1
                    continue
                # A formula does not get a model's confidence, whatever the
                # producing engine wrote into confidence_score.
                forecast_conf = min(0.35, forecast_conf if forecast_conf is not None else 0.35)
        elif allow_fallback:
            made = mechanical_eps(reported.get(symbol) or {}, period)
            if made is None:
                counts["no_agi"] += 1
                continue
            agi_eps, forecast_conf = made
            agi_stamp = as_of
            agi_source = SOURCE_FALLBACK
        else:
            counts["no_agi"] += 1
            continue

        street_age = as_of.toordinal() - street_stamp.toordinal()
        agi_age = as_of.toordinal() - agi_stamp.toordinal()
        if street_age > MAX_AGE_DAYS or agi_age > MAX_AGE_DAYS:
            counts["stale"] += 1
            continue

        gap_abs = round(agi_eps - street_eps, 4)
        gap_pct = round(gap_abs / abs(street_eps) * 100.0, 4)
        impact = causal_impacts.get(symbol) or {}
        causal_conf = _number(impact.get("confidence"))
        revision = street_revision_pct(street_series, as_of)

        rows.append({
            "symbol": symbol,
            "as_of_date": as_of.isoformat(),
            "fiscal_period": period,
            "street_eps": round(street_eps, 4),
            "agi_eps": round(agi_eps, 4),
            "agi_eps_source": agi_source,
            "eps_gap_abs": gap_abs,
            "eps_gap_pct": gap_pct,
            "street_eps_age_days": street_age,
            "agi_eps_age_days": agi_age,
            "causal_exposure_effect_pct": _number(impact.get("exposure_effect_pct")),
            "causal_effect_low": _number(impact.get("exposure_effect_low")),
            "causal_effect_high": _number(impact.get("exposure_effect_high")),
            "causal_confidence": causal_conf,
            "forecast_confidence": None if forecast_conf is None else round(forecast_conf, 4),
            "gap_confidence": _gap_confidence(forecast_conf, causal_conf),
            # Control, not signal: kept so an ablation can ask whether the gap
            # adds anything over the revision momentum that already failed.
            "street_revision_3m_pct": revision,
            "gap_state": classify(gap_pct, revision),
            "gap_version": GAP_VERSION,
        })
        counts["joined"] += 1
        counts["modelled" if agi_source == SOURCE_MODEL else "fallback"] += 1

    return {
        "ok": True,
        "as_of": as_of.isoformat(),
        "version": GAP_VERSION,
        "rows": rows,
        "coverage": {
            **counts,
            "symbols": len({r["symbol"] for r in rows}),
            "periods": sorted({r["fiscal_period"] for r in rows}),
            "with_causal_state": sum(1 for r in rows if r["causal_confidence"] is not None),
            "with_revision_control": sum(1 for r in rows if r["street_revision_3m_pct"] is not None),
        },
        "states": {state: sum(1 for r in rows if r["gap_state"] == state)
                   for state in sorted({r["gap_state"] for r in rows})},
    }
