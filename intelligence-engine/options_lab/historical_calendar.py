"""Source-backed retrospective calendar; never writes live calendar reviews.

An event list does not establish absence of other events. Each session therefore
needs explicit coverage of every required category before it can become a review.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
REQUIRED = frozenset(('rbi', 'india_macro', 'budget', 'fomc', 'other_material'))


def build(bundle, days):
    if bundle.get('mode') != 'retrospective':
        raise ValueError('Retrospective mode required')
    sources = bundle.get('sources', {})
    def sourced(ids):
        return bool(ids) and all(i in sources and sources[i].get('url', '').startswith('https://')
                                 and sources[i].get('retrieved_on') for i in ids)
    events = bundle.get('events', [])
    for event in events:
        if event['category'] not in REQUIRED or not sourced(event.get('source_ids')):
            raise ValueError('Event needs recognized category and source provenance')
        at = datetime.fromisoformat(event['at'])
        if at.tzinfo is None:
            raise ValueError('Event timestamp must include timezone')
    reviews, blocked = {}, {}
    coverage = bundle.get('session_coverage', {})
    for day in days:
        datetime.strptime(day, '%Y-%m-%d')
        checks = coverage.get(day, {})
        missing = sorted(c for c in REQUIRED if not (
            checks.get(c, {}).get('reviewed') is True
            and sourced(checks[c].get('source_ids'))
            and checks[c].get('reviewed_at')
            and checks[c].get('note')))
        # A dated announcement with unknown time must never silently disappear
        # when a caller supplies otherwise complete session coverage.
        pending = [e for e in bundle.get('pending_events', []) if e.get('date') == day]
        if pending:
            missing = sorted(set(missing) | {'unresolved_event_time'})
        if missing:
            blocked[day] = missing
            continue
        windows = []
        for event in events:
            at = datetime.fromisoformat(event['at']).astimezone(IST)
            # Explicit research policy, not a claim about actual event duration.
            start = at - timedelta(minutes=30)
            end = at + timedelta(minutes=60)
            midnight = datetime.fromisoformat(day).replace(tzinfo=IST)
            a, b = max(start, midnight), min(end, midnight + timedelta(days=1, microseconds=-1))
            if a < b:
                windows.append({'start': a.isoformat(), 'end': b.isoformat()})
        reviews[day] = {'date': day, 'windows': windows}
    return {'mode': 'retrospective', 'reviews': reviews, 'blocked': blocked,
            'policy': '30 minutes before / 60 after sourced announcements; incomplete sessions withheld',
            'live_trading_approved': False}
