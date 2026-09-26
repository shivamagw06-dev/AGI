"""Build institutional snapshots from saved public retrievals and supplied directory.
Usage: python scripts/build-institutional-profiles.py SUMMARY_JSON RETRIEVALS_JSON
Raw retrievals are retained locally; only factual holdings are shipped.
"""
import json,re,sys
from pathlib import Path
from importlib.machinery import SourceFileLoader
b=SourceFileLoader('investor_builder',str(Path(__file__).with_name('build-investor-profiles.py'))).load_module()
root=Path(__file__).resolve().parents[1]
summaries=json.loads(Path(sys.argv[1]).read_text());inputs=json.loads(Path(sys.argv[2]).read_text())
assert len(summaries)==len({r['name'] for r in summaries})==100
profiles=[]
for source in inputs:
 p=b.trendlyne(source);p['category']='institutional'
 if not p['sourceUrl']:
  m=re.search(r'https://trendlyne.com/portfolio/superstar-shareholders/\d+/latest/[^/\s]+/',source['parts'][0]);p['sourceUrl']=m[0] if m else None
 p['extraNote']='Institutional and group disclosure snapshot. Group totals may combine related entities; overlapping groups must not be added together.'
 p=b.coverage(p)
 assert all(len(r['history'])==len(p['periods']) for r in p['rows']),p['name']
 assert len({r['stock'] for r in p['rows']})==len(p['rows']),p['name']
 profiles.append(p)
summary_by_name={r['name']:r for r in summaries}
for p in profiles:
 summary_by_name[p['name']]['url']=p['sourceUrl']
 (root/'src/data/investorProfiles/holdings'/('in-'+p['slug']+'.json')).write_text(json.dumps(p,ensure_ascii=False,separators=(',',':'))+'\n')
idxpath=root/'src/data/investorProfiles/index.json';index=json.loads(idxpath.read_text());index=[p for p in index if p.get('category')!='institutional']
assert not ({p['slug'] for p in index}&{p['slug'] for p in profiles})
index.extend({k:p[k] for k in ['name','country','slug','reportPeriod','coverageLabel','sourceUrl','category']} for p in profiles)
idxpath.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
(root/'src/data/institutionalInvestors.js').write_text('// Owner-supplied 100-name directory, matched to public source entries on 2026-09-26.\n// Valuation date was not supplied; detailed holdings retain separate source periods.\nexport const indiaInstitutionalInvestors = '+json.dumps(sorted(summaries,key=lambda x:-x['value']),ensure_ascii=False,indent=2)+';\n')
print(json.dumps({'profiles':len(profiles),'withHoldings':sum(bool(p['rows']) for p in profiles),'rows':sum(len(p['rows']) for p in profiles),'partial':[p['name'] for p in profiles if p['rows'] and not p['retrievalComplete']]}))
