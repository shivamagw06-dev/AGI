"""Durable public macro ingestion. Background runtime only; never called by page reads."""
from __future__ import annotations
import csv, hashlib, io, json, os, urllib.parse, urllib.request, uuid
from datetime import datetime, timezone
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

def _now(): return datetime.now(timezone.utc)

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

def _wb_fetch(country,indicator):
    url=f"https://api.worldbank.org/v2/country/{country.lower()}/indicator/{indicator}?format=json&per_page=100&mrv=25"; req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0"})
    with urllib.request.urlopen(req,timeout=25) as response: raw=response.read()
    payload=json.loads(raw); rows=payload[1] if isinstance(payload,list) and len(payload)>1 and isinstance(payload[1],list) else []
    return [row for row in rows if row.get("value") is not None],hashlib.sha256(raw).hexdigest(),url

def collect_world_bank():
    run_id=str(uuid.uuid4()); errors=[]; observations=[]
    _rest("macro_public_ingestion_runs",method="POST",rows={"run_id":run_id,"source":"World Bank","status":"RUNNING","started_at":_now().isoformat()},prefer="return=minimal")
    for series_id,(indicator,unit,country) in WORLD_BANK_SERIES.items():
        try:
            rows,payload_hash,url=_wb_fetch(country,indicator)
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
        url=f"https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}?format=json&per_page=5000&mrv=25"
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0"})
            with urllib.request.urlopen(req,timeout=30) as response: raw=response.read()
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
            with urllib.request.urlopen(req,timeout=35) as response: raw=response.read()
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
        series_id=f"oecd_{iso3.lower()}_policy_rate"
        registry.append({"series_id":series_id,"country_code":iso3,"domain":"monetary","label":"Policy Rate","unit":"%","frequency":"monthly","primary_source":"OECD","source_url":url,"source_series_id":"DF_FINMARK:IRSTCI","license_class":"PUBLIC_OFFICIAL","refresh_policy":"ON_RELEASE","active":True,"metadata":{"country_name":country,"connector":"oecd_sdmx","ingestion_status":"CONNECTED"},"updated_at":fetched.isoformat()})
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0","Accept":"text/csv"})
            with urllib.request.urlopen(req,timeout=30) as response: raw=response.read()
            digest=hashlib.sha256(raw).hexdigest(); accepted=0
            for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
                if row.get("MEASURE")!="IRSTCI" or not row.get("OBS_VALUE"): continue
                period=str(row.get("TIME_PERIOD") or "")
                if len(period)<7: continue
                observations.append({"series_id":series_id,"country_code":iso3,"period_date":f"{period[:7]}-01","value_numeric":row.get("OBS_VALUE"),"unit":"%","frequency":"monthly","release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,"is_forecast":False,"source":"OECD SDMX API","source_url":url,"source_payload_hash":digest,"quality_status":"PROVISIONAL","metadata":{"measure":"IRSTCI","country_name":country,"time_period":period,"pit_status":"FETCH_VINTAGE_ONLY","source_tier":"C"}}); accepted+=1
            if not accepted: errors.append(f"policy_rate:{iso3}:missing")
        except Exception as exc: errors.append(f"policy_rate:{iso3}:{str(exc)[:120]}")
    return _persist_official_run("OECD SDMX",registry,observations,errors)


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
            with urllib.request.urlopen(request,timeout=25) as response: raw=response.read()
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

def source_status():
    return [
        {"source":"World Bank","status":"CONNECTED","collection":"LIVE_API"},
        {"source":"IMF","status":"DEPLOYMENT_BLOCKED","collection":"RENDER_EGRESS_HTTP_403; API_V2_VERIFIED_EXTERNALLY"},
        {"source":"OECD","status":"CONNECTED","collection":"LIVE_SDMX"},
        {"source":"Yahoo Finance","status":"CONNECTED","collection":"MARKET_REFERENCE_TIER_D"},
        {"source":"MoSPI","status":"CONFIGURATION_REQUIRED","collection":"API_ACCESS_TOKEN_REQUIRED"},
        {"source":"RBI","status":"MAPPING_REQUIRED","collection":"DBIE_ACCESS_PATH_REQUIRED"},
        {"source":"BIS","status":"MAPPING_REQUIRED","collection":"SDMX_SERIES_KEYS_REQUIRED"},
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
        run_stage("Yahoo Finance Macro Market", collect_yahoo_macro_market),
    ]
    return {
        "ok": bool(seeded.get("ok") and all(item.get("ok") for item in collectors)),
        "registry": seeded,
        "collectors": collectors,
        "sources": source_status(),
    }
