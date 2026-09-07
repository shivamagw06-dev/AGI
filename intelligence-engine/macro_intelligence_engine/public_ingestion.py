"""Durable public macro ingestion. Background runtime only; never called by page reads."""
from __future__ import annotations
import calendar, csv, hashlib, io, json, math, os, re, time, urllib.error, urllib.parse, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from macro_intelligence_engine.public_data import CORE_50

SOURCE_DEFAULTS = {
    "growth": ("MoSPI", "https://www.mospi.gov.in/"), "inflation": ("MoSPI", "https://www.mospi.gov.in/"),
    "labour": ("MoSPI", "https://www.mospi.gov.in/"), "monetary": ("RBI", "https://data.rbi.org.in/DBIE/"),
    "fiscal": ("IMF", "https://data.imf.org/"), "external": ("Ministry of Commerce / RBI", "https://tradestat.commerce.gov.in/"),
    "credit": ("BIS / RBI", "https://data.bis.org/"), "currency": ("RBI / BIS", "https://data.rbi.org.in/DBIE/"),
    "activity": ("MoSPI / OECD", "https://www.mospi.gov.in/"), "property": ("BIS / RBI", "https://data.bis.org/"),
    "financial": ("RBI / BIS", "https://data.rbi.org.in/DBIE/"), "global": ("IMF / World Bank / BIS / OECD", "https://data.imf.org/"),
}
WORLD_BANK_SERIES = {
    "gdp": ("NY.GDP.MKTP.CD", "USD", "IND"), "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "%", "IND"),
    "investment": ("NE.GDI.FTOT.ZS", "% GDP", "IND"), "unemployment": ("SL.UEM.TOTL.ZS", "%", "IND"),
    "government_debt_gdp": ("GC.DOD.TOTL.GD.ZS", "% GDP", "IND"), "current_account_gdp": ("BN.CAB.XOKA.GD.ZS", "% GDP", "IND"),
    "exports": ("NE.EXP.GNFS.CD", "USD", "IND"), "imports": ("NE.IMP.GNFS.CD", "USD", "IND"),
    "private_credit_gdp": ("FS.AST.PRVT.GD.ZS", "% GDP", "IND"), "global_gdp": ("NY.GDP.MKTP.KD.ZG", "%", "WLD"),
}
G20_COUNTRIES = {
    "ARG":"Argentina", "AUS":"Australia", "BRA":"Brazil", "CAN":"Canada", "CHN":"China",
    "FRA":"France", "DEU":"Germany", "IND":"India", "IDN":"Indonesia", "ITA":"Italy",
    "JPN":"Japan", "MEX":"Mexico", "RUS":"Russia", "SAU":"Saudi Arabia", "ZAF":"South Africa",
    "KOR":"South Korea", "TUR":"Türkiye", "GBR":"United Kingdom", "USA":"United States",
}
G20_WORLD_BANK_SERIES = {
    "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "Growth", "%"),
    "inflation": ("FP.CPI.TOTL.ZG", "Inflation", "%"),
    "unemployment": ("SL.UEM.TOTL.ZS", "Labour", "%"),
    "government_debt_gdp": ("GC.DOD.TOTL.GD.ZS", "Fiscal", "% GDP"),
    "current_account_gdp": ("BN.CAB.XOKA.GD.ZS", "External", "% GDP"),
    "investment_gdp": ("NE.GDI.FTOT.ZS", "Growth", "% GDP"),
    "private_credit_gdp": ("FS.AST.PRVT.GD.ZS", "Financial", "% GDP"),
    "gdp_per_capita": ("NY.GDP.PCAP.CD", "Structural", "USD"),
}
IMF_G20_SERIES = {
    "gdp_growth": ("NGDP_RPCH", "Growth", "%"), "inflation": ("PCPIPCH", "Inflation", "%"),
    "unemployment": ("LUR", "Labour", "%"), "government_debt_gdp": ("GGXWDG_NGDP", "Fiscal", "% GDP"),
    "fiscal_balance_gdp": ("GGXCNL_NGDP", "Fiscal", "% GDP"), "current_account_gdp": ("BCA_NGDPD", "External", "% GDP"),
}
YAHOO_MACRO_MARKET_SERIES = {
    "usd_fx": {"symbol": "INR=X", "country": "IND", "unit": "INR per USD"},
    "oil": {"symbol": "BZ=F", "country": "WLD", "unit": "USD/barrel"},
    "gas": {"symbol": "NG=F", "country": "WLD", "unit": "USD/MMBtu"},
    "copper": {"symbol": "HG=F", "country": "WLD", "unit": "USD/lb"},
    "gold": {"symbol": "GC=F", "country": "WLD", "unit": "USD/troy oz"},
    "global_risk": {"symbol": "^VIX", "country": "WLD", "unit": "index"},
}
BIS_INDIA_SERIES = {
    "credit_gdp_gap": {"flow":"WS_CREDIT_GAP","key":"Q.IN.P.A.C","unit":"% GDP","frequency":"quarterly","label":"Credit-to-GDP Gap"},
    "debt_service_ratio": {"flow":"WS_DSR","key":"Q.IN.P","unit":"%","frequency":"quarterly","label":"Debt-Service Ratio"},
    "house_prices": {"flow":"WS_SPP","key":"Q.IN.N.628","unit":"index (2010=100)","frequency":"quarterly","label":"House Prices"},
    "bank_credit": {"flow":"WS_TC","key":"Q.IN.P.B.M.USD.A","unit":"USD billions","frequency":"quarterly","label":"Bank Credit"},
}

