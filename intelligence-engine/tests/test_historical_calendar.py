from options_lab.historical_calendar import build, REQUIRED
import pytest


def bundle():
    return dict(mode='retrospective',sources={'s':dict(url='https://example.org/source',retrieved_on='2026-10-02')},
                events=[dict(category='rbi',at='2026-02-06T10:00:00+05:30',source_ids=['s'])],session_coverage={})


def test_known_event_does_not_clear_unreviewed_day():
    result=build(bundle(),['2026-02-06'])
    assert not result['reviews']
    assert set(result['blocked']['2026-02-06'])==REQUIRED


def test_complete_explicit_review_creates_window():
    b=bundle()
    b['session_coverage']['2026-02-06']={c:dict(reviewed=True,source_ids=['s'],reviewed_at='2026-10-02T00:00:00+05:30',note='synthetic test fixture') for c in REQUIRED}
    result=build(b,['2026-02-06'])
    assert result['reviews']['2026-02-06']['windows']==[dict(start='2026-02-06T09:30:00+05:30',end='2026-02-06T11:00:00+05:30')]
    assert result['live_trading_approved'] is False


def test_naive_and_unsourced_events_rejected():
    b=bundle(); b['events'][0]['at']='2026-02-06T10:00:00'
    with pytest.raises(ValueError):build(b,[])
    b=bundle(); b['events'][0]['source_ids']=['missing']
    with pytest.raises(ValueError):build(b,[])


@pytest.mark.parametrize('at,day,start,end', [
    ('2025-10-29T14:00:00-04:00','2025-10-29','23:00:00','23:59:59.999999'),
    ('2025-12-10T14:00:00-05:00','2025-12-11','00:00:00','01:30:00'),
])
def test_us_release_timezone_rollover(at,day,start,end):
    b=bundle()
    b['events']=[dict(category='fomc',at=at,source_ids=['s'])]
    b['session_coverage'][day]={c:dict(reviewed=True,source_ids=['s'],reviewed_at='2026-10-02T00:00:00+05:30',note='synthetic fixture') for c in REQUIRED}
    result=build(b,[day])
    assert result['reviews'][day]['windows']==[dict(start=f'{day}T{start}+05:30',end=f'{day}T{end}+05:30')]


def test_pending_announcement_blocks_otherwise_reviewed_day():
    b=bundle(); day='2026-02-06'
    b['session_coverage'][day]={c:dict(reviewed=True,source_ids=['s'],reviewed_at='2026-10-02T00:00:00+05:30',note='synthetic fixture') for c in REQUIRED}
    b['pending_events']=[dict(date=day,category='rbi',status='announcement_time_unverified')]
    result=build(b,[day])
    assert result['reviews']=={}
    assert result['blocked'][day]==['unresolved_event_time']


def test_rbi_inventory_does_not_clear_sessions():
    import json
    from pathlib import Path
    b=json.loads((Path(__file__).parents[1]/'options_lab/reference_data/historical_event_calendar.json').read_text())
    events=[e for e in b['events'] if e['category']=='rbi']
    assert {e['at'] for e in events}=={'2026-02-06T10:00:00+05:30','2026-04-08T10:00:00+05:30'}
    assert not build(b,[e['at'][:10] for e in events])['reviews']
