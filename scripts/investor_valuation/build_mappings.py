"""Build conservative, reviewable symbol mappings from existing AGI reference data."""
import csv, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def norm(s):
    s = re.sub(r'\b(limited|ltd|incorporated|inc|corporation|corp|company|co)\b', '', s.lower())
    return re.sub('[^a-z0-9]', '', s)
def build(sec_dir):
    candidates = {}
    for path in [ROOT/'EQUITY_L.csv', ROOT/'SME_EQUITY_L.csv']:
        for r in csv.DictReader(path.open()):
            candidates.setdefault(norm(r.get('NAME OF COMPANY',r.get('NAME_OF_COMPANY'))), set()).add(r['SYMBOL']+'.NS')
    mappings = {'IN': {}, 'CUSIP': {}}
    for p in (ROOT/'src/data/investorProfiles/holdings').glob('in-*.json'):
        for r in json.loads(p.read_text())['rows']:
            found = candidates.get(norm(r['stock']), set())
            if len(found)==1:
                mappings['IN'][r['stock']] = {'symbol': next(iter(found)), 'source': 'NSE equity security master, exact normalized company name'}
    cusips = {}
    for p in Path(sec_dir).glob('*.json'):
        for r in json.loads(p.read_text()).get('holdings', []):
            if r.get('ticker') and r.get('share_type')=='SH' and not r.get('put_call'):
                cusips.setdefault(r['cusip'],set()).add(r['ticker'].replace('.','-'))
    for key, values in cusips.items():
        if len(values)==1:
            mappings['CUSIP'][key] = {'symbol':next(iter(values)), 'source':'AGI SEC holdings archive identifier mapping'}
    out=ROOT/'src/data/investorProfiles/priceMappings.json'
    out.write_text(json.dumps(mappings,indent=2)+'\n')
    print({k:len(v) for k,v in mappings.items()})
if __name__=='__main__':
    import sys
    build(sys.argv[1])