# Search is a gap-filling evidence source, not a substitute for an official
# statistical connector.  Results outside these domains are never persisted.
INDIA_MACRO_SOURCE_DOMAINS = (
    "rbi.org.in", "mospi.gov.in", "commerce.gov.in", "indiabudget.gov.in",
    "dea.gov.in", "labour.gov.in", "data.gov.in", "bis.org", "imf.org",
    "worldbank.org", "oecd.org", "ilo.org", "unctad.org",
)
WEB_REQUIRED_TERMS = {
    "gdp_qoq": ("qoq", "q-o-q", "quarter-on-quarter", "quarter on quarter", "sequential"),
    "industrial_production": ("industrial production", "index of industrial production", "iip"),
    "cpi": ("consumer price index", "headline cpi", "cpi"),
    "core_cpi": ("core inflation", "core cpi"),
    "food_inflation": ("food inflation", "food price"),
    "policy_rate": ("repo rate", "policy rate"),
    "fx_reserves": ("foreign exchange reserves", "forex reserves", "fx reserves"),
}
FMP_US_INDICATORS = (
    "GDP", "realGDP", "federalFunds", "CPI", "inflationRate", "retailSales",
    "consumerSentiment", "unemploymentRate", "totalNonfarmPayroll",
    "industrialProductionTotalIndex", "tradeBalanceGoodsAndServices",
)
FMP_INDIA_EVENT_PATTERNS = (
    (re.compile(r"\bgdp\b.*\b(qoq|quarter.on.quarter)\b", re.I), "gdp_qoq"),
    (re.compile(r"\bgdp\b.*\b(yoy|year.on.year|growth)\b", re.I), "gdp_growth"),
    (re.compile(r"\b(consumer price|cpi)\b", re.I), "cpi"),
    (re.compile(r"\b(core cpi|core inflation)\b", re.I), "core_cpi"),
    (re.compile(r"\b(food inflation|food price)\b", re.I), "food_inflation"),
    (re.compile(r"\b(industrial production|index of industrial production|iip)\b", re.I), "industrial_production"),
    (re.compile(r"\b(repo rate|interest rate decision|policy rate)\b", re.I), "policy_rate"),
    (re.compile(r"\btrade balance\b", re.I), "trade_balance"),
    (re.compile(r"\bexports?\b", re.I), "exports"),
    (re.compile(r"\bimports?\b", re.I), "imports"),
    (re.compile(r"\b(forex|foreign exchange|fx) reserves?\b", re.I), "fx_reserves"),
    (re.compile(r"\b(composite pmi|pmi composite)\b", re.I), "pmi"),
    (re.compile(r"\bconsumer confidence\b", re.I), "consumer_confidence"),
    (re.compile(r"\bunemployment rate\b", re.I), "unemployment"),
)

def _now(): return datetime.now(timezone.utc)


def _urlopen(request, *, timeout=30, attempts=3):
    """Open a public-data request with bounded retries for transient failures."""
    for attempt in range(max(1, attempts)):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            retryable = exc.code in {408, 425, 429, 500, 502, 503, 504}
            if not retryable or attempt + 1 >= attempts:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            time.sleep(min(delay, 10))
        except (TimeoutError, urllib.error.URLError):
            if attempt + 1 >= attempts:
                raise
            time.sleep(min(2 ** attempt, 10))


def _series_has_history(series_id):
    try:
        return bool(_rest("macro_public_observations", query=f"?select=id&series_id=eq.{series_id}&limit=1"))
    except Exception:
        return False

