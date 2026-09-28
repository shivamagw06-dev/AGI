import copy
import gzip
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import pytest
from options_lab import regime_agents as r, paper_agents as p
from options_lab.streaming import discover_futures, universe, NIFTY

NOW=datetime(2026,9,28,11,0,tzinfo=p.IST)

def quote(key,kind,strike,bid=20,ask=20.5,now=NOW,delta=.17):
    return dict(instrument_key=key,option_type=kind,strike=strike,expiry='2026-10-06',lot_size=65,
                bid=bid,ask=ask,bid_size=650,ask_size=650,volume=10000,oi=1000,iv=20,
                greeks=dict(delta=delta),provider='upstox',underlying_key=NIFTY,
                quote_at=now.isoformat(),captured_at=now.isoformat(),spot_at=now.isoformat(),spot=25000)

def chain(now=NOW):
    return [quote('atmC','CE',25000,10,10.2,now,.5),quote('atmP','PE',25000,10,10.2,now,-.5),
            quote('shortC','CE',25100,6,6.1,now),quote('longC','CE',25150,1,1.02,now,.1),
            quote('shortP','PE',24900,6,6.1,now,-.17),quote('longP','PE',24850,1,1.02,now,-.1)]

def ctx(name='RANGE_HIGH_IV',event='CLEAR'):
    return dict(name=name,event=event,iv_percentile=70,atr=10,iv=20)

def bars(trending=False):
    return [dict(at=int(NOW.timestamp())-(51-i)*300,open=25000+i*5 if trending else 25000,
                 close=25002+i*5 if trending else 25000,
                 high=25004+i*5 if trending else 25002,low=24998+i*5 if trending else 24998) for i in range(50)]

def ready():
    state=r.fresh();state.update(last_at=(NOW-timedelta(seconds=1)).isoformat(),day='2026-09-28',
        calendar=dict(date='2026-09-28',windows=[]),regime=ctx(),candles=bars(),session_bars=3)
    return state


def test_indicator_wilder_trend_and_flat():
    trend=r.indicators(bars(True));flat=r.indicators(bars())
    assert trend['adx']==pytest.approx(100)
    assert trend['ema20']>trend['ema50']
    assert flat['adx']==0 and flat['atr']==4
    assert r.indicators(bars()[:49]) is None


def test_calendar_fail_closed_and_post_event_expiry():
    assert r.event_state(dict(date=None,windows=[]),NOW)=='UNREVIEWED'
    conf=dict(date='2026-09-28',windows=[dict(start=(NOW-timedelta(minutes=5)).isoformat(),end=NOW.isoformat())])
    assert r.event_state(conf,NOW)=='BLACKOUT'
    assert r.event_state(conf,NOW+timedelta(minutes=30))=='POST_EVENT'
    assert r.event_state(conf,NOW+timedelta(minutes=61))=='CLEAR'
    assert r.event_state(conf,NOW+timedelta(days=1))=='UNREVIEWED'
    with pytest.raises(ValueError):r.calendar(dict(date='2099-01-01',windows=[dict(start='2099-01-01T10:00',end='2099-01-01T11:00')]))


def test_iv_recording_does_not_require_event_review_or_50_bars():
    state=r.fresh();state['candles']=bars()[:3]
    c=r.context(state,chain(),NOW)
    assert c['iv']==20 and c['name']=='EVENT_RISK' and c['iv_percentile'] is None
    state['calendar']=dict(date='2026-09-28',windows=[]);state['candles']=bars();state['session_bars']=3
    state['iv_history']=[dict(day=(NOW-timedelta(days=i+1)).date().isoformat(),iv=10) for i in range(20)]
    c=r.context(state,chain(),NOW)
    assert c['iv_percentile']==100 and c['name']=='RANGE_HIGH_IV'
    state['iv_history']=state['iv_history'][:19]
    assert r.context(state,chain(),NOW)['iv_percentile'] is None


