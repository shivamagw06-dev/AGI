from datetime import datetime,timedelta
from copy import deepcopy
from unittest.mock import patch
import pytest
from options_lab import minute_backtest as m, minute_history as h, paper_agents as p
NOW=datetime(2026,8,10,9,15,tzinfo=p.IST)

def fixture_frames(count=375):
    rows=[]
    for i in range(count):
        t=NOW+timedelta(minutes=i);spot=[t.isoformat(),25000,25020,24980,25000,0,0];contracts={}
        for strike,price in [(25000,30),(25050,20)]:
            meta=dict(instrument_key=str(strike),option_type='CE',strike=strike,expiry='2026-08-13',lot_size=25,underlying_key=h.h.NIFTY_KEY)
            contracts[str(strike)]=(meta,[t.isoformat(),price,price+1,price-1,price,10000,100000])
        rows.append((t,dict(spot=spot,contracts=contracts)))
    return rows

def signal(rows,signal,name,spot):
    if name!='trend_pullback':return None
    return [dict(x,side='BUY' if x['strike']==25000 else 'SELL') for x in rows]

def run(frames,**kwargs):
    with patch.object(m.s,'setup',return_value={'side':'CE','rv':10}),patch.object(m.s,'select_legs',side_effect=signal):
        return m.simulate(frames,'2026-08-10','2026-08-10',{},**kwargs)

def test_fills_only_follow_completed_bar_and_use_open_not_close():
    frames=fixture_frames();frames[60][1]['contracts']['25000'][1][4]=80
    result=run(frames)['strategies']['trend_pullback'];trade=result['trades'][0]
    assert trade['entry_at']=='2026-08-10T10:15:00+05:30'
    assert trade['legs'][0]['price']==pytest.approx(30*1.005)
    assert trade['exit_at']=='2026-08-10T10:16:00+05:30'
    assert trade['reason']=='Target at minute close' and trade['fees']>0

def test_future_candles_do_not_change_earlier_trades():
    a=fixture_frames();a[60][1]['contracts']['25000'][1][4]=80;b=deepcopy(a)
    for _,frame in b[100:]:frame['spot'][4]=23000
    assert run(a)['strategies']['trend_pullback']['trades'][0]==run(b)['strategies']['trend_pullback']['trades'][0]

def test_missing_exit_preserves_unresolved_and_hides_total_profit():
    frames=fixture_frames();del frames[61][1]['contracts']['25000']
    result=run(frames)['strategies']['trend_pullback']
    assert result['status']=='unresolved' and result['net_pnl'] is None and result['unresolved_position']

def test_missing_minute_does_not_fill_from_later_prices():
    frames=fixture_frames();del frames[61];result=run(frames)
    assert result['missing_minute_gaps']==1
    assert result['strategies']['trend_pullback']['status']=='unresolved'

def test_missing_review_and_short_history_do_not_become_zero_pnl():
    result=run(fixture_frames());assert set(result['strategies'])==set(m.NAMES)
    for key in m.r.NAMES:
        assert result['strategies'][key]['net_pnl'] is None
        assert result['strategies'][key]['status']=='not_testable'

def test_higher_execution_costs_worsen_same_flat_trade():
    base=run(fixture_frames())['strategies']['trend_pullback'];stress=run(fixture_frames(),multiplier=2)['strategies']['trend_pullback']
    assert base['closed_trades']==stress['closed_trades']==2
    assert stress['net_pnl']<base['net_pnl']<0

def test_no_invented_bid_ask_or_depth_in_history():
    now,frame=fixture_frames(1)[0];rows=m.signal_rows(frame,now+timedelta(minutes=1),{})
    assert rows and all('bid' not in x and 'ask_size' not in x for x in rows)

def test_request_accepts_months_but_rejects_future_and_unconfirmed_reviews():
    assert m.config('2026-06-01','2026-08-31')['start']=='2026-06-01'
    for a,b,cal in [('2026-01-01','2026-09-01',[]),('2026-09-29','2099-01-01',[]),('2026-08-10','2026-08-10',[dict(date='2026-08-10',reviewed=False,windows=[])])]:
        with pytest.raises(ValueError):m.config(a,b,cal)

def test_candle_validation_rejects_bad_order_nan_and_duplicates():
    good=fixture_frames(1)[0][1]['spot'];assert h.clean([good,good])==[good]
    bad=deepcopy(good);bad[2]=1
    with pytest.raises(ValueError):h.clean([bad])
    bad=deepcopy(good);bad[4]=float('nan')
    with pytest.raises(ValueError):h.clean([bad])
    bad=deepcopy(good);bad[4]+=1
    with pytest.raises(ValueError):h.clean([good,bad])

def test_caches_real_downloads_and_separates_live_tables(tmp_path):
    with patch.object(p,'paths',return_value=(tmp_path/'source',tmp_path/'paper')):
        rows=[fixture_frames(1)[0][1]['spot']]
        with patch.object(h.h,'_request',return_value={'candles':rows}) as request,patch.object(h.time,'sleep'):
            h.download(h.h.NIFTY_KEY,'2026-08-10','2026-08-10','secret',spot=True)
            h.download(h.h.NIFTY_KEY,'2026-08-10','2026-08-10','secret',spot=True)
            assert request.call_count==1
        assert len(h.spot_rows('2026-08-10','2026-08-10'))==1
        with p.database() as db:
            assert db.execute('SELECT count(*) FROM second_frames').fetchone()[0]==0
            assert db.execute('SELECT count(*) FROM sessions').fetchone()[0]==0
