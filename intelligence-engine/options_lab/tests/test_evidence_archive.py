import json,zlib
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import pytest
from options_lab import evidence_archive as a,paper_agents as p
NOW=datetime(2026,9,29,tzinfo=timezone.utc)
@pytest.fixture
def store(tmp_path):
    with patch.object(p,'paths',return_value=(tmp_path/'source',tmp_path/'paper')):
        with p.database() as db:
            for days in (5,30,200):
                at=(NOW-timedelta(days=days)).isoformat();db.execute('INSERT INTO second_frames VALUES(?,?)',(at,zlib.compress(json.dumps([{'sample':days}]).encode())))
        yield tmp_path

def test_archive_verified_before_hot_delete_and_round_trip(store):
    a.maintain(NOW)
    with p.database() as db:assert db.execute('SELECT count(*) FROM second_frames').fetchone()[0]==1
    rows=list(a.archived_frames('2026-01-01',NOW.isoformat()))
    assert [r[1][0]['sample'] for r in rows]==[200,30]
    assert a.status()['archived_days']==2 and a.status()['retention_days']==365
    a.maintain(NOW);assert a.status()['archived_days']==2

def test_failed_write_never_deletes_hot_evidence(store):
    with patch.object(a.gzip,'open',side_effect=OSError('disk full')):
        with pytest.raises(OSError):a.maintain(NOW)
    with p.database() as db:assert db.execute('SELECT count(*) FROM second_frames').fetchone()[0]==3

def test_corruption_refuses_replay(store):
    a.maintain(NOW);path=next(a.root().glob('*.jsonl.gz'));path.write_bytes(b'broken')
    with pytest.raises(ValueError,match='checksum'):list(a.archived_frames('2026-01-01',NOW.isoformat()))

def test_retains_six_months_and_expires_only_after_year(store):
    a.maintain(NOW);a.maintain(NOW+timedelta(days=170))
    assert a.status()['archived_days']==2

def test_restart_after_partial_pruning_does_not_shrink_archive(store):
    at=(NOW-timedelta(days=30)).isoformat();payload=zlib.compress(json.dumps([{'sample':30}]).encode())
    a.maintain(NOW)
    # Simulate a process crash after archive commit, before hot pruning completed.
    with p.database() as db:db.execute('INSERT INTO second_frames VALUES(?,?)',(at,payload))
    before=list(a.archived_frames('2026-01-01',NOW.isoformat()))
    a.maintain(NOW)
    assert list(a.archived_frames('2026-01-01',NOW.isoformat()))==before


def test_detailed_replay_reads_older_archived_frames(store):
    from options_lab import replay
    from options_lab.tests.test_regime_agents import chain
    at=NOW-timedelta(days=30)+timedelta(hours=5)
    with p.database() as db:
        db.execute('DELETE FROM second_frames')
        db.execute('INSERT INTO second_frames VALUES(?,?)',(at.isoformat(),zlib.compress(json.dumps(chain(at)).encode())))
    a.maintain(NOW)
    result=replay.run(replay.request_config(at.date().isoformat(),at.date().isoformat()))
    assert result['coverage']['frames']==1
    assert result['coverage']['days']==[at.date().isoformat()]