@pytest.mark.parametrize('name,count', [('iron_condor',4),('iron_fly',4),('regime_credit',2),('long_straddle',2),('long_strangle',2)])
def test_basket_selection(name,count):
    c=ctx(event='POST_EVENT')
    if name=='regime_credit':c['name']='TREND_UP'
    if name.startswith('long_'):c.update(name='VOL_BREAKOUT',iv_percentile=20)
    legs,_=r.choose(name,c,chain(),25000,bars())
    assert len(legs)==count and len({l['instrument_key'] for l in legs})==count
    assert len({l['expiry'] for l in legs})==1


def test_fly_requires_reviewed_post_event_not_just_range():
    assert r.choose('iron_fly',ctx(),chain(),25000,bars())[0] is None
    missing=chain()
    for x in missing:x['greeks']={}
    assert r.choose('iron_condor',ctx(),missing,25000,bars())[0] is None
    assert r.choose('long_straddle',dict(ctx('VOL_BREAKOUT'),iv_percentile=None),chain(),25000,bars())[0] is None


def test_regime_debit_requires_pullback_and_uses_actual_chain():
    b=bars(True);b[-2]['low']=24000;b[-1]['close']=26000
    legs,_=r.choose('regime_debit',ctx('TREND_UP'),chain(),25000,b)
    assert [l['side'] for l in legs]==['BUY','SELL']
    assert all(l['option_type']=='CE' for l in legs)


def test_futures_vwap_is_own_contract_and_full_notional_reserve():
    f=quote('future','FUT',0,25000,25001);f.update(vwap=24990,ltp=25000)
    legs,_=r.choose('futures_trend',ctx('TREND_UP'),[f],25000,bars())
    fill=r.execute(legs,{'future':f},NOW,True)
    t=r.terms(fill,ctx())
    assert t['reserve']>1600000 and t['max_loss'] is None
    assert r.admission(ready(),'futures_trend',t,fill) is not None
    assert r.choose('futures_trend',ctx('TREND_UP'),chain(),25000,bars())[0] is None
    f['vwap']=None
    assert r.choose('futures_trend',ctx('TREND_UP'),[f],25000,bars())[0] is None


def test_four_leg_payoff_uses_one_side_max_loss_not_sum_of_wings():
    legs,_=r.choose('iron_condor',ctx(),chain(),25000,bars())
    fills=r.execute(legs,{q['instrument_key']:q for q in chain()},NOW,True)
    t=r.terms(fills,ctx());credit=sum((1 if f['side']=='SELL' else -1)*f['price']*65 for f in fills)
    assert t['max_loss']==pytest.approx(50*65-credit+t['entry_cost'])
    assert t['max_profit']==pytest.approx(credit-t['entry_cost'])
    assert r.terms([dict(fills[0],side='SELL')],ctx()) is None


def test_long_straddle_full_premium_risk_and_uncapped_upside():
    legs,_=r.choose('long_straddle',dict(ctx('VOL_BREAKOUT'),iv_percentile=20),chain(),25000,bars())
    fills=r.execute(legs,{q['instrument_key']:q for q in chain()},NOW,True)
    t=r.terms(fills,ctx())
    assert t['max_loss']==pytest.approx(-r.s.cashflow(fills))
    assert t['max_profit'] is None


@pytest.mark.parametrize('fault',['stale','same','skew','size','expiry','lot','missing'])
def test_entry_never_fills_incomplete_or_mismatched_basket(fault):
    legs,_=r.choose('iron_condor',ctx(),chain(),25000,bars())
    quotes={q['instrument_key']:q for q in chain(NOW+timedelta(seconds=1))};q=quotes[legs[0]['instrument_key']]
    if fault=='stale':q['quote_at']=(NOW-timedelta(seconds=10)).isoformat()
    if fault=='same':q['quote_at']=NOW.isoformat()
    if fault=='skew':q['quote_at']=(NOW-timedelta(seconds=1)).isoformat()
    if fault=='size':q['ask_size']=1
    if fault=='expiry':q['expiry']='2026-10-13'
    if fault=='lot':q['lot_size']=25
    if fault=='missing':del quotes[q['instrument_key']]
    assert r.execute(legs,quotes,NOW+timedelta(seconds=1),True,NOW.isoformat()) is None


