"""Read-only data jobs, isolated from strategy decisions and simulated fills.

Credentials are loaded from the existing service environment by each child.
They are never returned through HTTP or persisted in job configuration.
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import paper_agents as p

_guard = threading.Lock()
_children = {}


def root():
    base = p.paths()[1].parent / 'provider_evidence'
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    return base


def read(name):
    try: return json.loads((root()/f'{name}.json').read_text())
    except (OSError, ValueError): return {}


def write(name, value):
    target = root()/f'{name}.json'
    temp = target.with_suffix(f'.{os.getpid()}.tmp')
    with open(temp, 'w') as out:
        os.chmod(temp, 0o600)
        json.dump(value, out); out.flush(); os.fsync(out.fileno())
    os.replace(temp, target)


def storage():
    base = root().resolve()
    mount = Path('/var/data/kip')
    persistent = mount.is_mount() and base.is_relative_to(mount.resolve())
    return dict(persistent_mount_verified=persistent, free_bytes=shutil.disk_usage(base).free,
                policy_days=365, backup='Same-volume archive; independent disaster-recovery backup not verified')


def status():
    from .evidence_archive import status as retention
    return dict(config=read('config'), storage=storage(), retention=retention(),
                groww_stream=read('groww_stream'), groww_history=read('groww_history'),
                upstox_history=read('upstox_history'), live_validation=read('live_validation'), data_comparison=read('data_comparison'), strategy_validation=read('strategy_validation'), legacy_validation=read('legacy_validation'), execution='Observation only; no provider switching or orders')


def start(activate=False):
    with _guard:
        cfg=read('config')
        if activate:
            if not cfg:
                end=datetime.now(p.IST).date()-timedelta(days=1)
                cfg=dict(start=(end-timedelta(days=364)).isoformat(),end=end.isoformat())
            cfg['enabled']=True; write('config',cfg)
        if not cfg.get('enabled'): return dict(enabled=False)
        if not storage()['persistent_mount_verified']:
            return dict(enabled=True,blocked='Persistent evidence mount not verified')
        for name, module in [
            ('upstox_history','options_lab.year_history'),
            ('groww_history','options_lab.year_history'),
            ('groww_stream','options_lab.groww_observer'),
            ('validation_monitor','options_lab.validation_pipeline'),
            ('experiment','options_lab.validation_pipeline'),
        ]:
            old=_children.get(name)
            if old and old.poll() is None: continue
            state=read(name)
            if name.endswith('history') and state.get('finished_at') and state.get('download_version')=='v2': continue
            if name=='experiment':
                history=read('upstox_history')
                if not history.get('finished_at') or history.get('download_version')!='v2':continue
                result=read('strategy_validation')
                if result.get('status') in ('complete','failed'):continue
            # A failed provider gets at most one retry per five minutes.
            if state.get('retry_after') and state['retry_after']>datetime.now(timezone.utc).isoformat(): continue
            child=subprocess.Popen([sys.executable,'-m',module,name],stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                cwd=Path(__file__).resolve().parent.parent)
            try:
                child.stdin.write(json.dumps(cfg).encode());child.stdin.close()
            except Exception:
                child.terminate();raise
            _children[name]=child
        return dict(enabled=True)


def process_lock(name):
    lock=open(root()/f'{name}.lock','a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    return lock


if __name__=='__main__':
    import time
    try:lock=process_lock('supervisor')
    except BlockingIOError:sys.exit(0)
    while True:
        try:
            start()
            cutoff=(datetime.now(timezone.utc)-timedelta(days=365)).date().isoformat()
            for path in root().glob('groww-????-??-??.jsonl.gz'):
                if path.name[6:16]<cutoff:
                    path.unlink()
                    (root()/(path.name[:16]+'-manifest.json')).unlink(missing_ok=True)
        except Exception:pass
        time.sleep(60)
