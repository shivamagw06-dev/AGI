"""Estimating volatility from few returns, without understating it.

Two corrections, both of which matter at the horizons this warehouse measures.

The first is the estimator. A five-day realised volatility computed as the
population standard deviation of five returns understates the true figure by
about sixteen percent -- and the error is one-directional, so every premium
measured against it comes out too large. On this data that inflated the
variance risk premium from roughly +1.8 volatility points to +3.2, which is the
difference between a modest edge and an obvious one.

The second is the mean. The usual estimator subtracts the sample mean, which
spends a degree of freedom estimating a drift that, over five days, is almost
entirely noise. Assuming zero drift keeps that degree of freedom, and at short
horizons the assumption costs far less than the estimate does.

So: sigma = sqrt(mean(r^2)), then divided by the factor that makes it unbiased
for the number of returns actually used. For five returns that factor is 0.952;
by twenty it is 0.987, which is why the error hides in the short windows and
only shows itself when a five-day number sits next to a twenty-day one.
"""

from __future__ import annotations

import math
from typing import Optional

TRADING_DAYS = 252


def _bias_factor(n: int) -> float:
    """E[sigma_hat] / sigma for the zero-mean estimator over n returns.

    The chi distribution's mean. Computed rather than tabulated so it stays
    correct for any window someone later asks for.
    """
    if n <= 0:
        return 1.0
    try:
        return (math.sqrt(2.0 / n) * math.gamma((n + 1) / 2.0)
                / math.gamma(n / 2.0))
    except (ValueError, OverflowError):
        # Large n: the factor is within a whisker of 1 and the gammas overflow.
        return 1.0


def annualised(returns: list[float], *, min_returns: int = 3,
              correct_small_sample: bool = True) -> Optional[float]:
    """Annualised volatility in percent, or None if there is too little to say."""
    usable = [r for r in returns if r is not None and math.isfinite(r)]
    if len(usable) < min_returns:
        return None
    n = len(usable)
    sigma = math.sqrt(sum(r * r for r in usable) / n)
    if correct_small_sample:
        factor = _bias_factor(n)
        if factor > 0:
            sigma /= factor
    return round(sigma * math.sqrt(TRADING_DAYS) * 100.0, 4)


def log_returns(prices: list[float]) -> list[float]:
    """Consecutive log returns, skipping any non-positive price."""
    out = []
    for i in range(1, len(prices)):
        a, b = prices[i - 1], prices[i]
        if a and b and a > 0 and b > 0:
            out.append(math.log(b / a))
    return out
