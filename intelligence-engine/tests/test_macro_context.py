from datetime import datetime
import pytest
from options_lab.macro_context import available_news, oil_move

NOW=datetime.fromisoformat('2026-03-11T12:00:00+05:30')

def bundle():
    return {'sources':{'s':{'url':'https://example.org/event'}},'news_events':[dict(id='a',topic='geopolitical',source_ids=['s'],published_at='2026-03-11T11:00:00+05:30',first_seen_at='2026-03-11T11:02:00+05:30',evidence_mode='recorded')]}

def test_no_lookahead_or_retrospective_triggers():
    b=bundle()
    assert len(available_news(b,NOW)['events'])==1
    b['news_events'][0]['first_seen_at']='2026-03-11T12:01:00+05:30'
    assert not available_news(b,NOW)['events']
    b=bundle(); b['news_events'][0]['evidence_mode']='retrospective'
    assert not available_news(b,NOW)['events']

def test_date_only_and_duplicates():
    b=bundle(); b['news_events']*=2
    assert len(available_news(b,NOW)['events'])==1
    b=bundle(); del b['news_events'][0]['published_at']
    assert not available_news(b,NOW)['events']

def quotes():
    base=dict(price=80,instrument='BRENT_CONTRACT_X',currency='USD',unit='barrel',source='fixture')
    return (dict(base,at='2026-03-11T11:00:00+05:30',received_at='2026-03-11T11:00:01+05:30'),dict(base,price=84,at='2026-03-11T11:59:00+05:30',received_at='2026-03-11T11:59:01+05:30'))

def test_oil_change_requires_same_contract_and_fresh_data():
    a,b=quotes(); assert oil_move(a,b,NOW)['change_pct']==pytest.approx(5)
    b['instrument']='ROLLED_CONTRACT'
    with pytest.raises(ValueError):oil_move(a,b,NOW)
    a,b=quotes(); b['price']=float('nan')
    with pytest.raises(ValueError):oil_move(a,b,NOW)
    a,b=quotes(); b['at']='2026-03-11T11:30:00+05:30'
    with pytest.raises(ValueError):oil_move(a,b,NOW)
