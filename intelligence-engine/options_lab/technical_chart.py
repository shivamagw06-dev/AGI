"""Bounded chart evidence, using the same completed candles as paper agents."""
from .regime_agents import indicators


def chart_payload(state):
    research = state.get('research') or {}
    spreads = state.get('spreads') or {}
    bars = research.get('candles') or spreads.get('candles') or []
    bars = bars[-100:]
    points = []
    for i, bar in enumerate(bars):
        point = {k: bar[k] for k in ('at', 'open', 'high', 'low', 'close')}
        history = bars[:i+1]
        point.update(indicators(history) or {})
        closes = [b['close'] for b in history]
        for length in (3, 10):
            point[f'sma{length}'] = sum(closes[-length:])/length if len(closes)>=length else None
        points.append(point)
    return dict(interval_seconds=300, source='Recorded Upstox one-second samples',
                candles=points, as_of=state.get('last_at'),
                regime=research.get('regime'), volume_available=False,
                note='Completed sampled candles only. Gaps are not reconstructed. SMA3/10: spread benchmarks; EMA20/50, ADX and ATR: research agents. Nifty spot has no traded volume; VWAP is not calculated from index ticks.')
