"""Optional approved BSE manifest connection plus administrator-supplied XBRL.

The manifest contract is deliberately explicit; no guessed/private BSE API.
Configure BSE_SHAREHOLDING_FEED_URL for an authorised JSON manifest containing
filings: [{url, period, scripCode}]. Original document URLs must be BSE-hosted.
A missing or failed feed remains visible and cannot erase imported disclosures.
"""
from datetime import datetime, timezone
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Feed redirects are not allowed')

def collect_bse(imported, previous, get, parse, metadata):
    records = {(f['isin'],f['period']):f for f in [*previous,*imported] if f.get('status')=='ok' and f.get('isin') and f.get('exchange')=='BSE'}
    url = os.getenv('BSE_SHAREHOLDING_FEED_URL','').strip()
    state={'state':'not_configured','message':'Automatic BSE feed not connected. Administrator-imported original documents are included when available.','importedCount':len(imported),'checkedCount':0,'failedCount':0}
    if not url: return list(records.values()),state
    try:
        u=urlparse(url)
        if u.scheme!='https' or not u.hostname or u.username: raise ValueError('Invalid approved feed URL')
        headers={'Accept':'application/json'}
        token=os.getenv('BSE_SHAREHOLDING_FEED_TOKEN','').strip()
        if token: headers['Authorization']='Bearer '+token
        with build_opener(NoRedirect()).open(Request(url,headers=headers),timeout=30) as response:
            raw=response.read(5_000_001)
            if len(raw)>5_000_000: raise ValueError('Manifest exceeds size limit')
        manifest=json.loads(raw)
        entries=manifest.get('filings')
        if not isinstance(entries,list) or not entries or len(entries)>10000: raise ValueError('Invalid manifest')
        known_urls={f.get('url') for f in records.values()}
        pending=[entry for entry in entries if entry.get('url') not in known_urls]
        state['checkedCount']=len(entries)-len(pending)
        for entry in pending[:250]:
            try:
                doc=entry['url'];target=urlparse(doc)
                if target.scheme!='https' or target.hostname not in {'www.bseindia.com','bseindia.com'} or target.username: raise ValueError('Document must be an original BSE URL')
                existing=next((f for f in records.values() if f.get('url')==doc),None)
                if existing: state['checkedCount']+=1; continue
                data=get(doc);info=metadata(data)
                if info['scripCode']!=str(entry['scripCode']): raise ValueError('BSE issuer mismatch')
                rows=parse(data,entry['period'])
                filing={**info,'symbol':info['symbol'] or 'BSE-'+info['scripCode'],'period':entry['period'],'url':doc,'exchange':'BSE','status':'ok','rows':rows,'cacheVersion':2,'submitted':entry.get('submitted',''),'submittedISO':entry.get('submittedISO',''),'provenance':'approved BSE feed'}
                records[(info['isin'],entry['period'])]=filing;state['checkedCount']+=1
            except Exception: state['failedCount']+=1
        state.update(state='partial' if state['failedCount'] or len(pending)>250 else 'connected',message='BSE feed checked; only validated original documents included.',pendingCount=max(0,len(pending)-250)+state['failedCount'],checkedAt=datetime.now(timezone.utc).isoformat())
    except Exception as exc:
        state.update(state='unavailable',message='BSE feed unavailable; previous original documents retained.',error=type(exc).__name__)
    return list(records.values()),state
