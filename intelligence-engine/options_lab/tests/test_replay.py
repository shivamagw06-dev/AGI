import copy
import json
import sqlite3
import zlib
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import pytest
from options_lab import replay as b, paper_agents as p, regime_agents as r, spread_agents as s
from options_lab.tests.test_regime_agents import NOW,chain,quote,ctx,ready

@pytest.fixture
def store(tmp_path):
    with patch.object(p,'paths',return_value=(tmp_path/'source.sqlite',tmp_path/'paper.sqlite')):
        with p.database() as db:b.schema(db)
        yield tmp_path


def test_no_evidence_reports_all_eleven_as_not_tested_and_never_touches_live(store):
    p.control('start')
    with p.database() as db:
        before=db.execute('SELECT state FROM sessions').fetchone()[0]
    result=b.run(b.request_config('2026-09-01','2026-09-28'))
    assert len(result['agents'])==11 and result['status']=='no_data'
    assert set(result['decision_audit'])==set(result['validation'])==set(result['agents'])
    assert all(x['status']=='insufficient_evidence' for x in result['validation'].values())
    assert all(a['closed_trades'] is None and a['net_pnl'] is None and a['evidence_status']=='insufficient_data' for a in result['agents'].values())
    with p.database() as db:assert db.execute('SELECT state FROM sessions').fetchone()[0]==before


def test_legacy_snapshots_are_not_upscaled_and_real_legacy_pnl_is_retained(store):
    from options_lab.tests.test_paper_agents import quote as oldquote
    rows=[oldquote(t,spot) for t,spot in [('09:15',25000),('09:30',25010),('09:45',25005),('10:00',25060),('10:15',25080)]]
    rows.append(oldquote('10:30',25000,bid=75,ask=76))
    with sqlite3.connect(store/'source.sqlite') as db:
        cols=list(rows[0]);db.execute('CREATE TABLE option_snapshots ('+','.join(cols)+',local_date)')
        for row in rows:db.execute('INSERT INTO option_snapshots VALUES('+','.join('?' for _ in range(len(cols)+1))+')',list(row.values())+['2026-09-28'])
    result=b.run(b.request_config('2026-09-28','2026-09-28'))
    assert result['agents']['opening_range']['closed_trades']==1
    assert result['agents']['opening_range']['net_pnl']<0
    assert result['agents']['opening_range']['replay_interval_seconds']==900
    assert result['coverage']['frames']==0
    assert result['agents']['iron_condor']['net_pnl'] is None


def test_recorded_frames_use_ist_date_boundaries(store):
    frames=[datetime(2026,9,27,18,29,tzinfo=timezone.utc),datetime(2026,9,28,4,0,tzinfo=timezone.utc),datetime(2026,9,28,18,31,tzinfo=timezone.utc)]
    with p.database() as db:
        for now in frames:db.execute('INSERT INTO second_frames VALUES(?,?)',(now.isoformat(),zlib.compress(json.dumps(chain(now)).encode())))
    result=b.run(b.request_config('2026-09-28','2026-09-28'))
    assert result['coverage']['frames']==1
    assert result['coverage']['warmup_frames']==1
    assert result['coverage']['days']==['2026-09-28']


def test_sparse_frames_cannot_create_candles_or_results():
    first,last=b.bounds('2026-09-28','2026-09-28')
    frames=[(NOW+timedelta(minutes=i*15),chain(NOW+timedelta(minutes=i*15))) for i in range(10)]
    result,c=b.replay_frames(frames,first,last,overrides={'2026-09-28':dict(date='2026-09-28',windows=[])})
    assert c['complete_bars']==0 and c['gaps_over_5s']==9
    assert result['agents']['trend_pullback']['net_pnl'] is None


def test_calendar_reviews_cannot_look_ahead():
    first,last=b.bounds('2026-09-28','2026-09-28')
    review=dict(date='2026-09-28',windows=[],reviewed_at=(NOW+timedelta(seconds=1)).isoformat())
    seen=[]
    actual=r.advance
    def capture(state,rows,now,allowed):
        seen.append(r.event_state(state['calendar'],now));actual(state,rows,now,allowed)
    with patch.object(r,'advance',side_effect=capture):
        b.replay_frames([(NOW,chain()),(NOW+timedelta(seconds=1),chain(NOW+timedelta(seconds=1)))],first,last,[review])
    assert seen==['UNREVIEWED','CLEAR']


