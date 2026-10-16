import copy
import json
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch
import pytest
from options_lab import daily_research as d


def bars(n=450):
    return [dict(date=(date(2020,1,1)+timedelta(days=i)).isoformat(),open=100+i,high=102+i,low=99+i,close=101+i) for i in range(n)]


def test_official_csv_formats_and_non_nifty_filter():
    rows=d.parse_csv('Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value\nNIFTY BANK,28-09-2026,10,12,9,11\nNIFTY 50,28-09-2026,23064.9,23080.25,22762.2,22780.25\n')
    assert len(rows)==1 and rows[0]['close']==22780.25
    assert d.parse_csv('Date,Open,High,Low,Close\n28 Sep 2026,23064.9,23080.25,22762.2,22780.25\n')==rows


@pytest.mark.parametrize('field,value',[('close','nan'),('open',0),('high',10),('date','2099-01-01')])
def test_bad_prices_and_future_dates_rejected(field,value):
    r=bars(1);r[0][field]=value
    with pytest.raises(ValueError):d.validate(r)


def test_duplicate_conflict_does_not_partially_import():
    db=sqlite3.connect(':memory:');d.schema(db)
    with db:d.store(bars(2),'test',db)
    new=bars(3);new[0]['close']=100
    with pytest.raises(ValueError):
        with db:d.store(new,'bad',db)
    assert db.execute('select count(*) from nifty_daily_bars').fetchone()[0]==2
    assert db.execute('select count(*) from nifty_daily_imports').fetchone()[0]==1
    assert len(d.validate(bars(2)+bars(2)))==2


def test_incremental_indicators_match_full_history_and_strict_ema_length():
    rows=bars();f=d.features(rows)
    assert d.ema([1]*199,200) is None
    assert d.ema([1]*200,200)==1
    assert d.ema([1]*200+[202],200)==3
    for i in (199,399,449):
        closes=[r['close'] for r in rows[:i+1]]
        assert f[i]['ema200']==pytest.approx(d.ema(closes,200))
        assert f[i]['ema50']==pytest.approx(d.ema(closes,50))
        assert f[i]['rsi2']==pytest.approx(d.rsi(closes))
    assert d.desired('daily_trend',rows[:399],0,0)==0
    assert d.desired('daily_trend',rows[:400],0,0)==1


def test_future_changes_cannot_change_prior_decisions_or_returns():
    rows=bars();changed=copy.deepcopy(rows)
    for r in changed[425:]:
        for key in ('open','high','low','close'):r[key]*=0.7
    for name in d.NAMES:
        a=d.study(rows,name);b=d.study(changed,name)
        assert a['daily'][:24]==b['daily'][:24]
        assert a['daily'][24]['position']==b['daily'][24]['position']


def test_next_open_reference_and_round_trip_costs():
    with patch.object(d,'direction',side_effect=[1,-1,0,0,0]):out=d.study(bars(404),'daily_trend')
    expected=(1-.0005)*(501/500)*(1-.0005)**2*(1-(502/501-1))*(1-.0005)
    assert out['reference_return_pct']==round((expected-1)*100,3)
    assert out['closed_trades']==2 and out['turnover_units']==4
    assert out['observations']==3
    assert out['trades'][0]['entry_date']==bars(404)[400]['date']
    assert out['trades'][0]['exit_date']==bars(404)[401]['date']
    assert out['daily'][0]['signal_date']==bars(404)[399]['date']


def test_final_open_rebalance_cost_and_latest_signal_state():
    with patch.object(d,'direction',side_effect=[1,0,0]) as signal:out=d.study(bars(402),'daily_pullback')
    assert out['closed_trades']==1 and out['open_exposure']==0
    assert out['reference_return_pct']==round(((1-.0005)**2*(501/500)-1)*100,3)
    assert signal.call_args.args[2:]==(0,0)


def test_rule_boundaries_and_pullback_time_exit():
    f=dict(ready=True,close=110,ema50=106,ema200=100,momentum=5,rsi2=9,upper=109,lower=95,exit_upper=108,exit_lower=98)
    for name in d.NAMES:assert d.direction(name,f,0,0)==1
    assert d.direction('daily_pullback',f,1,5)==0
    assert d.direction('daily_pullback',{**f,'rsi2':61},1,1)==0
    assert d.direction('daily_pullback',{**f,'close':99},1,1)==0
    assert d.direction('daily_breakout',{**f,'close':97},1,1)==0
    assert d.direction('daily_breakout',{**f,'close':94},1,1)==-1
    with pytest.raises(ValueError):d.direction('wrong',f,0,0)


