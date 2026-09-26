"""Publish attributed filings separately from price valuations."""
import base64
import gzip
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'investor_valuation'))
from publish import api, BRANCH

FILE = 'investor-filings/latest.json'
def publish(path):
    data = json.loads(Path(path).read_bytes())
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(data['updatedAt'])).total_seconds()
    if data.get('schemaVersion') != 1 or not data.get('profiles') or not 0 <= age < 86400 or data.get('checkedCount', 0) < 1 or not isinstance(data.get('filings'),dict) or not data['filings']:
        raise ValueError('Invalid or empty filing scan; previous data preserved')
    cache_path='investor-filings/cache.json.gz'
    cache=gzip.compress(json.dumps(data.pop('filings',{}),ensure_ascii=False).encode(),mtime=0)
    old=api(f'contents/{cache_path}?ref={BRANCH}',missing_ok=True)
    body={'message':'Cache original shareholder facts for reviewed mappings','branch':BRANCH,'content':base64.b64encode(cache).decode()}
    if old: body['sha']=old['sha']
    saved=api(f'contents/{cache_path}','PUT',body)
    data['cacheUrl']=f"https://raw.githubusercontent.com/shivamagw06-dev/AGI/{saved['commit']['sha']}/{cache_path}"
    content=json.dumps(data,ensure_ascii=False).encode()
    previous = api(f'contents/{FILE}?ref={BRANCH}', missing_ok=True)
    body = {'message': 'Refresh original investor disclosures and mapping review queue', 'branch': BRANCH, 'content': base64.b64encode(content).decode()}
    if previous: body['sha'] = previous['sha']
    api(f'contents/{FILE}', 'PUT', body)
    print('Published original filings and immutable fact cache')
if __name__ == '__main__': publish(sys.argv[1])
