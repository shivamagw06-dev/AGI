"""Bounded, isolated replay of recorded evidence; never synthesises quote history."""
from __future__ import annotations
import json
import os
import sqlite3
import subprocess
import sys
import threading
import zlib
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import paper_agents as p, spread_agents as s, regime_agents as r

VERSION = 'all-strategies-replay-v1'
MAX_SECONDS = 900
MAX_FRAMES = 350000  # More than fourteen regular sessions; evidence retention is fourteen days.
IV_NAMES = {'regime_credit', 'iron_condor', 'long_straddle', 'long_strangle', 'iron_fly'}


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS replay_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL, status TEXT NOT NULL, request TEXT NOT NULL,
        progress TEXT NOT NULL, error TEXT)''')
    db.execute('''CREATE TABLE IF NOT EXISTS paper_calendar_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, reviewed_at TEXT NOT NULL, payload TEXT NOT NULL)''')


def request_config(start, end, calendars=None):
    try:
        first = datetime.strptime(start, '%Y-%m-%d').date()
        last = datetime.strptime(end, '%Y-%m-%d').date()
        if first > last or (last-first).days > 60 or last > datetime.now(p.IST).date():
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Choose a past range of at most 60 days')
    if calendars is None:
        calendars = []
    if not isinstance(calendars, list) or len(calendars) > 61:
        raise ValueError('Supply at most 61 dated historical event reviews')
    clean = {}
    for item in calendars:
        try:
            day = item['date']
            if datetime.strptime(day,'%Y-%m-%d').date().isoformat()!=day:raise ValueError()
            if not start <= day <= end or day in clean or item.get('reviewed') is not True:
                raise ValueError()
            windows = item['windows']
            if not isinstance(windows, list) or len(windows) > 20:
                raise ValueError()
            normalized = []
            for window in windows:
                a, b = p.timestamp(window['start']), p.timestamp(window['end'])
                if a >= b or any(t.astimezone(p.IST).date().isoformat() != day for t in (a, b)):
                    raise ValueError()
                normalized.append(dict(start=a.isoformat(), end=b.isoformat()))
            clean[day] = dict(date=day, windows=normalized)
        except (KeyError, TypeError, ValueError):
            raise ValueError('Each historical review needs a unique date in the test range, reviewed=true and valid timezone-aware windows')
    return dict(start=start, end=end, calendars=clean)


def bounds(start, end):
    first = datetime.fromisoformat(start).replace(tzinfo=p.IST).astimezone(timezone.utc)
    last = (datetime.fromisoformat(end).replace(tzinfo=p.IST)+timedelta(days=1)).astimezone(timezone.utc)
    return first, last


def progress(job, **values):
    if job is None:
        return
    with closing(p.database()) as db, db:
        db.execute('UPDATE replay_jobs SET updated_at=?, progress=? WHERE id=? AND status IN (\'queued\',\'running\')',
                   (datetime.now(timezone.utc).isoformat(), json.dumps(values), job))


def latest_job(db):
    schema(db)
    row = db.execute('SELECT * FROM replay_jobs ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        return None
    if row['status'] in ('queued','running') and (datetime.now(timezone.utc)-p.timestamp(row['created_at'])).total_seconds()>MAX_SECONDS+60:
        db.execute("UPDATE replay_jobs SET status='failed',error='Replay interrupted or exceeded its limit; run again.' WHERE id=?",(row['id'],))
        row=db.execute('SELECT * FROM replay_jobs WHERE id=?',(row['id'],)).fetchone()
    result = dict(row)
    result['request'] = json.loads(result['request'])
    result['progress'] = json.loads(result['progress'])
    return result


def submit(start, end, calendars=None):
    config = request_config(start, end, calendars)
    now = datetime.now(timezone.utc)
    with closing(p.database()) as db, db:
        schema(db)
        db.execute('BEGIN IMMEDIATE')
        # A killed deployment cannot leave a permanent running badge.
        db.execute("UPDATE replay_jobs SET status='failed',error='Replay interrupted or exceeded its 15-minute limit; run again.' WHERE status IN ('queued','running') AND created_at < ?",
                   ((now-timedelta(seconds=MAX_SECONDS+60)).isoformat(),))
        running = db.execute("SELECT id FROM replay_jobs WHERE status IN ('queued','running') LIMIT 1").fetchone()
        if running:
            raise ValueError('A replay is already running. Wait for its result before starting another.')
        job = db.execute('INSERT INTO replay_jobs(created_at,updated_at,status,request,progress) VALUES(?,?,?,?,?)',
                         (now.isoformat(), now.isoformat(), 'queued', json.dumps(config), '{}')).lastrowid
    threading.Thread(target=launch, args=(job,), daemon=True).start()
    return dict(ok=True, job_id=job, status='queued')


def fail(job, message):
    with closing(p.database()) as db, db:
        db.execute("UPDATE replay_jobs SET status='failed',error=?,updated_at=? WHERE id=? AND status IN ('queued','running')",
                   (message, datetime.now(timezone.utc).isoformat(), job))


def launch(job):
    # Separate lightweight interpreter: large replays do not monopolise the API's GIL.
    try:
        completed = subprocess.run([sys.executable, '-m', 'options_lab.replay', str(job)],
                                   cwd=str(Path(__file__).resolve().parent.parent),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=MAX_SECONDS)
        if completed.returncode:
            fail(job, 'Replay worker failed; forward accounts were not changed.')
    except subprocess.TimeoutExpired:
        fail(job, 'Replay exceeded 15 minutes. Select a shorter date range.')
    except OSError:
        fail(job, 'Replay worker could not start; forward accounts were not changed.')


def unavailable(agent, reason):
    agent.update(evidence_status='insufficient_data', status=reason)
    for key in ('cash','equity','net_pnl','closed_trades','win_rate','max_drawdown',
                'average_pnl','profit_factor','total_charges','available_after_reserve','capital_reserved'):
        agent[key] = None


def replay_frames(frames, first, last, reviews=(), overrides=None, iv_seed=(), job=None):
    """Use the exact forward transitions. Prior frames warm indicators without orders."""
    state = p.fresh_state()
    state['spreads'] = s.fresh()
    state['research'] = r.fresh()
    research = state['research']
    research['iv_history'] = [x for x in iv_seed if x['day'] < first.astimezone(p.IST).date().isoformat()
                              and p.timestamp(x['at']) < first
                              and p.timestamp(x.get('available_at',x['at'])) <= first][-60:]
    reviews = sorted(reviews, key=lambda x: p.timestamp(x['reviewed_at']))
    cursor = 0
    known = {}
    overrides = overrides or {}
    coverage = dict(frames=0, warmup_frames=0, quote_rows=0, gaps_over_5s=0, days=[],
                    complete_bars=0, max_research_bars=0, max_spread_bars=0, max_prior_iv_days=0,
                    reviewed_days=[], post_event_frames=0, futures_frames=0, valid_option_frames=0,
                    iv_frames=0, delta_frames=0, eligible_frames={name:0 for name in (*s.NAMES,*r.NAMES)})
    previous = None
    last_bar = None
    seeded = False
    for index, (now, rows) in enumerate(frames):
        if now >= last:
            break
        while cursor < len(reviews) and p.timestamp(reviews[cursor]['reviewed_at']) <= now:
            review = reviews[cursor]
            known[review['date']] = review
            cursor += 1
        day = now.astimezone(p.IST).date().isoformat()
        if not seeded:
            research['iv_history'] = sorted({x['day']:x for x in research['iv_history'] if x['day']<day and p.timestamp(x['at'])<now}.values(),key=lambda x:x['day'])[-60:]
            seeded = True
        research['calendar'] = overrides.get(day) or known.get(day) or dict(date=None, windows=[])
        selected = now >= first
        r.advance(research, rows, now, selected)
        options = [q for q in rows if q.get('option_type') in ('CE','PE')]
        s.advance(state['spreads'], options, now, selected)
        if selected:
            coverage['frames'] += 1
            coverage['quote_rows'] += len(rows)
            if day not in coverage['days']:
                coverage['days'].append(day)
            coverage['gaps_over_5s'] += int(previous is not None and (now-previous).total_seconds()>5
                                           and previous.astimezone(p.IST).date()==now.astimezone(p.IST).date())
            coverage['max_research_bars'] = max(coverage['max_research_bars'],len(research['candles']))
            coverage['max_spread_bars'] = max(coverage['max_spread_bars'],len(state['spreads']['candles']))
            coverage['max_prior_iv_days'] = max(coverage['max_prior_iv_days'],len(research['iv_history']))
            if research['last_bar'] is not None and research['last_bar'] != last_bar:
                coverage['complete_bars'] += 1
            ctx = research['regime']
            reviewed = r.event_state(research['calendar'],now) not in ('UNREVIEWED','BLACKOUT')
            if reviewed and day not in coverage['reviewed_days']:
                coverage['reviewed_days'].append(day)
            coverage['post_event_frames'] += int(ctx.get('event')=='POST_EVENT')
            valid = [q for q in rows if r.eligible(q,now)]
            option_valid = [q for q in valid if q['option_type'] in ('CE','PE')]
            has_iv = any(p.number(q.get('iv')) for q in option_valid)
            has_delta = any(p.number(q.get('greeks',{}).get('delta')) is not None for q in option_valid)
            has_future = any(q['option_type']=='FUT' and p.number(q.get('vwap')) for q in valid)
            coverage['valid_option_frames'] += int(bool(option_valid))
            coverage['iv_frames'] += int(has_iv)
            coverage['delta_frames'] += int(has_delta)
            coverage['futures_frames'] += int(has_future)
            for name in s.NAMES:
                ready = 615 <= now.astimezone(p.IST).hour*60+now.astimezone(p.IST).minute < 855 and len(state['spreads']['candles'])>=12 and bool(option_valid)
                coverage['eligible_frames'][name] += int(ready and (name!='volatility_credit' or has_iv))
            for name in r.NAMES:
                ready = 600 <= now.astimezone(p.IST).hour*60+now.astimezone(p.IST).minute < 855 and reviewed and len(research['candles'])>=50 and research['session_bars']>=3
                ready = ready and (has_future if name=='futures_trend' else bool(option_valid))
                if name in IV_NAMES:
                    ready = ready and ctx.get('iv_percentile') is not None
                if name in ('regime_credit','iron_condor','long_strangle'):
                    ready = ready and has_delta
                if name=='iron_fly':
                    ready = ready and ctx.get('event')=='POST_EVENT'
                coverage['eligible_frames'][name] += int(bool(ready))
        else:
            coverage['warmup_frames'] += 1
        previous = now
        last_bar = research['last_bar']
        if index % 1000 == 0:
            progress(job, phase='Replaying one-second evidence', processed_frames=index+1, at=now.isoformat())
    result = p.summary(state)
    for name in (*s.NAMES,*r.NAMES):
        a = result['agents'][name]
        a['replay_interval_seconds'] = 1
        a['evidence_status'] = 'observed'
        if a['blocked'] or a['position']:
            a['evidence_status'] = 'unresolved'
            a['status'] = 'Incomplete result: open or unresolved position at end of evidence; last mark retained'
        elif not a['closed_trades'] and not coverage['eligible_frames'][name]:
            reasons = []
            if not coverage['frames']:
                reasons.append('No recorded one-second frames in this range')
            elif name in s.NAMES:
                if coverage['max_spread_bars']<12:reasons.append('Needs 12 complete five-minute bars')
                if not coverage['valid_option_frames']:reasons.append('No usable option bid/ask depth')
                if name=='volatility_credit' and not coverage['iv_frames']:reasons.append('Missing option IV')
            else:
                if coverage['max_research_bars']<50:reasons.append('Needs 50 complete five-minute bars and three fresh session bars')
                if not coverage['reviewed_days']:reasons.append('Missing dated event-calendar reviews')
                if name in IV_NAMES and coverage['max_prior_iv_days']<20:reasons.append('Needs 20 prior daily IV observations')
                if name=='futures_trend' and not coverage['futures_frames']:reasons.append('Missing futures quotes / average traded price')
                if name=='iron_fly' and not coverage['post_event_frames']:reasons.append('No reviewed post-event window')
                if name in ('regime_credit','iron_condor','long_strangle') and not coverage['delta_frames']:reasons.append('Missing recorded option delta')
            unavailable(a, '; '.join(reasons) or 'Required inputs never overlap in a usable observation')
        elif not a['closed_trades']:
            a['status'] = 'No completed trades under these rules and risk limits in usable observations'
    return result, coverage


def run(config, job=None):
    first,last = bounds(config['start'],config['end'])
    with closing(p.database()) as db:
        schema(db)
        # This fixed cutoff makes a run reproducible while the collector keeps appending.
        cutoff = db.execute('SELECT MAX(at) FROM second_frames WHERE at < ?', (last.isoformat(),)).fetchone()[0]
        warm_start = (first-timedelta(days=14)).isoformat()
        count = db.execute('SELECT COUNT(*) FROM second_frames WHERE at>=? AND at<=?', (warm_start,cutoff or '')).fetchone()[0]
        if count > MAX_FRAMES:
            raise ValueError('Too many recorded seconds. Choose a shorter range.')
        reviews = [json.loads(x[0]) for x in db.execute('SELECT payload FROM paper_calendar_reviews WHERE reviewed_at < ? ORDER BY reviewed_at',(last.isoformat(),))]
        live = db.execute('SELECT state FROM sessions WHERE id=1').fetchone()
        research = json.loads(live[0]).get('research',{}) if live else {}
        seed = research.get('iv_history',[]) + ([research['iv_today']] if research.get('iv_today') else [])
    # Keyset pages release read locks between batches; no transaction is held for the run.
    def frames():
        after = ''
        while cutoff:
            with closing(p.database()) as db:
                page = db.execute('SELECT at,payload FROM second_frames WHERE at>=? AND at>? AND at<=? ORDER BY at LIMIT 250',
                                  (warm_start,after,cutoff)).fetchall()
            if not page:return
            for at,payload in page:
                from .iv_history import normalize_stream_rows
                yield p.timestamp(at),normalize_stream_rows(json.loads(zlib.decompress(payload)))
            after = page[-1][0]
    progress(job, phase='Reading recorded evidence', total_frames=count)
    result,coverage = replay_frames(frames(),first,last,reviews,config['calendars'],seed,job)
    # Preserve the legacy fifteen-minute experiment, clearly labelled separately.
    rows = p.read_quotes(config['start'],config['end'])
    legacy = p.fresh_state()
    batches = sampled = 0
    from itertools import groupby
    for _,group in groupby(rows,key=lambda x:x['captured_at']):
        before = legacy['last_at']
        p.step(legacy,list(group))
        batches += 1
        sampled += int(legacy['last_at'] != before)
    original = p.summary(legacy)
    for name,a in original['agents'].items():
        a.update(replay_interval_seconds=900,evidence_status='observed')
        if not rows:unavailable(a,'No stored fifteen-minute option snapshots in this range')
        elif a['blocked'] or a['position']:
            a.update(evidence_status='unresolved',status='Incomplete result: open or unresolved position at end of evidence; last mark retained')
        result['agents'][name] = a
    coverage.update(legacy_days=len({x['captured_at'][:10] for x in rows}),legacy_quote_rows=len(rows),
                    legacy_observations=sampled,frame_cutoff=cutoff,
                    calendar_mode='retrospective_admin_inputs' if config['calendars'] else 'recorded_as_of_reviews',
                    retrospective_dates=sorted(config['calendars']),iv_seed_days=len([x for x in seed if p.timestamp(x['at'])<first and p.timestamp(x.get('available_at',x['at']))<=first]))
    result.update(ok=True,version=VERSION,mode='historical_replay',start=config['start'],end=config['end'],
                  status='research_only' if rows or coverage['frames'] else 'no_data',
                  days=coverage['legacy_days'],quote_rows=len(rows),observations=batches,sampled_observations=sampled,
                  coverage=coverage,completed_at=datetime.now(timezone.utc).isoformat(),job_id=job,
                  assumptions=['Original two: 15-minute snapshots and legacy illustrative costs.',
                    'Other nine: exact forward rules on recorded one-second frames; no interpolation or invented depth.',
                    'Warm-up uses prior recorded frames without entries. IV seed uses only prior dated observations.',
                    'Historical calendar overrides are retrospective research assumptions, not point-in-time evidence.',
                    'Current dated fee model is applied throughout; not a historical tariff reconstruction.',
                    'Open/unresolved positions are not closed at invented prices. Results are exploratory, not validation.'])
    return result


def worker(job):
    try:
        os.nice(10)
    except (AttributeError,OSError):
        pass
    with closing(p.database()) as db,db:
        schema(db)
        row = db.execute("SELECT request FROM replay_jobs WHERE id=? AND status='queued'",(job,)).fetchone()
        if not row:return
        config = json.loads(row[0])
        db.execute("UPDATE replay_jobs SET status='running',updated_at=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),job))
    try:
        result = run(config,job)
        now = datetime.now(timezone.utc).isoformat()
        with closing(p.database()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT status FROM replay_jobs WHERE id=?',(job,)).fetchone()[0] != 'running':return
            db.execute('INSERT INTO backtests(created_at,result) VALUES(?,?)',(now,json.dumps(result)))
            db.execute("UPDATE replay_jobs SET status='completed',updated_at=?,progress=? WHERE id=?",(now,json.dumps(dict(phase='Complete')),job))
    except ValueError as exc:
        fail(job,str(exc))
    except Exception:
        fail(job,'Recorded evidence could not be replayed. Check data integrity; forward accounts were not changed.')


if __name__ == '__main__':
    worker(int(sys.argv[1]))
