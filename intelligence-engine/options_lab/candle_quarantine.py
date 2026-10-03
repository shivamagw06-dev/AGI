"""Partition rejected raw candles for review; never writes to the history store.

Candidates are not complete chunks. Invalid timestamps, conflicting duplicate
versions and cached-price conflicts remain quarantined. No prices are filled.
"""
from datetime import datetime
from .year_history import normalize
from .minute_history import p


def import_reviewed(con, provider, records, artifact_sha256):
    """Atomically import reviewed candidates; never mark chunks/gaps complete.

    Caller must supply records with instrument, normalized row and provenance.
    This helper does not approve a recovery artifact or reconcile source conflicts.
    """
    import json
    if len(artifact_sha256) != 64 or any(c not in '0123456789abcdef' for c in artifact_sha256):
        raise ValueError('Invalid artifact SHA256')
    con.execute('SAVEPOINT reviewed_recovery')
    inserted = 0
    try:
        con.execute('''CREATE TABLE IF NOT EXISTS recovery_provenance(
            provider TEXT, instrument TEXT, at TEXT, artifact_sha256 TEXT,
            provenance TEXT, PRIMARY KEY(provider,instrument,at,artifact_sha256))''')
        for record in records:
            instrument, row = record['instrument'], record['row']
            provenance = record['provenance']
            if not instrument or not provenance or normalize([row]) != [row]:
                raise ValueError('Unreviewed or non-normalized candidate')
            old = con.execute('SELECT payload FROM candles WHERE provider=? AND instrument=? AND at=?',
                              (provider, instrument, row[0])).fetchone()
            if old is not None and json.loads(old[0]) != row:
                raise ValueError('Cached conflict: recovery rolled back')
            cursor = con.execute('INSERT OR IGNORE INTO candles VALUES(?,?,?,?)',
                                 (provider, instrument, row[0], json.dumps(row)))
            inserted += cursor.rowcount
            con.execute('INSERT OR IGNORE INTO recovery_provenance VALUES(?,?,?,?,?)',
                        (provider, instrument, row[0], artifact_sha256, json.dumps(provenance, sort_keys=True)))
        con.execute('RELEASE SAVEPOINT reviewed_recovery')
    except Exception:
        con.execute('ROLLBACK TO SAVEPOINT reviewed_recovery')
        con.execute('RELEASE SAVEPOINT reviewed_recovery')
        raise
    return {'inserted': inserted, 'complete': False, 'gaps_preserved': True}


def partition(rows, start, end, cached=None):
    if not isinstance(rows, list):
        raise ValueError('Invalid candles container')
    cached = cached or {}
    groups, rejected = {}, []
    for index, raw in enumerate(rows):
        stamp = None
        try:
            if isinstance(raw, list) and raw:
                value = str(raw[0])
                if len(value) == 19:
                    value += '+05:30'
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is not None:
                    stamp = parsed.astimezone(p.IST).isoformat()
            row = normalize([raw])[0]
            stamp = row[0]
            if not start <= stamp[:10] <= end:
                raise ValueError('Candles outside requested range')
            groups.setdefault(stamp, []).append((index, raw, row))
        except (ValueError, TypeError, IndexError) as exc:
            rejected.append(dict(index=index, at=stamp, raw=raw, reason=str(exc)))
    bad_times = {r['at'] for r in rejected if r['at'] is not None}
    candidates = []
    for stamp, versions in sorted(groups.items()):
        row = versions[0][2]
        reason = None
        if stamp in bad_times:
            reason = 'Timestamp also has an invalid version'
        elif any(v[2] != row for v in versions):
            reason = 'Conflicting candles'
        elif stamp in cached and cached[stamp] != row:
            reason = 'Provider corrected cached data; manual reconciliation needed'
        if reason:
            rejected.extend(dict(index=i, at=stamp, raw=raw, reason=reason)
                            for i, raw, _ in versions)
        else:
            candidates.append(row)
    return dict(candidates=candidates, quarantine=sorted(rejected, key=lambda x:x['index']),
                raw_count=len(rows), complete=False,
                status='review_only_not_imported')
