"""Read existing public AGI filing endpoints; never publishes or authenticates."""
import concurrent.futures
import json
from pathlib import Path
import subprocess

MAPPINGS = {
    'Warren Buffett': 'berkshire-hathaway',
    'Baillie Gifford': 'baillie-gifford',
    'Kenneth C. Griffin': 'citadel-advisors',
    'Jim Simons': 'renaissance-technologies',
    'Bill Gates': 'gates-foundation-trust',
    'Ole Andreas Halvorsen': 'viking-global',
    'Raymond Thomas Dalio': 'bridgewater-associates',
    'Philippe Laffont': 'coatue-management',
    'Charles T. Akre': 'akre-capital',
    'Steve Mandel': 'lone-pine-capital',
    'Bill Ackman': 'pershing-square',
    'Daniel Loeb': 'third-point',
    'Seth Klarman': 'baupost-group',
    'Lee Ainslie': 'maverick-capital',
    'George Soros': 'soros-fund-management',
    'Stanley Druckenmiller': 'duquesne-family-office',
    'Li Lu': 'himalaya-capital',
    'David Tepper': 'appaloosa-management',
    'Mohnish Pabrai': 'dalal-street',
    'Michael Burry': 'scion-asset-management',
}

if __name__ == '__main__':
    destination = Path('/private/tmp/agi-investor-sec'); destination.mkdir(exist_ok=True)
    def fetch(item):
        name, slug = item
        try:
            response = subprocess.run(['curl', '-fsS', '--max-time', '150', 'https://finance-news-backend-19i5.onrender.com/api/institutional-holdings/funds/' + slug], check=True, capture_output=True, text=True)
            data = json.loads(response.stdout)
            (destination / (slug + '.json')).write_text(json.dumps(data))
            return {'name': name, 'rows': len(data.get('holdings', [])), 'review': (data.get('latest_filing') or {}).get('needs_review')}
        except Exception as error:
            return {'name': name, 'error': str(error)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(fetch, MAPPINGS.items()):
            print(json.dumps(result), flush=True)
