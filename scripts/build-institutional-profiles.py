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
country=sys.argv[3] if len(sys.argv)>3 else 'IN'
assert country in {'IN','US'}
assert len(summaries)==len({r['name'] for r in summaries})==len(inputs)
assert {r['name'] for r in summaries}=={r['name'] for r in inputs}
profiles=[]
for source in inputs:
 p=b.trendlyne(source);p['category']='institutional'
 if not p['sourceUrl']:
  m=re.search(r'https://(?:us\.)?trendlyne.com/(?:us/)?portfolio/superstar-shareholders/\d+/latest/[^/\s]+/',source['parts'][0]);p['sourceUrl']=m[0] if m else None
 p['extraNote']='Institutional and group disclosure snapshot. Group totals may combine related entities; overlapping groups must not be added together.'
 p=b.coverage(p)
 assert all(len(r['history'])==len(p['periods']) for r in p['rows']),p['name']
 if country=='IN':assert len({r['stock'] for r in p['rows']})==len(p['rows']),p['name']
 # US tables may disclose multiple holder entities for the same security.
 profiles.append(p)
summary_by_name={r['name']:r for r in summaries}
for p in profiles:
 summary_by_name[p['name']]['url']=p['sourceUrl']
 (root/'src/data/investorProfiles/holdings'/(country.lower()+'-'+p['slug']+'.json')).write_text(json.dumps(p,ensure_ascii=False,separators=(',',':'))+'\n')
idxpath=root/'src/data/investorProfiles/index.json';index=json.loads(idxpath.read_text());index=[p for p in index if not (p.get('category')=='institutional' and p['country']==country)]
assert not ({p['slug'] for p in index}&{p['slug'] for p in profiles})
index.extend({k:p[k] for k in ['name','country','slug','reportPeriod','coverageLabel','sourceUrl','category']} for p in profiles)
idxpath.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
(root/('src/data/institutionalInvestors.js' if country=='IN' else 'src/data/usInstitutionalInvestors.js')).write_text('// Owner-supplied directory matched to public source entries on 2026-09-26.\n// Valuation date was not supplied; detailed holdings retain separate source periods.\nexport const '+('indiaInstitutionalInvestors' if country=='IN' else 'usaInstitutionalInvestors')+' = '+json.dumps(sorted(summaries,key=lambda x:-x['value']),ensure_ascii=False,indent=2)+';\n')
print(json.dumps({'profiles':len(profiles),'withHoldings':sum(bool(p['rows']) for p in profiles),'rows':sum(len(p['rows']) for p in profiles),'partial':[p['name'] for p in profiles if p['rows'] and not p['retrievalComplete']]}))