def test_gaps_restart_warmup_and_withhold_returns():
    rows=bars(450)
    for r in rows[420:]:r['date']=(date.fromisoformat(r['date'])+timedelta(days=20)).isoformat()
    out=d.report(rows)
    assert out['usable_rows']==30 and out['ema200'] is None
    assert out['benchmark_return_pct'] is None
    assert all(x['reference_return_pct'] is None for x in out['strategies'].values())


def test_bundled_official_history_provenance():
    seed=json.loads(d.SEED.read_text());rows=d.validate(seed['rows'])
    import hashlib
    assert hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()==seed['sha256']
    assert seed['source']==d.SOURCE
    assert len(rows)==743 and rows[-1]['date']=='2026-09-28'
    out=d.report(rows)
    assert out['missing_calendar_gaps']==[] and len(out['strategies'])==4
    for s in out['strategies'].values():
        assert s['observations']==342 and s['closed_trades']>0
        assert s['double_cost_return_pct']<=s['reference_return_pct']
        assert s['live_trading_approved'] is False


def test_seed_merges_with_recent_import_instead_of_being_skipped():
    db=sqlite3.connect(':memory:');seed=json.loads(d.SEED.read_text())
    with db:d.store([seed['rows'][-1]],'single daily update',db)
    assert len(d.load(db))==743 and len(d.load(db))==743
    assert db.execute('select count(*) from nifty_daily_imports').fetchone()[0]==2


@pytest.mark.asyncio
async def test_admin_engine_routes_enforce_token_and_offload(monkeypatch):
    # Compile the actual route declarations without constructing unrelated service singletons.
    import ast
    import threading
    from pathlib import Path
    from types import SimpleNamespace
    from typing import Any
    import httpx
    from fastapi import APIRouter, FastAPI, Depends, Header, HTTPException, Body
    from starlette.concurrency import run_in_threadpool
    tree=ast.parse((Path(__file__).resolve().parents[2]/'app/api/routes.py').read_text())
    names={'require_token','nifty_daily_research','nifty_daily_import','nifty_daily_refresh'}
    selected=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names],type_ignores=[])
    namespace=dict(APIRouter=APIRouter,Depends=Depends,Header=Header,HTTPException=HTTPException,Body=Body,Any=Any,
        Settings=SimpleNamespace,get_settings=lambda:SimpleNamespace(intelligence_engine_token='test-token'),router=APIRouter(),run_in_threadpool=run_in_threadpool)
    exec(compile(selected,'app/api/routes.py','exec'),namespace)
    app=FastAPI();app.include_router(namespace['router'])
    main=threading.get_ident();calls=[]
    def dashboard():calls.append(threading.get_ident());return {'ok':True}
    monkeypatch.setattr(d,'dashboard',dashboard)
    monkeypatch.setattr(d,'refresh',lambda:(_ for _ in ()).throw(TimeoutError('private diagnostic')))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        for path,method in [('', 'GET'),('/import','POST'),('/refresh','POST')]:
            assert (await client.request(method,'/options-lab/daily-research'+path)).status_code==401
        headers={'Authorization':'Bearer test-token'}
        assert (await client.get('/options-lab/daily-research',headers=headers)).json()=={'ok':True}
        assert calls and calls[0]!=main
        bad=await client.post('/options-lab/daily-research/import',headers=headers,json={'csv':'bad'})
        assert bad.status_code==422
        missing=await client.post('/options-lab/daily-research/refresh',headers=headers)
        assert missing.status_code==503 and 'private diagnostic' not in missing.text


def test_daily_returns_reconcile_including_terminal_rebalance():
    import math
    with patch.object(d,'direction',side_effect=[1,-1,0]):out=d.study(bars(402),'daily_trend')
    compounded=math.prod(1+x['return_pct']/100 for x in out['daily'])
    assert round((compounded-1)*100,3)==out['reference_return_pct']
    assert out['daily'][-1]['ending_rebalance_cost_pct']<0