def test_past_calendar_overrides_are_explicit_and_do_not_change_live(store):
    config=b.request_config('2026-09-28','2026-09-28',[dict(date='2026-09-28',windows=[],reviewed=True)])
    result=b.run(config)
    assert result['coverage']['calendar_mode']=='retrospective_admin_inputs'
    assert result['coverage']['retrospective_dates']==['2026-09-28']
    with p.database() as db:assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0


@pytest.mark.parametrize('review',[
    dict(date='2026-09-28',windows=[],reviewed=False),
    dict(date='2026-09-27',windows=[],reviewed=True),
    dict(date='2026-09-28',windows=[dict(start='2026-09-28T10:00',end='2026-09-28T11:00')],reviewed=True),
    dict(date='2026-09-28',windows=[dict(start='2026-09-28T11:00+05:30',end='2026-09-28T10:00+05:30')],reviewed=True),
])
def test_calendar_invalid_or_unconfirmed_rejected(review):
    with pytest.raises(ValueError):b.request_config('2026-09-28','2026-09-28',[review])


def test_iv_seed_excludes_future_days_and_no_duplicate_warmup_days():
    first,last=b.bounds('2026-09-28','2026-09-28')
    seed=[dict(day='2026-09-25',iv=10,at='2026-09-25T15:00+05:30'),dict(day='2026-09-28',iv=15,at='2026-09-28T15:00+05:30')]
    seen=[];actual=r.advance
    def capture(state,rows,now,allowed):
        seen.append(copy.deepcopy(state['iv_history']));actual(state,rows,now,allowed)
    warm=NOW-timedelta(days=3)
    with patch.object(r,'advance',side_effect=capture):b.replay_frames([(warm,chain(warm)),(NOW,chain())],first,last,iv_seed=seed)
    assert seen[0]==[] and [x['day'] for x in seen[1]]==['2026-09-25']


def test_iv_becomes_available_during_replay_without_leaking_before_import():
    first,last=b.bounds('2026-09-28','2026-09-28')
    available=NOW+timedelta(seconds=1)
    seed=[dict(day='2026-09-25',iv=10,at='2026-09-25T15:30+05:30',available_at=available.isoformat()),
          dict(day='2026-09-28',iv=20,at='2026-09-28T15:30+05:30',available_at=available.isoformat())]
    seen=[];actual=r.advance
    def capture(state,rows,now,allowed):
        seen.append(copy.deepcopy(state['iv_history']));actual(state,rows,now,allowed)
    with patch.object(r,'advance',side_effect=capture):
        _,coverage=b.replay_frames([(NOW,chain()),(available,chain(available))],first,last,iv_seed=seed)
    assert seen[0]==[]
    assert [x['day'] for x in seen[1]]==['2026-09-25']
    assert coverage['max_prior_iv_days']==1


@pytest.mark.parametrize('name',r.NAMES)
def test_all_seven_replay_the_same_fill_exit_and_fee_ledger_as_forward(name):
    state=ready()
    state['calendar']=dict(date='2026-09-28',windows=[])
    context=ctx('TREND_UP' if name in ('regime_credit','regime_debit','futures_trend') else 'VOL_BREAKOUT' if name.startswith('long_') else 'RANGE_HIGH_IV',event='POST_EVENT')
    context['iv_percentile']=20 if name.startswith('long_') else 70
    quotes=chain()
    if name=='futures_trend':
        q=quote('fut','FUT',0,100,100.01);q.update(ltp=100,vwap=99);quotes.append(q)
    bars=state['candles'];bars[-2]['low']=24000;bars[-1]['close']=26000
    legs,_=r.choose(name,context,quotes,25000,bars)
    assert legs
    fills=r.execute(legs,{q['instrument_key']:q for q in quotes},NOW,True)
    terms=r.terms(fills,context)
    assert terms
    a=state['agents'][name]
    a.update(cash=-terms['entry_cost'] if name=='futures_trend' else s.cashflow(fills),
             position=dict(**terms,legs=fills,equity_before=0.,entry_at=(NOW-timedelta(hours=3)).isoformat(),max_seconds=1800))
    # This fixture starts with an already-funded paper position to exercise all exit ledgers.
    def fresh():return copy.deepcopy(state)
    expected=fresh();r.advance(expected,quotes,NOW,True)
    with patch.object(r,'fresh',side_effect=fresh):
        result,_=b.replay_frames([(NOW,quotes)],*b.bounds('2026-09-28','2026-09-28'),overrides={'2026-09-28':state['calendar']})
    actual=result['agents'][name];forward=expected['agents'][name]
    assert actual['closed_trades']==1 and len(forward['trades'])==1
    assert actual['net_pnl']==forward['trades'][0]['pnl']
    assert actual['cash']==pytest.approx(round(forward['cash'],2))
    assert actual['total_charges']>0


