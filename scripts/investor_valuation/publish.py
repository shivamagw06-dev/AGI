"""Atomically publish the public snapshot to a dedicated machine-owned data branch."""
import base64, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
REPO='shivamagw06-dev/AGI'
BRANCH='investor-valuation-data'
FILE='investor-valuations/latest.json'

def validate(data):
    if data.get('schemaVersion')!=1 or not data.get('profiles'):
        raise ValueError('Invalid valuation snapshot')
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(data['updatedAt'])).total_seconds()
    if not 0<=age<86400: raise ValueError('Snapshot must be from the last 24 hours')
    if not any(p.get('pricedCount',0)>0 for p in data['profiles'].values()):
        raise ValueError('No priced holdings; preserve previous snapshot')

def api(path,method='GET',data=None,missing_ok=False):
    args=['gh','api',f'repos/{REPO}/{path}','--method',method]
    if data is not None: args+=['--input','-']
    result=subprocess.run(args,input=json.dumps(data) if data is not None else None,capture_output=True,text=True)
    if result.returncode:
        if missing_ok and 'HTTP 404' in result.stderr: return None
        raise RuntimeError('GitHub data publication failed: '+result.stderr[:300])
    return json.loads(result.stdout) if result.stdout else None

def publish(path):
    content=Path(path).read_bytes();validate(json.loads(content))
    if api(f'git/ref/heads/{BRANCH}',missing_ok=True) is None:
        main=api('git/ref/heads/main')
        api('git/refs','POST',{'ref':f'refs/heads/{BRANCH}','sha':main['object']['sha']})
    previous=api(f'contents/{FILE}?ref={BRANCH}',missing_ok=True)
    body={'message':'Refresh daily disclosed-holdings valuations','branch':BRANCH,'content':base64.b64encode(content).decode()}
    if previous: body['sha']=previous['sha']
    api(f'contents/{FILE}','PUT',body)
    print('Published public valuation snapshot to the dedicated data branch')
if __name__=='__main__': publish(sys.argv[1])
