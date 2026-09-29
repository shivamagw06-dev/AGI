from datetime import datetime, timedelta
from options_lab.replay_evidence import ReplayEvidence, iv_schedule, validation_report, signal_direction

NOW=datetime.fromisoformat('2026-09-28T10:00:00+05:30')


def test_iv_schedule_never_uses_same_day_or_future_import_and_rejects_invalid():
    rows=[dict(day='2026-09-25',at='2026-09-25T15:30+05:30',available_at=NOW.isoformat(),iv=20),
          dict(day='2026-09-28',at='2026-09-28T15:30+05:30',available_at=NOW.isoformat(),iv=20),
          dict(day='bad',iv=20),dict(day='2026-09-25',at=NOW.isoformat(),iv=float('nan'))]
    schedule=iv_schedule(rows)
    assert len(schedule)==2 and schedule[0][0]==NOW
    assert schedule[1][0].date().isoformat()=='2026-09-29'


def test_direction_labels_match_spread_payoffs():
    for kind,short,long,expected in [('CE',100,150,'bearish'),('CE',150,100,'bullish'),('PE',150,100,'bullish'),('PE',100,150,'bearish')]:
        assert signal_direction(dict(pending=dict(legs=[dict(side='SELL',option_type=kind,strike=short),dict(side='BUY',option_type=kind,strike=long)])))==expected


def test_audit_keeps_first_bearish_evidence_and_counts_beyond_truncated_journal():
    audit=ReplayEvidence();a=dict(status='signal',pending=dict(context=dict(name='TREND_DOWN',adx=28)),trades=[])
    for i in range(105):
        now=NOW+timedelta(seconds=i)
        a['events']=[dict(at=now.isoformat(),kind='signal',reason='confirmed trend')]
        audit.observe(now,{'credit':a},{'name':'TREND_DOWN'})
        audit.observe(now,{'credit':a})  # duplicate cannot count twice
    r=audit.finish({'credit':a})['credit']
    assert r['event_counts']['signal']==105 and len(r['recent_decisions'])==100
    assert r['first_bearish_signal']['at']==NOW.isoformat()
    assert r['first_bearish_signal']['context']['adx']==28


def test_validation_counts_all_trades_before_ui_truncation_and_stresses_fees():
    audit=ReplayEvidence();a=dict(status='ready',events=[],trades=[])
    for i in range(30):
        now=NOW+timedelta(days=i)
        audit.observe(now,{'test':a})
        a['trades'].append(dict(exit_at=now.isoformat(),pnl=10,entry_cost=6,exit_cost=5))
    evidence=audit.finish({'test':a})
    report=validation_report({'test':dict(evidence_status='observed',closed_trades=30,net_pnl=300,total_charges=330)},evidence)['test']
    assert report['status']=='failed_diagnostics'
    assert report['net_with_double_fees']==-30
    assert report['earlier_net']==150 and report['later_net']==150
    assert report['net_without_best_day']==290 and report['live_trading_approved'] is False


def test_missing_data_never_passes_or_gets_zero_return():
    report=validation_report({'x':dict(evidence_status='insufficient_data',closed_trades=None,net_pnl=None,total_charges=None)}, {})['x']
    assert report['status']=='insufficient_evidence'
    assert report['net_with_double_fees'] is None and report['earlier_net'] is None


def test_positive_sample_never_automatically_approves_live_trading():
    daily=[dict(date=f'2026-09-{i:02}',net_pnl=100) for i in range(1,21)]
    r=validation_report({'x':dict(evidence_status='observed',closed_trades=30,net_pnl=2000,total_charges=100)}, {'x':dict(daily_results=daily)})['x']
    assert r['status']=='needs_independent_validation' and not r['live_trading_approved']
