"""Deterministic technical math helpers (Feature Registry only — not engines)."""

from __future__ import annotations


def ema(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be >= 1")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = alpha * values[i] + (1 - alpha) * prev
        out[i] = prev
    return out


def rsi_wilder(closes: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    def _rsi(ag: float, al: float) -> float:
        if al == 0:
            return 100.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

    out[period] = _rsi(avg_gain, avg_loss)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = _rsi(avg_gain, avg_loss)
    return out


def atr_wilder(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    trs: list[float] = []
    for i in range(len(closes)):
        if i == 0:
            trs.append(highs[i] - lows[i])
        else:
            trs.append(
                max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                )
            )
    atr = sum(trs[1 : period + 1]) / period
    out[period] = atr
    for i in range(period + 1, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        out[i] = atr
    return out


def sma(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    total = sum(values[:period])
    out[period - 1] = total / period
    for i in range(period, len(values)):
        total += values[i] - values[i - period]
        out[i] = total / period
    return out


def stdev(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        mean = sum(window) / period
        var = sum((x - mean) ** 2 for x in window) / period
        out[i] = var**0.5
    return out


def roc(closes: list[float], period: int = 10) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    for i in range(period, len(closes)):
        prev = closes[i - period]
        out[i] = None if prev == 0 else ((closes[i] / prev) - 1.0) * 100.0
    return out


def realized_vol(closes: list[float], period: int = 20) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return out
    import math

    for i in range(period, len(closes)):
        rets = []
        for j in range(i - period + 1, i + 1):
            prev = closes[j - 1]
            if prev == 0:
                continue
            rets.append(math.log(closes[j] / prev))
        if len(rets) < 2:
            continue
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        out[i] = (var**0.5) * (252**0.5)
    return out


def adx_wilder(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    """Wilder ADX(period). Returns None until enough bars for DX seed + ADX smooth."""
    n = len(closes)
    out: list[float | None] = [None] * n
    if n <= period * 2:
        return out

    trs: list[float] = [0.0]
    plus_dm: list[float] = [0.0]
    minus_dm: list[float] = [0.0]
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        trs.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )

    atr = sum(trs[1 : period + 1]) / period
    pdm = sum(plus_dm[1 : period + 1]) / period
    mdm = sum(minus_dm[1 : period + 1]) / period

    dx_series: list[float | None] = [None] * n

    def _di(dm: float, atr_v: float) -> float:
        return 0.0 if atr_v == 0 else 100.0 * (dm / atr_v)

    def _dx(pdi: float, mdi: float) -> float:
        denom = pdi + mdi
        return 0.0 if denom == 0 else 100.0 * abs(pdi - mdi) / denom

    pdi = _di(pdm, atr)
    mdi = _di(mdm, atr)
    dx_series[period] = _dx(pdi, mdi)

    for i in range(period + 1, n):
        atr = (atr * (period - 1) + trs[i]) / period
        pdm = (pdm * (period - 1) + plus_dm[i]) / period
        mdm = (mdm * (period - 1) + minus_dm[i]) / period
        pdi = _di(pdm, atr)
        mdi = _di(mdm, atr)
        dx_series[i] = _dx(pdi, mdi)

    # ADX is Wilder smooth of DX starting after first `period` DX values
    first_dx_idx = period
    seed_end = first_dx_idx + period
    if seed_end > n:
        return out
    seed_vals = [dx_series[i] for i in range(first_dx_idx, seed_end) if dx_series[i] is not None]
    if len(seed_vals) < period:
        return out
    adx = sum(seed_vals) / period
    out[seed_end - 1] = adx
    for i in range(seed_end, n):
        dx = dx_series[i]
        if dx is None:
            continue
        adx = (adx * (period - 1) + dx) / period
        out[i] = adx
    return out