def _credentials():
    url=(os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or "").strip().rstrip("/"); key=(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key: raise RuntimeError("supabase_credentials_missing")
    return url,key

def _rest(table, *, method="GET", rows=None, query="", prefer=""):
    url,key=_credentials(); data=None if rows is None else json.dumps(rows,separators=(",",":"),default=str).encode()
    req=urllib.request.Request(f"{url}/rest/v1/{table}{query}",data=data,method=method,headers={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    if prefer:req.add_header("Prefer",prefer)
    with urllib.request.urlopen(req,timeout=30) as response: body=response.read(); return json.loads(body) if body else None

def _write_chunks(table, rows, *, query="", prefer="resolution=merge-duplicates,return=minimal", size=500):
    items=list(rows or [])
    for start in range(0,len(items),size):
        _rest(table,method="POST",rows=items[start:start+size],query=query,prefer=prefer)

def registry_rows():
    out=[]
    for series_id,domain,label,frequency in CORE_50:
        source,url=SOURCE_DEFAULTS[domain]; wb=WORLD_BANK_SERIES.get(series_id)
        out.append({"series_id":series_id,"country_code":wb[2] if wb else ("WLD" if domain=="global" else "IND"),"domain":domain,"label":label,"unit":wb[1] if wb else None,
            "frequency":frequency,"primary_source":"World Bank" if wb else source,"source_url":"https://api.worldbank.org/v2/" if wb else url,"source_series_id":wb[0] if wb else series_id,
            "license_class":"PUBLIC_OFFICIAL","refresh_policy":"ON_RELEASE","active":True,"metadata":{"connector":"world_bank" if wb else "pending_official_connector","ingestion_status":"CONNECTED" if wb else "REGISTERED","pit_policy":"first_successful_agi_fetch_unless_official_release_timestamp_is_supplied"},"updated_at":_now().isoformat()})
    return out

def seed_registry():
    rows=registry_rows(); _rest("macro_public_series_registry",method="POST",rows=rows,query="?on_conflict=series_id",prefer="resolution=merge-duplicates,return=minimal"); return {"ok":True,"registered":len(rows)}

def _wb_fetch(country, indicator, history=25):
    url=f"https://api.worldbank.org/v2/country/{country.lower()}/indicator/{indicator}?format=json&per_page=100&mrv={history}"; req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0"})
    with _urlopen(req, timeout=25) as response: raw=response.read()
    payload=json.loads(raw); rows=payload[1] if isinstance(payload,list) and len(payload)>1 and isinstance(payload[1],list) else []
    return [row for row in rows if row.get("value") is not None],hashlib.sha256(raw).hexdigest(),url

def collect_world_bank():
    run_id=str(uuid.uuid4()); errors=[]; observations=[]
    _rest("macro_public_ingestion_runs",method="POST",rows={"run_id":run_id,"source":"World Bank","status":"RUNNING","started_at":_now().isoformat()},prefer="return=minimal")
    for series_id,(indicator,unit,country) in WORLD_BANK_SERIES.items():
        try:
            history = 3 if _series_has_history(series_id) else 25
            rows,payload_hash,url=_wb_fetch(country,indicator,history=history)
            if not rows: errors.append(f"{series_id}:no_observation"); continue
            fetched=_now()
            for row in rows:
                period=str(row.get("date") or "")
                if not period[:4].isdigit(): continue
                observations.append({"series_id":series_id,"country_code":country,"period_date":f"{period[:4]}-12-31","value_numeric":row.get("value"),"unit":unit,"frequency":"annual","release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,"is_forecast":False,"source":"World Bank Indicators API","source_url":url,"source_payload_hash":payload_hash,"quality_status":"PROVISIONAL","metadata":{"indicator":indicator,"country_label":(row.get("country") or {}).get("value"),"pit_status":"FETCH_VINTAGE_ONLY","source_tier":"C"}})
        except Exception as exc: errors.append(f"{series_id}:{str(exc)[:100]}")
    if observations:_write_chunks("macro_public_observations",observations,query="?on_conflict=series_id,country_code,period_date,vintage_date,revision_number")
    status="COMPLETE" if observations and not errors else ("COMPLETE_WITH_WARNINGS" if observations else "FAILED")
    _rest("macro_public_ingestion_runs",method="PATCH",rows={"status":status,"completed_at":_now().isoformat(),"rows_received":len(WORLD_BANK_SERIES),"rows_accepted":len(observations),"rows_quarantined":len(errors),"error":";".join(errors)[:1000] or None,"receipt":{"series":[r["series_id"] for r in observations],"errors":errors}},query=f"?run_id=eq.{run_id}",prefer="return=minimal")
    return {"ok":bool(observations),"source":"World Bank","run_id":run_id,"status":status,"accepted":len(observations),"errors":errors}

def _g20_registry_rows():
    rows=[]
    for iso3,country in G20_COUNTRIES.items():
        for key,(indicator,domain,unit) in G20_WORLD_BANK_SERIES.items():
            rows.append({"series_id":f"g20_{iso3.lower()}_{key}","country_code":iso3,"domain":domain.lower(),"label":key.replace("_"," ").title(),"unit":unit,"frequency":"annual","primary_source":"World Bank G20 Comparison","source_url":"https://api.worldbank.org/v2/","source_series_id":indicator,"license_class":"PUBLIC_OFFICIAL","refresh_policy":"ON_RELEASE","active":True,"metadata":{"country_name":country,"upstream_indicator":indicator,"connector":"world_bank_g20","ingestion_status":"CONNECTED","pit_policy":"first_successful_agi_fetch"},"updated_at":_now().isoformat()})
    return rows

def collect_world_bank_g20():
    run_id=str(uuid.uuid4()); errors=[]; observations=[]; registry=_g20_registry_rows()
    _rest("macro_public_series_registry",method="POST",rows=registry,query="?on_conflict=series_id",prefer="resolution=merge-duplicates,return=minimal")
    _rest("macro_public_ingestion_runs",method="POST",rows={"run_id":run_id,"source":"World Bank G20","status":"RUNNING","started_at":_now().isoformat()},prefer="return=minimal")
    countries=";".join(code.lower() for code in G20_COUNTRIES)
    for key,(indicator,_domain,unit) in G20_WORLD_BANK_SERIES.items():
        sample_series = f"g20_ind_{key}"
        history = 3 if _series_has_history(sample_series) else 25
        url=f"https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}?format=json&per_page=5000&mrv={history}"
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0"})
            with _urlopen(req,timeout=30) as response: raw=response.read()
            payload=json.loads(raw); candidates=payload[1] if isinstance(payload,list) and len(payload)>1 else []
            histories={iso3: [] for iso3 in G20_COUNTRIES}
            for row in candidates or []:
                iso3=str(row.get("countryiso3code") or "").upper(); period=str(row.get("date") or "")
                if iso3 in G20_COUNTRIES and row.get("value") is not None and period[:4].isdigit(): histories[iso3].append(row)
            fetched=_now(); digest=hashlib.sha256(raw).hexdigest()
            for iso3,history in histories.items():
                for row in history:
                    period=str(row.get("date") or "")
                    observations.append({"series_id":f"g20_{iso3.lower()}_{key}","country_code":iso3,"period_date":f"{period[:4]}-12-31","value_numeric":row.get("value"),"unit":unit,"frequency":"annual","release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,"is_forecast":False,"source":"World Bank Indicators API","source_url":url,"source_payload_hash":digest,"quality_status":"PROVISIONAL","metadata":{"indicator":indicator,"country_name":G20_COUNTRIES[iso3],"pit_status":"FETCH_VINTAGE_ONLY","source_tier":"C"}})
            missing={iso3 for iso3,history in histories.items() if not history}
            if missing: errors.append(f"{key}:missing:{','.join(sorted(missing))}")
        except Exception as exc: errors.append(f"{key}:{str(exc)[:120]}")
    if observations:_write_chunks("macro_public_observations",observations,query="?on_conflict=series_id,country_code,period_date,vintage_date,revision_number")
    status="COMPLETE" if observations and not errors else ("COMPLETE_WITH_WARNINGS" if observations else "FAILED")
    _rest("macro_public_ingestion_runs",method="PATCH",rows={"status":status,"completed_at":_now().isoformat(),"rows_received":len(registry),"rows_accepted":len(observations),"rows_quarantined":len(errors),"error":";".join(errors)[:1000] or None,"receipt":{"countries":len(G20_COUNTRIES),"indicators":len(G20_WORLD_BANK_SERIES),"errors":errors}},query=f"?run_id=eq.{run_id}",prefer="return=minimal")
    return {"ok":bool(observations),"source":"World Bank G20","run_id":run_id,"status":status,"accepted":len(observations),"errors":errors}

def _persist_official_run(source, registry, observations, errors):
    run_id=str(uuid.uuid4()); started=_now()
    _rest("macro_public_ingestion_runs",method="POST",rows={"run_id":run_id,"source":source,"status":"RUNNING","started_at":started.isoformat()},prefer="return=minimal")
    if registry:_write_chunks("macro_public_series_registry",registry,query="?on_conflict=series_id")
    if observations:_write_chunks("macro_public_observations",observations,query="?on_conflict=series_id,country_code,period_date,vintage_date,revision_number")
    status="COMPLETE" if observations and not errors else ("COMPLETE_WITH_WARNINGS" if observations else "FAILED")
    _rest("macro_public_ingestion_runs",method="PATCH",rows={"status":status,"completed_at":_now().isoformat(),"rows_received":len(observations)+len(errors),"rows_accepted":len(observations),"rows_quarantined":len(errors),"error":";".join(errors)[:1000] or None,"receipt":{"series":len(registry),"observations":len(observations),"errors":errors}},query=f"?run_id=eq.{run_id}",prefer="return=minimal")
    return {"ok":bool(observations),"source":source,"run_id":run_id,"status":status,"accepted":len(observations),"errors":errors}

def collect_imf_g20():
    registry=[]; observations=[]; errors=[]; fetched=_now(); completed_year=fetched.year-1
    for key,(indicator,domain,unit) in IMF_G20_SERIES.items():
        url=f"https://www.imf.org/external/datamapper/api/v2/{indicator}"
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0"})
            with _urlopen(req,timeout=35) as response: raw=response.read()
            payload=json.loads(raw); values=((payload.get("values") or {}).get(indicator) or {}); digest=hashlib.sha256(raw).hexdigest()
            for iso3,country in G20_COUNTRIES.items():
                history=values.get(iso3) or {}; eligible=[(int(y),v) for y,v in history.items() if str(y).isdigit() and 2000<=int(y)<=completed_year and v is not None]
                series_id=f"imf_{iso3.lower()}_{key}"
                registry.append({"series_id":series_id,"country_code":iso3,"domain":domain.lower(),"label":key.replace("_"," ").title(),"unit":unit,"frequency":"annual","primary_source":"IMF WEO DataMapper","source_url":url,"source_series_id":indicator,"license_class":"PUBLIC_OFFICIAL","refresh_policy":"ON_RELEASE","active":True,"metadata":{"country_name":country,"connector":"imf_datamapper","dataset":"WEO","ingestion_status":"CONNECTED","pit_policy":"first_successful_agi_fetch"},"updated_at":fetched.isoformat()})
                if not eligible: errors.append(f"{indicator}:{iso3}:no_completed_observation"); continue
                for year,value in eligible:
                    observations.append({"series_id":series_id,"country_code":iso3,"period_date":f"{year}-12-31","value_numeric":value,"unit":unit,"frequency":"annual","release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,"is_forecast":False,"source":"IMF WEO DataMapper API v2","source_url":url,"source_payload_hash":digest,"quality_status":"PROVISIONAL","metadata":{"indicator":indicator,"country_name":country,"forecast_excluded_after":completed_year,"pit_status":"FETCH_VINTAGE_ONLY","source_tier":"C"}})
        except Exception as exc: errors.append(f"{indicator}:{str(exc)[:120]}")
    return _persist_official_run("IMF WEO DataMapper",registry,observations,errors)

def collect_oecd_policy_rates():
    registry=[]; observations=[]; errors=[]; fetched=_now()
    for iso3,country in G20_COUNTRIES.items():
        key=f"{iso3}.M.IRSTCI.PA._Z._Z._Z._Z.N"
        url=f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK/{key}?startPeriod=2000-01&dimensionAtObservation=AllDimensions&format=csvfile"
        series_ids=[f"oecd_{iso3.lower()}_policy_rate"] + (["policy_rate"] if iso3 == "IND" else [])
        for series_id in series_ids:
            registry.append({"series_id":series_id,"country_code":iso3,"domain":"monetary","label":"Policy Rate","unit":"%","frequency":"monthly","primary_source":"OECD","source_url":url,"source_series_id":"DF_FINMARK:IRSTCI","license_class":"PUBLIC_OFFICIAL","refresh_policy":"ON_RELEASE","active":True,"metadata":{"country_name":country,"connector":"oecd_sdmx","ingestion_status":"CONNECTED"},"updated_at":fetched.isoformat()})
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0","Accept":"text/csv"})
            with _urlopen(req,timeout=30) as response: raw=response.read()
            digest=hashlib.sha256(raw).hexdigest(); accepted=0
            for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
                if row.get("MEASURE")!="IRSTCI" or not row.get("OBS_VALUE"): continue
                period=str(row.get("TIME_PERIOD") or "")
                if len(period)<7: continue
                for series_id in series_ids:
                    observations.append({"series_id":series_id,"country_code":iso3,"period_date":f"{period[:7]}-01","value_numeric":row.get("OBS_VALUE"),"unit":"%","frequency":"monthly","release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,"is_forecast":False,"source":"OECD SDMX API","source_url":url,"source_payload_hash":digest,"quality_status":"PROVISIONAL","metadata":{"measure":"IRSTCI","country_name":country,"time_period":period,"pit_status":"FETCH_VINTAGE_ONLY","source_tier":"C"}}); accepted+=1
            if not accepted: errors.append(f"policy_rate:{iso3}:missing")
        except Exception as exc: errors.append(f"policy_rate:{iso3}:{str(exc)[:120]}")
    return _persist_official_run("OECD SDMX",registry,observations,errors)


def _sdmx_period_end(period):
    value=str(period or "")
    quarter=re.fullmatch(r"(\d{4})-Q([1-4])",value)
    if quarter:
        year=int(quarter.group(1)); month=int(quarter.group(2))*3
        return f"{year:04d}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}"
    month=re.fullmatch(r"(\d{4})-(\d{2})",value)
    if month:
        year=int(month.group(1)); number=int(month.group(2))
        return f"{year:04d}-{number:02d}-{calendar.monthrange(year,number)[1]:02d}"
    return f"{value[:4]}-12-31" if value[:4].isdigit() else None


def collect_bis_india():
    """Collect explicitly mapped India Core 50 series from the official BIS SDMX API."""
    fetched=_now(); registry=[]; observations=[]; errors=[]
    for series_id,spec in BIS_INDIA_SERIES.items():
        url=f"https://stats.bis.org/api/v1/data/{spec['flow']}/{spec['key']}/all?startPeriod=2000-01"
        registry.append({"series_id":series_id,"country_code":"IND","domain":next(row[1] for row in CORE_50 if row[0] == series_id),"label":spec["label"],"unit":spec["unit"],"frequency":spec["frequency"],"primary_source":"Bank for International Settlements","source_url":url,"source_series_id":f"{spec['flow']}:{spec['key']}","license_class":"PUBLIC_OFFICIAL","refresh_policy":"ON_RELEASE","active":True,"metadata":{"connector":"bis_sdmx","ingestion_status":"CONNECTED","source_tier":"B"},"updated_at":fetched.isoformat()})
        try:
            request=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0","Accept":"application/vnd.sdmx.structurespecificdata+xml;version=2.1"})
            with _urlopen(request,timeout=35) as response: raw=response.read()
            digest=hashlib.sha256(raw).hexdigest(); accepted=0
            for match in re.finditer(rb'<Obs\b[^>]*\bTIME_PERIOD="([^"]+)"[^>]*\bOBS_VALUE="([^"]+)"',raw):
                period=match.group(1).decode(); period_date=_sdmx_period_end(period)
                if not period_date: continue
                try: value=float(match.group(2))
                except ValueError: continue
                observations.append({"series_id":series_id,"country_code":"IND","period_date":period_date,"value_numeric":value,"unit":spec["unit"],"frequency":spec["frequency"],"release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,"is_forecast":False,"source":"BIS SDMX API","source_url":url,"source_payload_hash":digest,"quality_status":"PROVISIONAL","metadata":{"flow":spec["flow"],"key":spec["key"],"time_period":period,"pit_status":"FETCH_VINTAGE_ONLY","source_tier":"B"}}); accepted+=1
            if not accepted: errors.append(f"{series_id}:no_observations")
        except Exception as exc: errors.append(f"{series_id}:{type(exc).__name__}:{str(exc)[:100]}")
    return _persist_official_run("BIS India SDMX",registry,observations,errors)


def collect_yahoo_macro_market():
    """Collect bounded market history for Core 50 gaps; never acts as official macro evidence."""
    observations=[]; errors=[]; fetched=_now()
    for series_id, spec in YAHOO_MACRO_MARKET_SERIES.items():
        symbol=spec["symbol"]
        try:
            has_history=bool(_rest("macro_public_observations",query=f"?select=id&series_id=eq.{series_id}&limit=1"))
        except Exception:
            has_history=False
        history_range="5d" if has_history else "2y"
        url=f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol, safe='')}?interval=1d&range={history_range}"
        try:
            request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 AGI-Macro-Intelligence/1.0","Accept":"application/json"})
            with _urlopen(request,timeout=25) as response: raw=response.read()
            payload=json.loads(raw); result=(((payload.get("chart") or {}).get("result") or [None])[0] or {})
            timestamps=result.get("timestamp") or []
            quote=((((result.get("indicators") or {}).get("quote") or [{}])[0]) or {})
            closes=quote.get("close") or []
            digest=hashlib.sha256(raw).hexdigest(); accepted=0
            for timestamp,value in zip(timestamps,closes):
                if value is None: continue
                observed_at=datetime.fromtimestamp(int(timestamp),tz=timezone.utc)
                observations.append({
                    "series_id":series_id,"country_code":spec["country"],"period_date":observed_at.date().isoformat(),
                    "value_numeric":value,"unit":spec["unit"],"frequency":"daily","release_date":fetched.isoformat(),
                    "available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,
                    "is_forecast":False,"source":"Yahoo Finance Chart API","source_url":url,"source_payload_hash":digest,
                    "quality_status":"PROVISIONAL","metadata":{"symbol":symbol,"market_timestamp":observed_at.isoformat(),
                    "pit_status":"FETCH_VINTAGE_ONLY","source_tier":"D","history_range":history_range,
                    "evidence_role":"MARKET_REFERENCE_NOT_OFFICIAL_MACRO"},
                }); accepted+=1
            if not accepted: errors.append(f"{series_id}:{symbol}:no_observations")
        except Exception as exc: errors.append(f"{series_id}:{symbol}:{str(exc)[:120]}")
    return _persist_official_run("Yahoo Finance Macro Market",[],observations,errors)


def _fmp_get(path, params=None):
    key=(os.getenv("FMP_API_KEY") or "").strip()
    if not key: raise RuntimeError("fmp_api_key_missing")
    query={**(params or {}),"apikey":key}
    url=f"https://financialmodelingprep.com/stable/{path}?{urllib.parse.urlencode(query)}"
    public_url=f"https://financialmodelingprep.com/stable/{path}"
    if params: public_url += f"?{urllib.parse.urlencode(params)}"
    request=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0","Accept":"application/json"})
    with _urlopen(request,timeout=30) as response: raw=response.read()
    payload=json.loads(raw)
    if isinstance(payload,dict) and payload.get("Error Message"): raise RuntimeError(str(payload["Error Message"])[:160])
    return payload,hashlib.sha256(raw).hexdigest(),public_url


def _fmp_period(event, released_at):
    """Best-effort period end from event suffix; otherwise use release date."""
    text=str(event or "")
    month_match=re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",text,re.I)
    quarter_match=re.search(r"\bQ([1-4])\b",text,re.I)
    year_match=re.search(r"\b(20\d{2})\b",text)
    year=int(year_match.group(1)) if year_match else released_at.year
    if month_match:
        month=list(calendar.month_abbr).index(month_match.group(1).title()[:3])
        return f"{year:04d}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}"
    if quarter_match:
        month=int(quarter_match.group(1))*3
        return f"{year:04d}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}"
    return released_at.date().isoformat()


def _fmp_event_series(event):
    for pattern,series_id in FMP_INDIA_EVENT_PATTERNS:
        if pattern.search(str(event or "")): return series_id
    return None


def collect_fmp_economics():
    """FMP vendor data: India releases plus separately-labelled US/global context."""
    if not _truthy("MIE_FMP_ENABLED","true") or not (os.getenv("FMP_API_KEY") or "").strip():
        return {"ok":True,"source":"FMP Economics","status":"DISABLED","accepted":0,"errors":[]}
    fetched=_now(); start=(fetched.date()-timedelta(days=89)).isoformat(); end=fetched.date().isoformat()
    registry=[]; observations=[]; errors=[]
    def add(series_id,country,domain,label,unit,frequency,date,value,source_url,digest,metadata):
        registry.append({"series_id":series_id,"country_code":country,"domain":domain,"label":label,"unit":unit,"frequency":frequency,
            "primary_source":"Financial Modeling Prep","source_url":source_url,"source_series_id":series_id,"license_class":"VENDOR_SECONDARY",
            "refresh_policy":"DAILY","active":True,"metadata":{"connector":"fmp_economics","ingestion_status":"CONNECTED","source_tier":"C"},"updated_at":fetched.isoformat()})
        observations.append({"series_id":series_id,"country_code":country,"period_date":date,"value_numeric":value,"unit":unit,"frequency":frequency,
            "release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,
            "is_forecast":False,"source":"Financial Modeling Prep stable API","source_url":source_url,"source_payload_hash":digest,
            "quality_status":"PROVISIONAL","metadata":{"connector":"fmp_economics","pit_status":"FETCH_VINTAGE_ONLY","source_tier":"C",**metadata}})
    try:
        payload,digest,url=_fmp_get("treasury-rates",{"from":start,"to":end})
        for row in payload if isinstance(payload,list) else []:
            date=str(row.get("date") or "")
            for field in ("month1","month2","month3","month6","year1","year2","year3","year5","year7","year10","year20","year30"):
                if row.get(field) is not None:
                    add(f"fmp_us_treasury_{field}","USA","monetary",f"US Treasury {field}","%","daily",date,row[field],url,digest,{"fmp_field":field,"evidence_role":"US_REFERENCE_NOT_INDIA_YIELD"})
    except Exception as exc: errors.append(f"treasury:{type(exc).__name__}:{str(exc)[:100]}")
    for name in FMP_US_INDICATORS:
        try:
            payload,digest,url=_fmp_get("economic-indicators",{"name":name,"from":start,"to":end})
            for row in payload if isinstance(payload,list) else []:
                if row.get("value") is not None and row.get("date"):
                    add(f"fmp_us_{name.lower()}","USA","global",f"US {name}",None,"as_reported",str(row["date"])[:10],row["value"],url,digest,{"fmp_name":name,"evidence_role":"US_MACRO_REFERENCE"})
        except Exception as exc: errors.append(f"indicator:{name}:{type(exc).__name__}:{str(exc)[:80]}")
    try:
        payload,digest,url=_fmp_get("economic-calendar",{"country":"IN","from":start,"to":end})
        catalogue={row[0]:row for row in CORE_50}
        for row in payload if isinstance(payload,list) else []:
            series_id=_fmp_event_series(row.get("event")); actual=row.get("actual")
            if not series_id or actual is None or series_id not in catalogue: continue
            released=datetime.fromisoformat(str(row.get("date") or "").replace("Z","+00:00"))
            _sid,domain,label,frequency=catalogue[series_id]
            add(series_id,"IND",domain,label,row.get("unit"),frequency,_fmp_period(row.get("event"),released),actual,url,digest,
                {"event":row.get("event"),"previous":row.get("previous"),"estimate":row.get("estimate"),"impact":row.get("impact"),"release_timestamp":str(row.get("date")),"trust_status":"PROPOSED"})
    except Exception as exc: errors.append(f"calendar:{type(exc).__name__}:{str(exc)[:100]}")
    try:
        payload,digest,url=_fmp_get("market-risk-premium")
        india=next((row for row in payload if isinstance(row,dict) and str(row.get("country") or "").lower()=="india"),None) if isinstance(payload,list) else None
        if india:
            for field,label in (("countryRiskPremium","India Country Risk Premium"),("totalEquityRiskPremium","India Total Equity Risk Premium")):
                if india.get(field) is not None: add(f"fmp_india_{field.lower()}","IND","valuation",label,"%","snapshot",fetched.date().isoformat(),india[field],url,digest,{"fmp_field":field,"evidence_role":"VALUATION_CONTEXT_NOT_CORE_50"})
    except Exception as exc: errors.append(f"risk_premium:{type(exc).__name__}:{str(exc)[:100]}")
    registry=list({row["series_id"]:row for row in registry}.values())
    observations=list({(row["series_id"],row["country_code"],row["period_date"],row["vintage_date"],row["revision_number"]):row for row in observations}.values())
    return _persist_official_run("FMP Economics",registry,observations,errors)


def _truthy(name, default="false"):
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _missing_india_series():
    """Return registered Core 50 series with no persisted India/global value."""
    ids=",".join(row[0] for row in CORE_50)
    rows = _rest(
        "macro_public_observations",
        query=f"?select=series_id&series_id=in.({ids})&country_code=in.(IND,WLD)&limit=10000",
    ) or []
    observed = {str(row.get("series_id") or "") for row in rows}
    return [row for row in CORE_50 if row[0] not in observed and row[3] != "derived"]


def _web_semantically_matches(series_id, extracted):
    required=WEB_REQUIRED_TERMS.get(series_id)
    if not required: return True
    title=str(extracted.get("source_title") or "").lower()
    quote=str(extracted.get("quote") or "").lower()
    evidence=f"{title} {quote}"
    if series_id == "gdp_qoq":
        # India GDP releases commonly mix FY, YoY-quarter and sequential data.
        # Never accept an annual-labelled source or a YoY quote as QoQ.
        forbidden=("annual gross domestic product","annual gdp","year-on-year","year on year","y-o-y","yoy")
        if any(term in title for term in ("annual gross domestic product","annual gdp")):
            return False
        if any(term in quote for term in forbidden):
            return False
    return any(term in evidence for term in required)


def _purge_invalid_web_candidates():
    """Remove proposed rows that fail deterministic series-specific semantics."""
    rows=_rest(
        "macro_public_observations",
        query="?select=id,series_id,source,metadata&country_code=eq.IND&limit=10000",
    ) or []
    purged=[]
    for row in rows:
        metadata=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}
        if metadata.get("connector") != "exa_web_fallback": continue
        extracted={"source_title":row.get("source"),"quote":metadata.get("quote")}
        if _web_semantically_matches(str(row.get("series_id") or ""),extracted): continue
        row_id=row.get("id")
        if row_id:
            _rest("macro_public_observations",method="DELETE",query=f"?id=eq.{urllib.parse.quote(str(row_id))}",prefer="return=minimal")
            purged.append(str(row_id))
    return purged


def _exa_macro_search(label, domain, frequency):
    key=(os.getenv("EXA_API_KEY") or "").strip()
    if not key: raise RuntimeError("exa_api_key_missing")
    query=(
        f"India latest official {label} {frequency} value release date "
        f"{domain} statistics"
    )
    payload={
        "query":query,"numResults":5,"type":"auto","includeDomains":list(INDIA_MACRO_SOURCE_DOMAINS),
        "contents":{"text":{"maxCharacters":3500}},
    }
    request=urllib.request.Request(
        "https://api.exa.ai/search",data=json.dumps(payload).encode(),method="POST",
        headers={"x-api-key":key,"Content-Type":"application/json","User-Agent":"AGI-Macro-Intelligence/1.0"},
    )
    with _urlopen(request,timeout=35) as response: raw=response.read()
    data=json.loads(raw); results=[]
    for item in data.get("results") or []:
        if not isinstance(item,dict): continue
        url=str(item.get("url") or "")
        hostname=(urllib.parse.urlparse(url).hostname or "").lower()
        if not any(hostname == host or hostname.endswith(f".{host}") for host in INDIA_MACRO_SOURCE_DOMAINS): continue
        results.append({"title":item.get("title"),"url":url,"published_date":item.get("publishedDate"),"text":str(item.get("text") or "")[:3500]})
    return results,query,hashlib.sha256(raw).hexdigest()


def _extract_macro_observation(series_id, label, frequency, results):
    """Use the configured model only to structure quoted webpage evidence."""
    key=(os.getenv("OPENAI_API_KEY") or "").strip()
    if not key: raise RuntimeError("openai_api_key_missing")
    model=(os.getenv("MIE_WEB_EXTRACT_MODEL") or "gpt-4.1-mini").strip()
    evidence=json.dumps(results,separators=(",",":"),ensure_ascii=True)
    prompt=(
        "Extract the latest completed-period numerical observation for the requested India macro series. "
        "Use only the supplied webpage evidence. Never estimate, calculate, or use a forecast. Return JSON only with keys: "
        "value (number or null), unit (string or null), period_date (YYYY-MM-DD or null), release_date "
        "(YYYY-MM-DD or null), source_url (one supplied URL or null), source_title (string or null), quote "
        "(short exact supporting text or null), confidence (0 to 1). If the value, period, unit, and supporting source "
        "are not explicit, return value null.\n"
        f"series_id={series_id}; label={label}; expected_frequency={frequency}; country=India\nEVIDENCE={evidence}"
    )
    payload={"model":model,"input":prompt,"temperature":0,"text":{"format":{"type":"json_object"}}}
    request=urllib.request.Request(
        "https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),method="POST",
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","User-Agent":"AGI-Macro-Intelligence/1.0"},
    )
    with _urlopen(request,timeout=45) as response: data=json.loads(response.read())
    text=""
    for item in data.get("output") or []:
        for content in item.get("content") or []:
            if content.get("type") == "output_text": text += str(content.get("text") or "")
    return json.loads(text or "{}"),model


def collect_web_macro_gaps():
    """Fill bounded Core 50 gaps from cited web pages as untrusted candidates."""
    if not _truthy("MIE_WEB_FALLBACK_ENABLED"):
        return {"ok":True,"source":"Exa Web Macro Fallback","status":"DISABLED","accepted":0,"errors":[]}
    purged=_purge_invalid_web_candidates()
    limit=max(1,min(int(os.getenv("MIE_WEB_FALLBACK_LIMIT","8")),20))
    observations=[]; errors=[]; fetched=_now()
    for series_id,domain,label,frequency in _missing_india_series()[:limit]:
        try:
            results,query,search_hash=_exa_macro_search(label,domain,frequency)
            if not results: errors.append(f"{series_id}:no_authoritative_results"); continue
            extracted,model=_extract_macro_observation(series_id,label,frequency,results)
            value=extracted.get("value"); source_url=str(extracted.get("source_url") or "")
            if value is None or not source_url or source_url not in {row["url"] for row in results}:
                errors.append(f"{series_id}:no_explicit_observation"); continue
            value=float(value)
            if not math.isfinite(value):
                errors.append(f"{series_id}:non_finite_value"); continue
            if float(extracted.get("confidence") or 0) < 0.75:
                errors.append(f"{series_id}:low_extraction_confidence"); continue
            if not _web_semantically_matches(series_id,extracted):
                errors.append(f"{series_id}:semantic_mismatch"); continue
            period=str(extracted.get("period_date") or "")
            release=str(extracted.get("release_date") or "")
            try:
                datetime.fromisoformat(period); datetime.fromisoformat(release)
            except ValueError:
                errors.append(f"{series_id}:date_missing"); continue
            observations.append({
                "series_id":series_id,"country_code":"IND","period_date":period,"value_numeric":value,
                "unit":extracted.get("unit"),"frequency":frequency,"release_date":f"{release}T00:00:00+00:00",
                "available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,
                "is_forecast":False,"source":extracted.get("source_title") or "Authoritative webpage via Exa",
                "source_url":source_url,"source_payload_hash":search_hash,"quality_status":"PROVISIONAL",
                "metadata":{"connector":"exa_web_fallback","query":query,"quote":extracted.get("quote"),
                    "extractor_model":model,"extractor_confidence":extracted.get("confidence"),
                    "pit_status":"FETCH_VINTAGE_ONLY","source_tier":"D","trust_status":"PROPOSED",
                    "evidence_role":"WEB_DISCOVERED_CANDIDATE_REQUIRES_VALIDATION"},
            })
        except Exception as exc: errors.append(f"{series_id}:{type(exc).__name__}:{str(exc)[:100]}")
    result=_persist_official_run("Exa Web Macro Fallback",[],observations,errors)
    result["purged_invalid_candidates"]=len(purged)
    return result

def source_status():
    return [
        {"source":"World Bank","status":"CONNECTED","collection":"LIVE_API"},
        {"source":"IMF","status":"DEPLOYMENT_BLOCKED","collection":"RENDER_EGRESS_HTTP_403; API_V2_VERIFIED_EXTERNALLY"},
        {"source":"OECD","status":"CONNECTED","collection":"LIVE_SDMX"},
        {"source":"Yahoo Finance","status":"CONNECTED","collection":"MARKET_REFERENCE_TIER_D"},
        {"source":"FMP Economics","status":"CONNECTED" if _truthy("MIE_FMP_ENABLED","true") and (os.getenv("FMP_API_KEY") or "").strip() else "DISABLED","collection":"VENDOR_ECONOMICS_TIER_C"},
        {"source":"Exa Web Fallback","status":"CONNECTED" if _truthy("MIE_WEB_FALLBACK_ENABLED") and (os.getenv("EXA_API_KEY") or "").strip() else "DISABLED","collection":"AUTHORITATIVE_WEB_DISCOVERY_TIER_D_PROPOSED"},
        {"source":"MoSPI","status":"CONFIGURATION_REQUIRED","collection":"API_ACCESS_TOKEN_REQUIRED"},
        {"source":"RBI","status":"MAPPING_REQUIRED","collection":"DBIE_ACCESS_PATH_REQUIRED"},
        {"source":"BIS","status":"CONNECTED","collection":"INDIA_CORE_SDMX_TIER_B"},
        {"source":"ILO","status":"MAPPING_REQUIRED","collection":"BULK_INDICATOR_KEYS_REQUIRED"},
        {"source":"UNCTAD","status":"MAPPING_REQUIRED","collection":"DATASET_KEYS_REQUIRED"},
        {"source":"Ministry of Commerce","status":"ADAPTER_REQUIRED","collection":"OFFICIAL_DOWNLOAD_NO_DOCUMENTED_API"},
    ]

def run_public_ingestion():
    def run_stage(label, collector):
        try:
            return collector()
        except Exception as exc:
            return {
                "ok": False,
                "source": label,
                "status": "FAILED",
                "accepted": 0,
                "errors": [f"{type(exc).__name__}: {str(exc)[:500]}"],
            }

    seeded = run_stage("Core 50 Registry", seed_registry)
    collectors = [
        run_stage("World Bank", collect_world_bank),
        run_stage("World Bank G20", collect_world_bank_g20),
        run_stage("IMF WEO DataMapper", collect_imf_g20),
        run_stage("OECD SDMX", collect_oecd_policy_rates),
        run_stage("BIS India SDMX", collect_bis_india),
        run_stage("Yahoo Finance Macro Market", collect_yahoo_macro_market),
        run_stage("FMP Economics", collect_fmp_economics),
        run_stage("Exa Web Macro Fallback", collect_web_macro_gaps),
    ]
    return {
        "ok": bool(seeded.get("ok") and all(item.get("ok") for item in collectors)),
        "registry": seeded,
        "collectors": collectors,
        "sources": source_status(),
    }
