"""Evidence-backed investor entity mappings. No fuzzy match can publish a holding."""
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import re

DATA = Path(__file__).with_name('reference_data')
BUCKETS = {'personal', 'family', 'corporate', 'managed'}

def normal(value):
    return re.sub(r'[^a-z0-9]', '', str(value).lower())

def identity(profile_id, holder, scope):
    return hashlib.sha256(json.dumps([profile_id, normal(holder), scope], separators=(',', ':')).encode()).hexdigest()[:24]

def directory():
    return json.loads((DATA / 'investor_directory.json').read_text())

def validate(payload):
    people = {p['id']:p for p in directory()}
    person = str(payload.get('profileId', ''))
    if person not in people: raise ValueError('Choose a listed Indian investor.')
    holder = ' '.join(str(payload.get('holder', '')).split())
    if not 3 <= len(holder) <= 300: raise ValueError('Supply the full legal shareholder name.')
    scope = str(payload.get('scope', '')).strip().upper()
    if not re.fullmatch(r'\*|[A-Z0-9&_.-]{1,32}', scope): raise ValueError('Supply an issuer symbol, BSE code, ISIN, or * for a verified all-issuer identity.')
    bucket = payload.get('bucket')
    if bucket not in BUCKETS: raise ValueError('Choose personal, family, corporate, or managed holdings.')
    start = str(payload.get('validFrom', ''))
    end = str(payload.get('validTo') or '')
    try:
        date.fromisoformat(start)
        if end and date.fromisoformat(end) < date.fromisoformat(start): raise ValueError()
    except ValueError: raise ValueError('Supply valid effective dates (YYYY-MM-DD).')
    evidence = str(payload.get('evidenceUrl', '')).strip()
    u = urlparse(evidence)
    if u.scheme != 'https' or not u.hostname or u.username or len(evidence)>2000:
        raise ValueError('A public HTTPS evidence link is required.')
    note = str(payload.get('evidenceNote', '')).strip()
    if not 15 <= len(note) <= 2000: raise ValueError('Explain what the source establishes, including group membership where relevant.')
    status = payload.get('status', 'approved')
    if status not in {'approved','rejected','revoked'}: raise ValueError('Invalid review decision.')
    return {'id':identity(person,holder,scope),'profileId':person,'holder':holder,'scope':scope,'bucket':bucket,
            'validFrom':start,'validTo':end or None,'evidenceUrl':evidence,'evidenceNote':note,'status':status}

def seeds():
    return [validate(r) for r in json.loads((DATA / 'investor_mapping_seeds.json').read_text())]

def registry():
    from institutional_warehouse import db
    records = {r['id']:r for r in seeds()}
    for row in db.query('SELECT mapping_json FROM wh_investor_entity_mappings'):
        item = json.loads(row['mapping_json']); records[item['id']] = item
    return {'ok':True,'mappings':list(records.values()),'directory':directory()}

def save(payload, actor):
    from institutional_warehouse import gateway
    item = validate(payload)
    item.update(reviewedAt=datetime.now(timezone.utc).isoformat(), reviewedBy=actor)
    result = gateway.write('investor_entity_mappings',[{'mapping_id':item['id'],'mapping_json':json.dumps(item)}],
                           source='investor_mapping_admin',actor=actor,reason='Review investor legal entity mapping')
    if not result.get('ok') or result.get('quarantined'): raise RuntimeError('Mapping was not saved.')
    return {'ok':True,'mapping':item}

def applies(mapping, filing):
    return (mapping['status']=='approved' and mapping['validFrom'] <= filing['period']
            and (not mapping.get('validTo') or filing['period'] <= mapping['validTo'])
            and mapping['scope'] in {'*', filing.get('symbol'), filing.get('isin'), filing.get('scripCode')})


