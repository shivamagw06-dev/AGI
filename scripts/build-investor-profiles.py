"""Build factual snapshots from retrieved public tables and AGI's SEC records.

Raw retrievals are local inputs, not shipped. No source commentary, inferred
trades, missing values, or reconstructed chart data are included.
"""
import json
import re
from pathlib import Path
from fetch_investor_sec_snapshots import MAPPINGS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'src/data/investorProfiles'
RETRIEVED = '2026-09-26'


def slug(name):
    text = name.strip().lower()
    hashed = 2166136261
    for c in text:
        hashed = ((hashed ^ ord(c)) * 16777619) & 0xffffffff
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-') + '-' + format(hashed, 'x')


def clean(text):
    return re.sub(r'cite\d+†([^]+)', lambda m: m[1].strip(), text).strip()


def read_lines(parts):
    lines = {}
    for part in parts:
        for m in re.finditer(r'L(\d+):\s?([\s\S]*?)(?=L\d+:|$)', part):
            lines[int(m[1])] = m[2].strip()
    return lines


def trendlyne(entry):
    parts = entry['parts']; first = parts[0]; lines = read_lines(parts)
    text = '\n'.join(v for _, v in sorted(lines.items()))
    country = entry['country']
    pattern = r'https://(?:us\.)?trendlyne.com/(?:us/)?portfolio/superstar-shareholders/\d+/latest/[^/\s)]+/?'
    source = re.search(pattern, first)
    total = re.search(r'Total lines: (\d+)', first)
    total = int(total[1]) if total else 0
    header = next((s for s in lines.values() if s.startswith('Expand  | Stock') or s.startswith('Stock Name  |')), '')
    columns = [clean(s) for s in header.split('|')]
    rows = []
    for _, line in sorted(lines.items()):
        cells = [clean(s) for s in line.split('|')]
        if country == 'IN' and re.match(r'^\s*\|\s*cite', line) and len(cells) == len(columns) and len(columns) >= 8:
            rows.append(dict(stock=cells[1], value=cells[2], quantity=cells[3], change=cells[4], history=cells[5:-2]))
        elif country == 'US' and line.startswith('cite') and len(cells) == len(columns) == 8:
            rows.append(dict(stock=cells[0], holder=cells[1], quantity=cells[3], history=[cells[4]], change=cells[5], value=cells[6]))
        elif country == 'US' and '|' not in line:
            flat = re.fullmatch(r'cite\d+†([^]+)\s+(.+?)\s+([\d,.]+)\s+([\d,]+)\s+([\d.]+%)\s+(-?[\d.]+|-)\s+([\d,.]+\s+[KMB])\s*(?:cite\d+†\s*)?', line)
            if flat:
                rows.append(dict(stock=flat[1].strip(), holder=flat[2], quantity=flat[4], history=[flat[5]], change=flat[6], value=flat[7]))
    period = re.search(r'\[Button:\s*([^\]]+)\]', text) or re.search(r'portfolio and holdings - ([A-Za-z]+ \d{4})', text)
    count = re.search(r'publicly holds ([\d,]+) stocks', text)
    complete = total > 1 and all(n in lines for n in range(total))
    limited = 'Results truncated' in text
    crawled = re.search(r'Crawled: ([^;]+);', first)
    return dict(name=entry['name'], country=country, slug=slug(entry['name']), kind='india-disclosures' if country == 'IN' else 'us-disclosures',
                sourceUrl=source[0] if source else None, sourceLabel='Trendlyne', retrievedAt=RETRIEVED,
                sourceCrawled=crawled[1] if crawled else None, reportPeriod=period[1].strip() if period else None,
                periods=columns[5:-2] if country == 'IN' and len(columns) >= 8 else ['Reported holding %'] if country == 'US' else [],
                sourceReportedCount=int(count[1].replace(',', '')) if count else None,
                sourceLimited=limited, retrievalComplete=complete, rows=rows)


def sec(profile):
    manager = MAPPINGS.get(profile['name']) if profile['country'] == 'US' else None
    path = Path('/private/tmp/agi-investor-sec') / (str(manager) + '.json')
    if not manager or not path.exists():
        return profile
    data = json.loads(path.read_text()); filing = data.get('latest_filing') or {}
    holdings = data.get('holdings') or []
    if not holdings or filing.get('needs_review'):
        return profile
    # Avoid claiming a complete table if the saved filing and collected rows differ.
    complete = len(holdings) == filing.get('holdings_count')
    rows = []
    for row in holdings:
        security = ' · '.join(str(row[k]) for k in ['title_of_class', 'put_call', 'share_type'] if row.get(k))
        weight = row.get('portfolio_weight')
        value = row.get('value_usd')
        quantity = row.get('shares')
        rows.append(dict(stock=row['issuer_name'], security=security, cusip=row.get('cusip'),
                         value=f'{value / 1_000_000:,.4f} M' if value is not None else None,
                         quantity=f'{quantity:,}' if quantity is not None else None,
                         change=None, history=[f'{weight:.4f}%' if weight is not None else None]))
    profile.update(kind='sec13f', sourceLabel='SEC 13F · AGI filing archive', sourceUrl=filing['source_url'],
                   managerName=data['manager']['display_name'], managerSlug=manager, reportPeriod=filing['report_date'],
                   filedAt=filing.get('filed_at'), sourceCrawled=None, periods=['Portfolio weight (%)'],
                   sourceReportedCount=filing.get('holdings_count'), sourceLimited=bool(filing.get('confidential_omitted')),
                   retrievalComplete=complete, rows=rows)
    return profile