def pending(state,name='long_straddle'):
    context=dict(ctx('VOL_BREAKOUT'),iv_percentile=20)
    legs,_=r.choose(name,context,chain(),25000,bars())
    state['agents'][name]['pending']=dict(legs=legs,signal_at=(NOW-timedelta(seconds=1)).isoformat(),context=context)


def test_entry_exit_shared_cash_and_fees_reconcile():
    state=ready();pending(state)
    r.advance(state,chain(),NOW,True)
    a=state['agents']['long_straddle'];assert a['position']
    assert state['equity']==pytest.approx(100000+sum(x['equity'] for x in state['agents'].values()))
    later=NOW+timedelta(seconds=1)
    state['calendar']=dict(date='2026-09-28',windows=[dict(start=later.isoformat(),end=(later+timedelta(minutes=1)).isoformat())])
    r.advance(state,chain(later),later,False)
    assert a['position'] is None and len(a['trades'])==1
    t=a['trades'][0]
    assert t['pnl']==pytest.approx(r.s.cashflow(t['legs'])+r.s.cashflow(t['exit_legs']),abs=.01)
    assert state['reserve']==0 and state['equity']==pytest.approx(100000+a['cash'])


def test_shared_overlap_risk_and_entry_limits():
    state=ready();pending(state)
    # Competing identical baskets cannot double-allocate one contract.
    state['agents']['long_strangle']['pending']=copy.deepcopy(state['agents']['long_straddle']['pending'])
    r.advance(state,chain(),NOW,True)
    assert state['agents']['long_straddle']['position']
    assert state['agents']['long_strangle']['position'] is None
    assert 'Overlapping' in state['agents']['long_strangle']['status']
    t=dict(planned_risk=2001,reserve=2001)
    assert 'risk' in r.admission(ready(),'iron_condor',t,[])
    state=ready();state['agents']['iron_condor']['daily_entries']=4
    assert 'daily entry' in r.admission(state,'iron_fly',dict(planned_risk=100,reserve=100),[])


def test_missing_exit_halts_whole_account_and_keeps_position():
    state=ready();pending(state);r.advance(state,chain(),NOW,True)
    before=state['equity'];later=NOW+timedelta(seconds=1)
    r.advance(state,[],later,True)
    assert state['halted'] and state['agents']['long_straddle']['blocked']
    assert state['agents']['long_straddle']['position'] and state['equity']==before
    pending(state,'long_strangle')
    r.advance(state,chain(later+timedelta(seconds=1)),later+timedelta(seconds=1),True)
    assert state['agents']['long_strangle']['position'] is None


def test_duplicate_pause_gap_and_new_day():
    state=ready();pending(state);r.advance(state,chain(),NOW,False)
    assert state['agents']['long_straddle']['position'] is None
    snapshot=copy.deepcopy(state);r.advance(state,chain(),NOW,True);assert state==snapshot
    state=ready();pending(state);r.advance(state,chain(),NOW,True)
    later=NOW+timedelta(seconds=6);r.advance(state,chain(later),later,True)
    assert state['halted'] and state['session_bars']==0


