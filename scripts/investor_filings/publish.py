"""Publish attributed filings separately from price valuations."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'investor_valuation'))
from publish import api, BRANCH

FILE = 'investor-filings/latest.json'
def publish(path):
    content = Path(path).read_bytes(); data = json.loads(content)
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(data['updatedAt'])).total_seconds()
    if data.get('schemaVersion') != 1 or not data.get('profiles') or not 0 <= age < 86400 or data.get('checkedCount', 0) < 1:
        raise ValueError('Invalid or empty filing scan; previous data preserved')
    previous = api(f'contents/{FILE}?ref={BRANCH}', missing_ok=True)
    body = {'message': 'Refresh original NSE investor disclosures', 'branch': BRANCH, 'content': base64.b64encode(content).decode()}
    if previous: body['sha'] = previous['sha']
    api(f'contents/{FILE}', 'PUT', body)
    print('Published exchange filing scan')
if __name__ == '__main__': publish(sys.argv[1])
