"""Replay-only decision attribution. Does not change signals or risk limits."""
from collections import Counter
from datetime import datetime, timedelta
from . import paper_agents as p


def iv_schedule(observations):
    scheduled = []
    for item in observations:
        try:
            next_day = datetime.fromisoformat(item['day']).replace(tzinfo=p.IST) + timedelta(days=1)
            at = p.timestamp(item['at'])
            available = p.timestamp(item.get('available_at', item['at']))
            if not p.number(item.get('iv')) or not 0 < float(item['iv']) < 200:
                continue
            if item.get('unit', 'percent') != 'percent':
                continue
            scheduled.append((max(next_day, available, at + timedelta(microseconds=1)), item))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(scheduled, key=lambda x: x[0])


def signal_direction(agent):
    pending = agent.get('pending') or {}
    regime = pending.get('context', {}).get('name')
    if regime in ('TREND_DOWN', 'TREND_UP'):
        return 'bearish' if regime == 'TREND_DOWN' else 'bullish'
    legs = pending.get('legs') or []
    if legs and len({l.get('option_type') for l in legs}) == 1:
        kind = legs[0]['option_type']
        short = next((l for l in legs if l.get('side') == 'SELL'), None)
        long = next((l for l in legs if l.get('side') == 'BUY'), None)
        if short and long:
            bullish = short['strike'] > long['strike']
            return 'bullish' if bullish else 'bearish'
    side = pending.get('side') or pending.get('option_type')
    return {'CE': 'bullish', 'PE': 'bearish'}.get(side, 'non-directional')


class ReplayEvidence:
    def __init__(self):
        self.records = {}

    def observe(self, now, agents, regime=None):
        at = now.isoformat()
        day = now.astimezone(p.IST).date().isoformat()
        for name, agent in agents.items():
            r = self.records.setdefault(name, dict(days=set(), reasons=Counter(), events=Counter(),
                regimes=Counter(), directions=Counter(), first_signal=None, first_bearish_signal=None,
                first_entry=None, decisions=[], last_at=None))
            if r['last_at'] and p.timestamp(r['last_at']) >= now:
                continue
            r['last_at'] = at
            r['days'].add(day)
            r['reasons'][agent.get('status') or 'No status'] += 1
            if regime:
                r['regimes'][regime.get('name', 'UNKNOWN')] += 1
            # Forward engines timestamp events with the observation time. This
            # captures events before the rolling UI journal truncates them.
            for event in agent.get('events', []):
                if p.timestamp(event['at']) != now:
                    continue
                kind = event['kind']
                r['events'][kind] += 1
                detail = dict(event)
                if kind == 'signal':
                    direction = signal_direction(agent)
                    detail['direction'] = direction
                    context = (agent.get('pending') or {}).get('context') or {}
                    detail['context'] = {k:context[k] for k in ('name','ema20','ema50','adx','iv_percentile','bars','session_bars') if k in context}
                    r['directions'][direction] += 1
                    r['first_signal'] = r['first_signal'] or detail
                    if direction == 'bearish':r['first_bearish_signal'] = r['first_bearish_signal'] or detail
                if kind == 'entry':r['first_entry'] = r['first_entry'] or detail
                r['decisions'].append(detail)
                r['decisions'] = r['decisions'][-100:]

    def finish(self, agents):
        output = {}
        for name, agent in agents.items():
            r = self.records.get(name, {})
            days = sorted(r.get('days', []))
            pnl = {d:dict(date=d,closed_trades=0,net_pnl=0.,fees=0.) for d in days}
            for trade in agent.get('trades', []):
                day = p.timestamp(trade['exit_at']).astimezone(p.IST).date().isoformat()
                if day not in pnl:continue
                pnl[day]['closed_trades'] += 1
                pnl[day]['net_pnl'] += trade['pnl']
                pnl[day]['fees'] += trade.get('entry_cost', 0) + trade.get('exit_cost', 0)
            output[name] = dict(observed_days=days,
                status_observations=dict(r.get('reasons', {})),
                event_counts=dict(r.get('events', {})), regime_observations=dict(r.get('regimes', {})),
                signal_directions=dict(r.get('directions', {})), first_signal=r.get('first_signal'),
                first_bearish_signal=r.get('first_bearish_signal'), first_entry=r.get('first_entry'),
                recent_decisions=r.get('decisions', []), daily_results=list(pnl.values()))
        return output


def validation_report(agents, audits):
    report = {}
    for name, a in agents.items():
        audit = audits.get(name, {})
        daily = audit.get('daily_results', [])
        days = len(daily)
        n = a.get('closed_trades')
        net = a.get('net_pnl')
        fees = a.get('total_charges')
        issues = []
        complete = a.get('evidence_status') == 'observed'
        if not complete:issues.append('Missing evidence or unresolved position')
        if days < 20:issues.append(f'Only {days}/20 observed sessions')
        if n is None or n < 30:issues.append(f'Only {n if n is not None else 0}/30 completed trades')
        stressed = round(net-fees, 2) if complete and n and net is not None and fees is not None else None
        if complete and n and net <= 0:issues.append('No positive net result after estimated costs')
        if stressed is not None and stressed <= 0:issues.append('Non-positive with twice the estimated fees')
        split = days // 2
        earlier = sum(x['net_pnl'] for x in daily[:split]) if complete and split else None
        later = sum(x['net_pnl'] for x in daily[split:]) if complete and split else None
        best = max((x['net_pnl'] for x in daily), default=0.)
        report[name] = dict(status='insufficient_evidence' if not complete or days<20 or not n or n<30 else 'failed_diagnostics' if issues else 'needs_independent_validation',
            issues=issues, observed_sessions=days, completed_trades=n,
            net_with_double_fees=stressed,
            net_without_best_day=round(net-best,2) if complete and n and net is not None else None,
            earlier_net=round(earlier,2) if earlier is not None else None,
            later_net=round(later,2) if later is not None else None,
            later_from=daily[split]['date'] if split else None,
            live_trading_approved=False)
    return report