def build_profiles(people, filings, mappings):
    profiles = {}; candidates = []
    # One latest document per ISIN, across both exchanges. Missing ISINs remain
    # source-scoped and cannot contribute to combined totals.
    issuers = {}
    for filing in filings:
        if filing.get('status') != 'ok': continue
        key = filing.get('isin') or filing.get('symbol')
        rank = (filing['period'], filing.get('submittedISO') or '', filing.get('exchange') == 'NSE')
        if key not in issuers or rank > issuers[key][0]: issuers[key] = (rank, filing)
    for person in people:
        pid = person.get('id') or 'in-' + person['slug']
        rules = [m for m in mappings if m['profileId']==pid]
        byholder = {}
        for rule in rules: byholder.setdefault(normal(rule['holder']), []).append(rule)
        rows = []; count_review = 0
        tokens = [t for t in re.findall(r'[a-z0-9]+',person['name'].lower()) if t not in {'and','associates','family','group','limited','ltd','private','pvt','the','of'}]
        for _, filing in issuers.values():
            counts = {}
            for row in filing['rows']: counts[normal(row['holder'])] = counts.get(normal(row['holder']),0)+1
            for row in filing['rows']:
                key = normal(row['holder']); approved = [m for m in byholder.get(key,[]) if applies(m,filing)]
                # Scoped review decisions override global approval for that issuer.
                scoped = [m for m in byholder.get(key,[]) if m['scope'] in {filing.get('symbol'),filing.get('isin'),filing.get('scripCode')} and m['validFrom'] <= filing['period'] and (not m.get('validTo') or filing['period']<=m['validTo'])]
                if scoped: approved = [m for m in scoped if m['status']=='approved']
                blocked = any(m['status'] in {'rejected','revoked'} and m['scope'] in {'*',filing.get('symbol'),filing.get('isin'),filing.get('scripCode')} and m['validFrom'] <= filing['period'] and (not m.get('validTo') or filing['period'] <= m['validTo']) for m in byholder.get(key,[]))
                exact = key == normal(person['name']) and not blocked
                if counts[key]==1 and (approved or exact):
                    buckets = {m['bucket'] for m in approved}
                    if len(buckets)>1: continue
                    rule = approved[0] if approved else None
                    rows.append({**row, **{k:filing.get(k) for k in ('symbol','stock','period','url','submitted','isin','scripCode','exchange','stale')},
                                 'bucket':rule['bucket'] if rule else ('corporate' if person.get('category')=='institutional' else 'personal'),
                                 'matchType':'approved mapping' if rule else 'exact name',
                                 'mappingId':rule['id'] if rule else None,'mappingEvidence':rule['evidenceUrl'] if rule else None})
                    continue
                if blocked or not tokens or count_review>=12: continue
                words = set(re.findall(r'[a-z0-9]+',row['holder'].lower()))
                overlap = sum(t in words for t in tokens)
                similar = overlap >= max(2,len(tokens)-1) or (len(tokens)==1 and len(tokens[0])>=3 and tokens[0] in words)
                if not similar: continue
                candidate = {'profileId':pid,'name':person['name'],'holder':row['holder'],'scope':filing.get('isin') or filing['symbol'],
                             'stock':filing['stock'],'period':filing['period'],'evidenceUrl':filing['url'],
                             'reason':'Duplicate shareholder contexts need reconciliation' if counts[key]>1 else 'Possible name or group relationship; identity not verified'}
                candidate['id']=identity(pid,row['holder'],candidate['scope'])
                if not any(c['id']==candidate['id'] for c in candidates): candidates.append(candidate); count_review+=1
        profiles[pid] = {'name':person['name'],'rows':sorted(rows,key=lambda r:(r['period'],r['stock'],r['holder']),reverse=True),
                         'approvedMappings':len([m for m in rules if m['status']=='approved']), 'reviewCount':count_review}
    return profiles,candidates


def bse_documents():
    from institutional_warehouse import db
    return [json.loads(r['filing_json']) for r in db.query('SELECT filing_json FROM wh_investor_bse_filings')]


def save_bse(payload, actor):
    from institutional_warehouse import gateway
    from financial_warehouse_completion.shareholding_xml import import_bse
    filing=import_bse(payload)
    filing['reviewedAt']=datetime.now(timezone.utc).isoformat()
    result=gateway.write('investor_bse_filings',[{'filing_id':filing['isin']+':'+filing['period'],'filing_json':json.dumps(filing)}],
                         source='original_bse_xbrl_admin',actor=actor,reason='Import original BSE shareholder disclosure')
    if not result.get('ok') or result.get('quarantined'): raise RuntimeError('BSE document was not saved.')
    return {'ok':True,'stock':filing['stock'],'period':filing['period'],'rows':len(filing['rows'])}
