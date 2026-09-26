"""Original exchange SHP XBRL parser, shared by scheduled collection and admin import."""
from decimal import Decimal
from xml.etree import ElementTree as ET
import re
from datetime import date

def local(tag):
    return tag.rsplit('}', 1)[-1]

def parse(raw, period):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('External declarations unsupported')
    root = ET.fromstring(raw)
    # Join duration/name and instant/quantity contexts by their dimensions,
    # not by context-id spelling; this also prevents mixing different dates.
    contexts, facts = {}, {}
    for item in root:
        if local(item.tag) == 'context':
            dims = tuple(sorted((e.get('dimension', ''), ''.join(e.itertext()).strip()) for e in item.iter() if local(e.tag) in ('typedMember', 'explicitMember')))
            dates = [e.text for e in item.iter() if local(e.tag) in ('instant', 'endDate')]
            contexts[item.get('id')] = (dims, dates[0] if len(dates) == 1 else None)
        elif item.get('contextRef'):
            key = (item.get('contextRef'), local(item.tag))
            value = (item.text or '').strip()
            if key in facts and facts[key] != value: raise ValueError('Conflicting XBRL facts')
            facts[key] = value
    quantities = {}
    for (ctx, tag), value in facts.items():
        if tag != 'NumberOfShares' or ctx not in contexts: continue
        dims, date = contexts[ctx]
        if not dims or date != period: continue
        qty = Decimal(value)
        if not qty.is_finite() or qty < 0 or qty != int(qty): raise ValueError('Invalid share count')
        pct = facts.get((ctx, 'ShareholdingAsAPercentageOfTotalNumberOfShares'))
        pct = Decimal(pct) * 100 if pct else None
        if pct is not None and (not pct.is_finite() or not 0 <= pct <= 100): raise ValueError('Invalid ownership')
        record = {'quantity': int(qty), 'ownershipPct': float(pct) if pct is not None else None}
        if dims in quantities and quantities[dims] != record: raise ValueError('Ambiguous shareholder dimensions')
        quantities[dims] = record
    result = []
    for (ctx, tag), name in facts.items():
        if tag != 'NameOfTheShareholder' or ctx not in contexts: continue
        dims, date = contexts[ctx]
        if date != period or dims not in quantities or not name: continue
        if facts.get((ctx, 'WhetherACategoryOrMoreThan1PercentageOfShareholding'), '').lower() == 'category': continue
        result.append({'holder': name, **quantities[dims]})
    if not result: raise ValueError('No named shareholder facts for filing period')
    return result


def metadata(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('External declarations unsupported')
    root=ET.fromstring(raw)
    fields={}
    for tag in ('ISIN','ScripCode','Symbol','NameOfTheCompany'):
        values={str(e.text or '').strip() for e in root if local(e.tag)==tag}
        if len(values)>1: raise ValueError('Conflicting issuer identity')
        fields[tag]=next(iter(values),'')
    if not re.fullmatch(r'IN[A-Z0-9]{10}',fields['ISIN']): raise ValueError('Missing or invalid issuer ISIN')
    return {'isin':fields['ISIN'],'scripCode':fields['ScripCode'],'symbol':fields['Symbol'],'stock':fields['NameOfTheCompany']}


def import_bse(payload):
    from urllib.parse import urlparse
    raw=str(payload.get('xml','')).encode()
    if not raw or len(raw)>2_000_000: raise ValueError('Upload original XBRL XML under 2 MB.')
    period=str(payload.get('period',''))
    if date.fromisoformat(period)>date.today(): raise ValueError('Filing period cannot be in the future.')
    info=metadata(raw)
    expected=str(payload.get('scripCode','')).strip()
    if not re.fullmatch(r'\d{6}',expected) or info['scripCode']!=expected: raise ValueError('BSE scrip code does not match the document.')
    url=str(payload.get('sourceUrl','')).strip();u=urlparse(url)
    if u.scheme!='https' or not u.hostname or u.username or len(url)>2000: raise ValueError('Link the original public HTTPS filing.')
    rows=parse(raw,period)
    return {**info,'symbol': info['symbol'] if re.fullmatch(r'[A-Z0-9&_.-]+',info['symbol']) and info['symbol'] not in {'NA','-'} else 'BSE-'+expected,
            'period':period,'url':url,'exchange':'BSE','status':'ok','rows':rows,'cacheVersion':2,
            'submitted':str(payload.get('submitted') or ''),'provenance':'administrator-supplied original XBRL'}
