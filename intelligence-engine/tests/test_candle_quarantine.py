from options_lab.candle_quarantine import partition
from options_lab.candle_quarantine import import_reviewed
import sqlite3
import json
import pytest


def recovery_db():
    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE candles(provider TEXT,instrument TEXT,at TEXT,payload TEXT,PRIMARY KEY(provider,instrument,at))')
    con.execute('CREATE TABLE gaps(reason TEXT)')
    con.execute("INSERT INTO gaps VALUES('partial rejected chunk')")
    con.commit()
    return con


def record(close=101, stamp='2026-01-28T09:15:00'):
    row = partition([candle(stamp, close)], '2026-01-28', '2026-01-28')['candidates'][0]
    return dict(instrument='FUT', row=row, provenance=['raw-source.gz'])


def test_recovery_idempotent_preserves_gaps_and_provenance():
    con = recovery_db()
    assert import_reviewed(con, 'groww', [record()], 'a'*64)['inserted'] == 1
    assert import_reviewed(con, 'groww', [record()], 'a'*64)['inserted'] == 0
    assert con.execute('SELECT count(*) FROM recovery_provenance').fetchone()[0] == 1
    assert con.execute('SELECT reason FROM gaps').fetchone()[0] == 'partial rejected chunk'


def test_recovery_conflict_rolls_back_entire_batch():
    con = recovery_db()
    import_reviewed(con, 'groww', [record()], 'a'*64)
    with pytest.raises(ValueError, match='Cached conflict'):
        import_reviewed(con, 'groww', [record(stamp='2026-01-28T09:16:00'), record(close=100)], 'b'*64)
    assert con.execute('SELECT count(*) FROM candles').fetchone()[0] == 1
    assert con.execute('SELECT count(*) FROM recovery_provenance').fetchone()[0] == 1


def test_recovery_invalid_candidate_rolls_back():
    con = recovery_db()
    bad = record()
    bad['provenance'] = []
    with pytest.raises(ValueError):
        import_reviewed(con, 'groww', [record(), bad], 'a'*64)
    assert con.execute('SELECT count(*) FROM candles').fetchone()[0] == 0


def candle(t='2026-01-28T09:15:00',close=101):
    return [t,100,102,99,close,10,None]


def test_valid_rows_survive_null_prices_without_claiming_complete():
    raw=[['2026-01-28T09:00:00',None,None,None,None],candle()]
    r=partition(raw,'2026-01-28','2026-02-03')
    assert len(r['candidates'])==1 and len(r['quarantine'])==1
    assert r['quarantine'][0]['raw']==raw[0]
    assert not r['complete'] and r['status']=='review_only_not_imported'


def test_conflicting_versions_both_quarantined():
    r=partition([candle(),candle(close=100)],'2026-01-28','2026-02-03')
    assert not r['candidates'] and len(r['quarantine'])==2


def test_invalid_version_prevents_same_timestamp_candidate():
    r=partition([candle(),['2026-01-28T09:15:00',None,None,None,None]],'2026-01-28','2026-02-03')
    assert not r['candidates'] and len(r['quarantine'])==2


def test_identical_duplicates_deduplicate():
    r=partition([candle(),candle()],'2026-01-28','2026-02-03')
    assert len(r['candidates'])==1 and not r['quarantine']


def test_cached_conflict_is_not_overwritten():
    old=partition([candle(close=100)],'2026-01-28','2026-02-03')['candidates'][0]
    r=partition([candle()],'2026-01-28','2026-02-03',{old[0]:old})
    assert not r['candidates'] and 'cached' in r['quarantine'][0]['reason']


def test_invalid_timestamp_and_out_of_range_preserved():
    r=partition([candle('bad'),candle('2026-02-04T09:15:00')],'2026-01-28','2026-02-03')
    assert not r['candidates'] and len(r['quarantine'])==2
