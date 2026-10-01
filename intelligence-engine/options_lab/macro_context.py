"""Point-in-time research context, never order instructions or calendar clearance."""
from datetime import datetime, timedelta
import math

TOPICS = frozenset(('oil_supply', 'geopolitical', 'macro_news'))


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result


def available_news(bundle, now, lifetime=timedelta(hours=24)):
    """Require recorded receipt AND publication; retrospective date-only items stay out."""
    if now.tzinfo is None or lifetime.total_seconds() <= 0:
        raise ValueError('Aware clock and positive lifetime required')
    ready, excluded = [], []
    seen = set()
    for event in bundle.get('news_events', []):
        ident = event.get('id')
        reason = None
        try:
            refs = event.get('source_ids', [])
            if not ident or event.get('topic') not in TOPICS or not refs or not all(
                bundle.get('sources', {}).get(s, {}).get('url', '').startswith('https://') for s in refs
            ):
                raise ValueError('Missing provenance or topic')
            published = timestamp(event['published_at'])
            received = timestamp(event['first_seen_at'])
            if event.get('evidence_mode') != 'recorded' or event.get('revised'):
                reason = 'Retrospective or revised evidence: context only'
            elif received < published:
                reason = 'Inconsistent timestamps'
            elif now < received:
                reason = 'Not known yet'
            elif now - published > lifetime:
                reason = 'Expired context'
            elif ident in seen:
                reason = 'Duplicate'
            else:
                ready.append(dict(event, available_at=received.isoformat(), direction=None))
                seen.add(ident)
        except (KeyError, ValueError, TypeError):
            reason = 'Missing or invalid point-in-time evidence'
        if reason:
            excluded.append(dict(id=ident, reason=reason))
    return dict(events=ready, excluded=excluded, live_trading_approved=False)


def oil_move(previous, current, now, max_age=timedelta(minutes=5)):
    """Compare same-contract quotes. Never splice futures rolls or infer NIFTY direction."""
    if now.tzinfo is None:
        raise ValueError('Timezone required')
    for quote in (previous, current):
        price = quote['price']
        if isinstance(price, bool) or not isinstance(price, (float, int)) or not math.isfinite(price) or price <= 0:
            raise ValueError('Invalid oil price')
        if not quote.get('source'):
            raise ValueError('Source required')
        at, received = timestamp(quote['at']), timestamp(quote['received_at'])
        if at > received or received > now:
            raise ValueError('Quote not available at evaluation time')
    for key in ('instrument', 'currency', 'unit', 'source'):
        if not previous.get(key) or previous[key] != current.get(key):
            raise ValueError('Comparable quote identity required')
    start, end = timestamp(previous['at']), timestamp(current['at'])
    if end <= start or max_age.total_seconds() <= 0 or now-end > max_age:
        raise ValueError('Stale or unordered quotes')
    return dict(instrument=current['instrument'], change_pct=(current['price']/previous['price']-1)*100,
                interval_seconds=(end-start).total_seconds(), available_at=current['received_at'],
                direction=None, live_trading_approved=False)
