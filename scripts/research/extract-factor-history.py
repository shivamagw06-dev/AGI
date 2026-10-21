"""Extract cached observations; never execute Excel macros or overwrite the source."""
import datetime as dt
import hashlib
import json
import math
import pathlib
import sys
import zipfile
import xml.etree.ElementTree as ET
import openpyxl

source = pathlib.Path(sys.argv[1])
root = pathlib.Path(__file__).resolve().parents[2]
w = openpyxl.load_workbook(source, read_only=True, data_only=True)
keys = ['momentum', 'value', 'growth', 'quality', 'all-weather']
rows, excluded = [], []
for rowno, row in enumerate(w['Factor Performance'].values, 1):
    if not isinstance(row[0], dt.datetime):
        continue
    date = row[0].date().isoformat()
    values = list(row[13:18])
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > -1 for v in values):
        excluded.append({'date': date, 'row': rowno, 'values': values})
        continue
    rows.append([date, *values])
assert rows and len({r[0] for r in rows}) == len(rows)
assert rows == sorted(rows)
assert all(x['date'] < rows[0][0] for x in excluded), 'Internal missing data requires review'
# Reconcile every cached chart point, not just the rounded screenshot totals.
ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
with zipfile.ZipFile(source) as z:
    chart = ET.fromstring(z.read('xl/charts/chart1.xml'))
checks = []
for col, key in enumerate(keys, 14):
    ser = next(s for s in chart.findall('.//c:ser', ns) if s.find('./c:val/c:numRef/c:f', ns).text == f'Temp!${chr(64+col)}$167:${chr(64+col)}$329')
    cache = [float(p.text) for p in ser.findall('./c:val//c:pt/c:v', ns)]
    window = [[r[0].date().isoformat(), *r[13:18]] for r in w['Temp'].values if isinstance(r[0], dt.datetime) and dt.datetime(2026,1,1) <= r[0] <= dt.datetime(2026,8,14)][:162]
    calculated = [100.0]
    for r in window:
        calculated.append(calculated[-1] * (1 + r[col-13]))
    assert len(cache) == len(calculated)
    error = max(abs(a-b) for a,b in zip(cache, calculated))
    assert error < 1e-9, (key, error)
    summary = w['Performance Summary'].cell(18+col-14, 3).value
    assert abs(calculated[-1]/100-1-summary) < 1e-12
    source_level = 100.0
    for r in rows:
        if '2026-01-01' <= r[0] <= '2026-08-14':
            source_level *= 1+r[col-13]
    checks.append({'sourceReturnPct': source_level-100, 'factor': key, 'pointsChecked': len(cache), 'maxIndexDifference': error, 'returnPct': summary*100})
result = {
    'source': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'sheet': 'Factor Performance', 'columns': 'A, N:R',
    'asOf': rows[-1][0], 'firstReturnDate': rows[0][0],
    'baselineDate': '2010-01-01',
    'baselineNote': 'Synthetic 100 reference only; source return for 2010-01-01 is #NAME? and is excluded. Valid compounding begins 2010-01-04.',
    'keys': keys, 'excluded': excluded, 'reconciliation': checks, 'rows': rows,
}
(root/'src/data/jpm-factor-history.json').write_text(json.dumps(result, separators=(',', ':'))+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'}, indent=2))
print('Valid observations:',len(rows))