def test_storage_preserves_benchmarks_and_pins_new_baskets():
    with tempfile.TemporaryDirectory() as d,patch.object(p,'paths',return_value=(Path(d)/'source',Path(d)/'paper')):
        p.control('start');state=p.fresh_state();state['version']='nifty-paper-v2-1s'
        state['agents']['opening_range']['cash']=99123
        state['research']=ready();pending(state['research'])
        with p.database() as db:db.execute('UPDATE sessions SET state=?',(json.dumps(state),))
        assert {'atmC','atmP'}<=p.pinned_contracts()
        p.stream_tick(chain(),dict(status='Testing'),now=NOW)
        data=p.dashboard()['live'];assert data['agents']['opening_range']['cash']==99123
        assert len(data['agents'])==11 and data['research']['version']==r.VERSION
        assert 'candles' not in data['research']
        p.control('pause');assert p.dashboard()['enabled'] is False


def test_discovery_filters_exact_nifty_and_subscribes_future():
    future=dict(segment='NSE_FO',instrument_type='FUT',underlying_key=NIFTY,instrument_key='F',
                expiry=int((NOW+timedelta(days=20)).timestamp()*1000),lot_size=65)
    data=[future,dict(future,underlying_key='NSE_INDEX|Nifty Bank',instrument_key='B')]
    from io import BytesIO
    with patch('urllib.request.urlopen',return_value=BytesIO(gzip.compress(json.dumps(data).encode()))):
        contracts=discover_futures(NOW)
    assert len(contracts)==1
    selected=universe(contracts,25000,NOW)
    assert selected['F']['option_type']=='FUT' and selected['F']['strike']==0


def test_futures_cash_only_posts_fees_and_price_difference():
    f=quote('F','FUT',0,25000,25001);entry=r.execute([dict(f,side='BUY')],{'F':f},NOW,True)[0]
    exit=copy.deepcopy(entry);exit.update(side='SELL',price=entry['price']+10,charges=r.charges((entry['price']+10)*65,'SELL',True))
    a=dict(cash=-entry['charges']['total'],position=dict(legs=[entry]))
    assert r.mark(a,[exit])==pytest.approx(650-entry['charges']['total']-exit['charges']['total'])


def test_daily_loss_exits_all_markable_positions_even_when_paused():
    state=ready();pending(state);r.advance(state,chain(),NOW,True)
    state['daily_start']=state['equity']+4000
    later=NOW+timedelta(seconds=1);r.advance(state,chain(later),later,False)
    assert state['halted'] and state['agents']['long_straddle']['position'] is None
    assert state['agents']['long_straddle']['trades'][0]['reason']=='Event / shared risk exit'


def test_warmup_uses_completed_bars_only_and_persists_across_sessions():
    state=r.fresh();start=NOW.replace(hour=9,minute=15,second=0)
    # This is synthetic validation data, never written to production evidence.
    for second in range(901):
        at=start+timedelta(seconds=second)
        r.advance(state,chain(at),at,False)
    assert len(state['candles'])==3 and state['session_bars']==3
    assert state['candles'][-1]['at']==int(start.timestamp())+600
    assert state['iv_today']['iv']==20
    future=start+timedelta(days=1)
    r.advance(state,chain(future),future,False)
    assert len(state['candles'])==3 and state['session_bars']==0
    assert len(state['iv_history'])==1 and state['iv_history'][0]['day']=='2026-09-28'


def test_no_annualised_five_minute_rv_across_missing_bars():
    b=bars();b[-1]['at']+=300
    assert r.indicators(b)['rv'] is None


def test_pending_unknown_event_never_enters_and_calendar_validation():
    state=ready();pending(state);state['calendar']['date']=None
    r.advance(state,chain(),NOW,True)
    assert state['agents']['long_straddle']['pending'] is None
    assert state['agents']['long_straddle']['position'] is None
    assert 'calendar' in state['agents']['long_straddle']['status']
    payload=dict(date='2099-01-01',windows=[dict(start='2099-01-01T13:00:00+05:30',end='2099-01-01T14:00:00+05:30')])
    assert r.calendar(payload)['windows']==payload['windows']
    payload['windows'][0]['end']='2099-01-01T12:00:00+05:30'
    with pytest.raises(ValueError):r.calendar(payload)
