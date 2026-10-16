import copy
from datetime import datetime, timedelta
from unittest.mock import patch
import pytest
from options_lab import iv_history as h, regime_agents as r
from options_lab.paper_agents import IST
from options_lab.tests.test_regime_agents import chain, bars
from options_lab.tests.test_streaming import QuoteCache, payload, NOW as STREAM_NOW, META, KEY

NOW = datetime(2026,9,29,15,0,tzinfo=IST)


def record(day, iv=13, **extra):
    return dict(day=day, iv=iv, at=day+'T15:30:00+05:30', unit='percent', **extra)


def test_real_bundle_is_consistent_and_cannot_backdate_availability():
    items=h.seed()['observations']
    assert len(items)>=20 and len({x['day'] for x in items})==len(items)
    for x in items:
        assert x['unit']=='percent' and x['source_url'].startswith('https://nsearchives.nseindia.com/')
        assert x['day'] < x['available_at'][:10]
        assert 2<=x['dte']<=14 and x['forward_quality']=='high'
        assert x['iv']==pytest.approx(sum(l['iv'] for l in x['legs'])/2)
        assert all(l['volume']>0 and l['open_interest']>0 and l['iv_quality']=='ok' for l in x['legs'])
    assert h.prior_observations(items,datetime(2026,9,29,0,0,tzinfo=IST))==[]


def test_actual_protobuf_fraction_normalized_once():
    data=payload();data['feeds'][KEY]['fullFeed']['marketFF']['iv']=.131378173828125
    cache=QuoteCache();cache.ingest(data,STREAM_NOW)
    rows=cache.rows(STREAM_NOW,META)
    assert rows[0]['iv']==pytest.approx(13.1378173828125)
    assert h.normalize_stream_rows(rows)==rows
    raw=[dict(iv=.13,provider='upstox')]
    assert h.normalize_stream_rows(raw)[0]['iv']==13
    assert raw[0]['iv']==.13
    for bad in (None,0,-1,float('nan'),float('inf'),3):
        assert h.stream_iv_percent(bad) is None


def test_prior_history_deduplicates_and_rejects_unknown_future_invalid():
    items=[record('2026-09-28'),record('2026-09-28',14),record('2026-09-29'),
           record('2026-05-01'),record('2026-09-25',float('nan')),
           record('2026-09-24',available_at='2026-10-01T00:00+05:30')]
    actual=h.prior_observations(items,NOW)
    assert len(actual)==1 and actual[0]['iv']==14


def test_bootstrap_preserves_every_account_and_corrects_old_units_idempotently():
    state=r.fresh();state.pop('iv_unit_version')
    state['iv_history']=[dict(day='2026-09-25',iv=.12,at='2026-09-25T15:30+05:30')]
    state['iv_today']=dict(day='2026-09-29',iv=.15,at='2026-09-29T14:00+05:30')
    state['agents']['iron_condor']['cash']=1234
    original=copy.deepcopy(state['agents'])
    assert h.bootstrap(state,NOW)
    assert state['agents']==original and state['iv_today']['iv']==15
    assert state['iv_today']['original_iv']==.15
    assert len(state['iv_history'])>=20
    saved=copy.deepcopy(state)
    assert not h.bootstrap(state,NOW)
    assert state==saved
    state['candles']=bars();state['session_bars']=3;state['calendar']=dict(date='2026-09-29',windows=[])
    ctx=r.context(state,chain(NOW),NOW)
    assert ctx['iv_days']>=20 and ctx['iv_percentile'] is not None


def test_stale_history_fails_closed_even_with_twenty_days():
    state=r.fresh();state['candles']=bars()
    state['iv_history']=[record((NOW-timedelta(days=20+i)).date().isoformat()) for i in range(25)]
    ctx=r.context(state,chain(NOW),NOW)
    assert ctx['iv_days']==25 and not ctx['iv_history_fresh'] and ctx['iv_percentile'] is None


def test_backfilled_series_not_used_before_retrieval_in_replay():
    from options_lab import replay
    from options_lab.paper_agents import timestamp
    seen=[]
    imported=[record('2026-09-25',available_at='2026-09-29T15:00+05:30')]
    first=timestamp('2026-09-28T00:00+05:30'); last=first+timedelta(days=1)
    actual=r.advance
    def capture(state,rows,now,allowed):
        seen.append(copy.deepcopy(state['iv_history']));actual(state,rows,now,allowed)
    with patch.object(r,'advance',side_effect=capture):
        replay.replay_frames([(first+timedelta(hours=11),[])],first,last,iv_seed=imported)
    assert seen==[[]]


def test_derivation_rejects_mismatched_day_and_current_day():
    with pytest.raises(ValueError,match='prior days'):
        h.derive_daily([], '2026-09-29',NOW.isoformat())
    with pytest.raises(ValueError,match='date mismatch'):
        h.derive_daily([dict(TckrSymb='NIFTY',TradDt='2026-09-25')],'2026-09-28',NOW.isoformat())


def test_daily_black76_derivation_recovers_known_volatility_at_spot_atm():
    from options_lab.tests.test_nse_history import chain_at, future
    rows=chain_at(24287.,.15,[24150,24200,24250,24300,24350])+[future(24287.)]
    observed=h.derive_daily(rows,'2026-08-21',NOW.isoformat())
    assert observed['strike']==24250 and observed['iv']==pytest.approx(15,abs=.02)
    assert observed['expiry']=='2026-08-25' and observed['forward_source']=='future'
    # A missing ATM put must not be replaced with a more distant traded pair.
    rows=[x for x in rows if not (x['OptnTp']=='PE' and x['StrkPric']=='24250')]
    with pytest.raises(ValueError,match='pair'):
        h.derive_daily(rows,'2026-08-21',NOW.isoformat())


def test_next_day_forward_observation_extends_without_duplicates():
    state=r.fresh();h.bootstrap(state,NOW)
    state['day']='2026-09-29';state['last_at']=NOW.isoformat()
    state['iv_today']=record('2026-09-29',14,available_at='2026-09-29T15:30:00+05:30')
    tomorrow=NOW+timedelta(days=1)
    h.bootstrap(state,tomorrow);r.advance(state,[],tomorrow,False)
    assert len(state['iv_history'])==31
    assert state['iv_history'][-1]['iv']==14
    assert len({x['day'] for x in state['iv_history']})==31