def test_open_position_at_end_is_incomplete_not_forced_liquidation():
    state=ready();qs=chain();legs,_=r.choose('iron_condor',ctx(),qs,25000,state['candles'])
    fills=r.execute(legs,{q['instrument_key']:q for q in qs},NOW,True);terms=r.terms(fills,ctx())
    state['agents']['iron_condor'].update(cash=s.cashflow(fills),position=dict(**terms,legs=fills,equity_before=0.,entry_at=NOW.isoformat(),max_seconds=7200))
    with patch.object(r,'fresh',return_value=state):
        result,_=b.replay_frames([(NOW,qs)],*b.bounds('2026-09-28','2026-09-28'),overrides={'2026-09-28':dict(date='2026-09-28',windows=[])})
    assert result['agents']['iron_condor']['evidence_status']=='unresolved'
    assert result['agents']['iron_condor']['closed_trades']==0


def test_job_is_async_deduplicated_and_completed_result_is_saved(store):
    with patch.object(b.threading.Thread,'start'):
        reply=b.submit('2026-09-28','2026-09-28')
        assert reply['status']=='queued'
        with pytest.raises(ValueError):b.submit('2026-09-28','2026-09-28')
    with patch.object(b.os,'nice'):b.worker(reply['job_id'])
    data=p.dashboard()
    assert data['replay_job']['status']=='completed'
    assert len(data['last_backtest']['agents'])==11
    assert data['live']['last_at'] is None


def test_expired_job_does_not_disable_run_forever(store):
    with p.database() as db:
        db.execute("INSERT INTO replay_jobs(created_at,updated_at,status,request,progress) VALUES('2000-01-01T00:00:00+00:00','2000-01-01T00:00:00+00:00','running','{}','{}')")
    assert p.dashboard()['replay_job']['status']=='failed'


def test_new_calendar_is_audited_without_resetting_balance(store):
    p.control('start')
    today=datetime.now(p.IST).date().isoformat()
    p.set_research_calendar(dict(date=today,windows=[]))
    with p.database() as db:
        saved=json.loads(db.execute('SELECT payload FROM paper_calendar_reviews').fetchone()[0])
    assert saved['date']==today and saved['reviewed_at']
    assert p.dashboard()['live']['agents']['opening_range']['cash']==100000


def test_complete_seconds_build_real_bars_and_warmup_cannot_trade():
    start=NOW.replace(hour=9,minute=15)
    frames=((start+timedelta(seconds=i),chain(start+timedelta(seconds=i))) for i in range(3602))
    first=start+timedelta(minutes=60)
    result,c=b.replay_frames(frames,first,first+timedelta(hours=1))
    assert c['warmup_frames']==3600 and c['frames']==2
    assert c['max_spread_bars']==12
    assert all(not a['trades'] for a in result['agents'].values())
    assert result['agents']['trend_pullback']['evidence_status']=='observed'
    assert result['agents']['regime_debit']['evidence_status']=='insufficient_data'


def test_duplicate_historical_reviews_are_rejected():
    item=dict(date='2026-09-28',windows=[],reviewed=True)
    with pytest.raises(ValueError):b.request_config('2026-09-28','2026-09-28',[item,item])


def test_raw_frames_are_not_changed_or_forward_session_created(store):
    now=NOW.astimezone(timezone.utc);blob=zlib.compress(json.dumps(chain(now)).encode())
    with p.database() as db:db.execute('INSERT INTO second_frames VALUES(?,?)',(now.isoformat(),blob))
    b.run(b.request_config('2026-09-28','2026-09-28'))
    with p.database() as db:
        assert db.execute('SELECT payload FROM second_frames').fetchone()[0]==blob
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0
