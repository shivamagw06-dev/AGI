"""Preserve the full non-option comparison input before the public audit is trimmed."""
import gzip
import json


def normalized_snapshot(report):
    managers = []
    for manager in report['managers']:
        holdings = {}
        for row in manager.get('auditHoldings', []):
            if row['unit'] != 'SH' or row['option']:
                continue
            key = row['cusip']
            holding = holdings.setdefault(key, {k: row[k] for k in ['cusip', 'issuer', 'securityClass']})
            holding['quantity'] = holding.get('quantity', 0) + row['quantity']
        managers.append({**{k: manager.get(k) for k in [
            'slug', 'name', 'cik', 'managerType', 'checkedAt', 'status', 'latest',
            'prior', 'comparisonStatus', 'comparisonError',
        ]}, 'holdings': list(holdings.values()), 'changes': manager.get('changes', [])})
    return {'checkedAt': report['checkedAt'], 'managers': managers}


def write_snapshot(report, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(normalized_snapshot(report), separators=(',', ':')).encode(), mtime=0))
