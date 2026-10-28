"""Audited historical ATM-IV bootstrap; percentages throughout, no order APIs.

The bundled observations are derived from traded NSE daily option closes. They
are an EOD near-expiry proxy, not intraday quotes or a constant-maturity index.
Availability is the actual retrieval time, so importing them cannot leak future
knowledge into an earlier replay. Forward observations extend the rolling series.
"""
from functools import lru_cache
from pathlib import Path
from datetime import date, timedelta
import copy
import json
import math

UNIT_VERSION = 1
SEED_PATH = Path(__file__).with_name('reference_data') / 'nifty_atm_iv_history.json'


def stream_iv_percent(value):
    """Upstox V3 protobuf iv is a fraction (0.13 = 13%), not percentage points."""
    try:
        value = float(value) * 100
        return value if math.isfinite(value) and 0 < value < 200 else None
    except (ValueError, TypeError):
        return None


def normalize_stream_rows(rows):
    """Decode old stored frames without changing their immutable source payloads."""
    return [dict(r, iv=stream_iv_percent(r.get('iv')), iv_unit='percent')
            if r.get('iv_unit') != 'percent' else r for r in rows]


@lru_cache(maxsize=1)
def seed():
    payload = json.loads(SEED_PATH.read_text())
    if payload.get('schema') != 1 or payload.get('underlying') != 'NIFTY':
        raise ValueError('Invalid NIFTY IV history bundle')
    return payload


def prior_observations(observations, now):
    from .paper_agents import IST, timestamp, number
    day = now.astimezone(IST).date()
    earliest = (day - timedelta(days=120)).isoformat()
    by_day = {}
    for item in observations:
        try:
            d = date.fromisoformat(item['day'])
            iv = number(item.get('iv'))
            if not (earliest <= d.isoformat() < day.isoformat() and iv and 0 < iv < 200):
                continue
            if item.get('unit', 'percent') != 'percent':
                continue
            if item.get('at') and timestamp(item['at']) >= now:
                continue
            if item.get('available_at') and timestamp(item['available_at']) > now:
                continue
            by_day[item['day']] = item
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(by_day.values(), key=lambda x: x['day'])[-60:]


def bootstrap(state, now):
    """Merge public history only; never reset balances, positions or trade logs."""
    from .paper_agents import IST
    changed = False
    if state.get('iv_unit_version') != UNIT_VERSION:
        # Older forward observations were saved directly from decimal V3 IV.
        for item in state.get('iv_history', []) + ([state['iv_today']] if state.get('iv_today') else []):
            if item.get('unit') != 'percent':
                item['original_iv'] = item.get('iv')
                item['iv'] = stream_iv_percent(item.get('iv'))
                item.update(unit='percent', source='Upstox V3 stream', unit_corrected=True)
        state['iv_unit_version'] = UNIT_VERSION
        changed = True
    payload = seed()
    today = now.astimezone(IST).date().isoformat()
    revision = (payload['generated_at'], today)
    if state.get('iv_seed_revision') != list(revision):
        # Historical close replaces a partial prior live day where available.
        merged = prior_observations(state.get('iv_history', []) + copy.deepcopy(payload['observations']), now)
        state['iv_history'] = merged
        state['iv_seed_revision'] = list(revision)
        state['iv_bootstrap'] = dict(imported_at=now.isoformat(), count=len(merged),
            first_day=merged[0]['day'] if merged else None,
            last_day=merged[-1]['day'] if merged else None,
            source='NSE daily option closes + forward Upstox observations',
            method='Near-expiry ATM call/put IV proxy; changing tenor and EOD/intraday basis')
        changed = True
    if changed:
        state['iv_recompute'] = True
    return changed


def derive_daily(rows, day, retrieved_at):
    """One same-strike pair, nearest eligible 2–14-day expiry; no fallback tenor."""
    import hashlib
    from . import nse_history as n
    from .paper_agents import timestamp, IST
    day = date.fromisoformat(str(day))
    if day >= timestamp(retrieved_at).astimezone(IST).date():
        raise ValueError('Only completed prior days may be imported')
    rows = [r for r in rows if r.get('TckrSymb') == 'NIFTY']
    if not rows or any(str(r.get('TradDt', ''))[:10] != day.isoformat() for r in rows):
        raise ValueError('Source trading date mismatch')
    records = n.option_records(rows, underlyings={'NIFTY'}, with_greeks=False)
    expiries = sorted({str(r['XpryDt'])[:10] for r in rows
                       if r.get('OptnTp') in ('CE', 'PE')
                       and 2 <= (date.fromisoformat(str(r['XpryDt'])[:10])-day).days <= 14})
    if not expiries:
        raise ValueError('No eligible expiry')
    chain = [r for r in records if r['expiry'] == expiries[0]]
    spots = [r['underlying_close'] for r in chain if r['underlying_close'] and r['underlying_close'] > 0]
    if not spots or max(spots) != min(spots):
        raise ValueError('Missing or inconsistent underlying close')
    spot = spots[0]
    strikes = {float(r['StrkPric']) for r in rows if str(r['XpryDt'])[:10] == expiries[0]
               and r.get('OptnTp') in ('CE', 'PE') and float(r['StrkPric']) > 0}
    strike = min(strikes, key=lambda k: (abs(k-spot), k))
    pair = [r for r in chain if r['strike'] == strike]
    if len(pair) != 2 or {r['option_type'] for r in pair} != {'CE', 'PE'}:
        raise ValueError('Missing same-strike ATM call/put pair')
    if any(r['iv_quality'] != 'ok' or r['forward_quality'] != 'high'
           or not r['iv'] or not .5 < r['iv'] < 100 or not r['open_interest']
           or r['open_interest'] <= 0 for r in pair):
        raise ValueError('ATM quality gate')
    iv = sum(r['iv'] for r in pair)/2
    if abs(pair[0]['iv'] - pair[1]['iv']) > max(3, iv*.3):
        raise ValueError('Call/put IV disagreement')
    return dict(day=day.isoformat(), at=day.isoformat()+'T15:30:00+05:30',
        available_at=retrieved_at, iv=round(iv, 6), unit='percent',
        source='NSE F&O bhavcopy', method='near-expiry-atm-ce-pe-black76-v1',
        source_url=n.ARCHIVE.format(yyyymmdd=day.strftime('%Y%m%d')),
        source_rows_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
        expiry=expiries[0], dte=pair[0]['dte_days'], strike=strike, spot=spot,
        rate_pct=n.DEFAULT_RATE_PCT, forward=pair[0]['forward'],
        forward_source=pair[0]['forward_source'], forward_quality=pair[0]['forward_quality'],
        forward_pair_count=pair[0]['forward_pair_count'], forward_dispersion_bp=pair[0]['forward_dispersion_bp'],
        legs=[{k:r[k] for k in ('option_type','close','volume','open_interest','iv','iv_quality')} for r in pair])
