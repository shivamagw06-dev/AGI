"""Twelve-month, lossless daily archives. Delete hot rows only after verification.

Archives remain beside the configured evidence database (persistent storage is
required). They are not backups: operators must back up this volume separately.
"""
import fcntl
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import zlib
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import paper_agents as p

RETENTION_DAYS = 365
HOT_DAYS = 14
_lock = threading.Lock()


def root():
    path = p.paths()[1].parent / 'nifty_second_archive'
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def archive_lock(exclusive=False):
    with open(root()/'archive.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


def durable(path):
    with open(path,'rb') as f:os.fsync(f.fileno())
    fd=os.open(str(path.parent),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def read_file(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            at, rows = json.loads(line)
            yield at, rows


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def _maintain(now=None):
    now = now or datetime.now(timezone.utc)
    base = root()
    # Never trade disk safety for silent evidence loss.
    if shutil.disk_usage(base).free < 512*1024*1024:
        raise ValueError('Archive needs at least 512 MiB free; hot evidence retained. Increase storage.')
    cutoff = (now-timedelta(days=HOT_DAYS)).date().isoformat()
    with closing(p.database()) as db:
        days = [r[0] for r in db.execute('SELECT DISTINCT substr(at,1,10) FROM second_frames WHERE at<? ORDER BY at',(cutoff,))]
    for day in days:
        path = base / (day+'.jsonl.gz')
        meta=path.with_suffix('.json')
        if path.exists() and meta.exists():
            manifest=json.loads(meta.read_text())
            if digest(path)!=manifest['sha256']:raise ValueError('Existing archive checksum failed; hot evidence retained')
            archived={at for at,_ in read_file(path)}
            with closing(p.database()) as db:
                remaining=[x[0] for x in db.execute('SELECT at FROM second_frames WHERE at>=? AND at<?',(day,day+'Z'))]
            if not set(remaining)<=archived:raise ValueError('Late rows outside verified archive; retain for reconciliation')
            while True:
                with closing(p.database()) as db,db:
                    removed=db.execute('DELETE FROM second_frames WHERE at IN (SELECT at FROM second_frames WHERE at>=? AND at<? LIMIT 500)',(day,day+'Z')).rowcount
                if not removed:break
            continue
        tmp = path.with_suffix('.tmp')
        # Rebuild from hot evidence, including any late rows; hot rows are
        # immutable and the collector only appends today's observations.
        count = 0;written=hashlib.sha256()
        with gzip.open(tmp, 'wt', compresslevel=6) as f:
            after = day
            while True:
                with closing(p.database()) as db:
                    page = db.execute('SELECT at,payload FROM second_frames WHERE at>? AND at<? ORDER BY at LIMIT 250',
                                      (after, day+'Z')).fetchall()
                if not page: break
                for at, payload in page:
                    line=json.dumps([at,json.loads(zlib.decompress(payload))],separators=(',',':'))+'\n'
                    f.write(line);written.update(line.encode())
                    count += 1
                after = page[-1][0]
        checked=hashlib.sha256();verified=0
        with gzip.open(tmp,'rt') as f:
            for line in f:
                json.loads(line);checked.update(line.encode());verified+=1
        if verified != count or checked.digest()!=written.digest():
            raise ValueError('Archive verification failed; hot evidence retained')
        with open(tmp, 'rb') as f: os.fsync(f.fileno())
        os.replace(tmp,path)
        manifest = dict(day=day,frames=count,sha256=digest(path),bytes=path.stat().st_size)
        meta = path.with_suffix('.json')
        temp_meta = meta.with_suffix('.tmp')
        temp_meta.write_text(json.dumps(manifest));durable(temp_meta);os.replace(temp_meta,meta);durable(meta)
        # The durable manifest and archive now exist; release disk rows in batches.
        while True:
            with closing(p.database()) as db, db:
                removed=db.execute('DELETE FROM second_frames WHERE at IN (SELECT at FROM second_frames WHERE at>=? AND at<? LIMIT 500)',(day,day+'Z')).rowcount
            if not removed:break
    expiry = (now-timedelta(days=RETENTION_DAYS)).date().isoformat()
    for path in base.glob('*.jsonl.gz'):
        if path.name[:10] < expiry:
            path.unlink();path.with_suffix('.json').unlink(missing_ok=True)
    (base/'status.json').write_text(json.dumps(dict(last_success=now.isoformat(),error=None)))


def maintain(now=None):
    with archive_lock(exclusive=True):
        _maintain(now)


def launch():
    if not _lock.acquire(blocking=False): return
    def job():
        try:
            subprocess.run([sys.executable,'-m','options_lab.evidence_archive'],
                cwd=Path(__file__).resolve().parent.parent,timeout=1800,check=True,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except Exception:
            (root()/'status.json').write_text(json.dumps(dict(error='Archive maintenance failed; unarchived hot evidence retained. Check disk capacity.')))
        finally: _lock.release()
    threading.Thread(target=job,daemon=True).start()


def archived_frames(first, last):
    for path in sorted(root().glob('*.jsonl.gz')):
        if path.name[:10] < first[:10] or path.name[:10] > last[:10]: continue
        meta = json.loads(path.with_suffix('.json').read_text())
        if digest(path) != meta['sha256']: raise ValueError('Recorded archive checksum failed')
        for at, rows in read_file(path):
            if first <= at < last: yield p.timestamp(at), rows


def status():
    base = root(); manifests=[json.loads(x.read_text()) for x in base.glob('*.jsonl.json')]
    state = json.loads((base/'status.json').read_text()) if (base/'status.json').exists() else {}
    return dict(retention_days=RETENTION_DAYS,hot_days=HOT_DAYS,archived_days=len(manifests),
        archive_bytes=sum(m['bytes'] for m in manifests),free_bytes=shutil.disk_usage(base).free,
        oldest_archived_day=min((m['day'] for m in manifests),default=None),**state)


if __name__=='__main__':
    try: os.nice(10)
    except (AttributeError,OSError): pass
    maintain()