def coverage(profile):
    rows = profile['rows']
    if not rows:
        profile['coverageLabel'] = 'Detailed source unavailable'
        profile['coverageNote'] = 'A usable detailed table was not available from the public source during collection. No missing holdings have been inferred.'
    elif profile['sourceLimited'] or not profile['retrievalComplete']:
        profile['coverageLabel'] = 'Partial disclosed portfolio'
        profile['coverageNote'] = f"{len(rows):,} rows are available. The source limits its results or retrieval is incomplete; this must not be read as the full portfolio."
    else:
        profile['coverageLabel'] = 'Retrieved disclosure snapshot'
        profile['coverageNote'] = f"{len(rows):,} rows were captured from the linked source. Public disclosures do not establish a complete current portfolio."
    if profile.get('sourceReportedCount') is not None:
        profile['coverageNote'] += f" The source reports {profile['sourceReportedCount']:,} positions for its period; historical rows and security classes can affect comparisons."
    if profile.get('sourceCrawled'):
        profile['coverageNote'] += ' Retrieval-cache age at collection: ' + profile['sourceCrawled'] + '.'
    return profile


def dataroma(profile, sources):
    if profile['country'] != 'US' or profile['name'] not in sources:
        return profile
    parts = sources[profile['name']]
    lines = read_lines(parts)
    text = '\n'.join(v for _, v in sorted(lines.items()))
    rows = []
    for line in lines.values():
        cells = [clean(s) for s in line.split('|')]
        if len(cells) == 12 and cells[0] == '≡' and re.fullmatch(r'[\d.]+', cells[2]) and re.fullmatch(r'\$[\d,]+', cells[6]):
            rows.append(dict(stock=cells[1], value=cells[6], quantity=cells[4], change=cells[3] or None, history=[cells[2] + '%']))
    if not rows:
        return profile
    source = re.search(r'https://www.dataroma.com/m/holdings.php\?m=[\w-]+', parts[0])
    period = re.search(r'Portfolio date: ([^\n]+)', text)
    count = re.search(r'No. of stocks: ([\d,]+)', text)
    count = int(count[1].replace(',', '')) if count else None
    manager = next((clean(line).removesuffix(' i') for line in lines.values() if profile['name'].split()[-1].lower() in clean(line).lower() and ' - ' in line and '|' not in line and not line.startswith('*') and len(line) < 160), None)
    profile.update(kind='fund-disclosures', sourceLabel='Dataroma', sourceUrl=source[0] if source else None,
                   managerName=manager, reportPeriod=period[1] if period else None, periods=['Portfolio weight (%)'],
                   sourceReportedCount=count, sourceLimited=False, retrievalComplete=len(rows) == count,
                   sourceCrawled=(re.search(r'Crawled: ([^;]+);', parts[0]) or [None, None])[1], rows=rows)
    return profile


if __name__ == '__main__':
    inputs = json.loads(Path('/private/tmp/agi-portfolio-web-sources.json').read_text())
    dataroma_path = Path('/private/tmp/agi-portfolio-dataroma-sources.json')
    dataroma_sources = {s['name']: s['parts'] for s in json.loads(dataroma_path.read_text())} if dataroma_path.exists() else {}
    profiles = [coverage(sec(dataroma(trendlyne(entry), dataroma_sources))) for entry in inputs]
    (OUTPUT / 'holdings').mkdir(parents=True, exist_ok=True)
    directory = []
    for profile in profiles:
        assert all(len(row['history']) == len(profile['periods']) for row in profile['rows']), profile['name']
        path = OUTPUT / 'holdings' / (profile['country'].lower() + '-' + profile['slug'] + '.json')
        path.write_text(json.dumps(profile, ensure_ascii=False, separators=(',', ':')) + '\n')
        directory.append({k: profile[k] for k in ['name', 'country', 'slug', 'reportPeriod', 'coverageLabel', 'sourceUrl']})
    (OUTPUT / 'index.json').write_text(json.dumps(directory, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'profiles': len(profiles), 'with_holdings': sum(bool(p['rows']) for p in profiles), 'rows': sum(len(p['rows']) for p in profiles)}))
