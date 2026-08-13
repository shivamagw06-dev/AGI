"""Durable public macro ingestion. Background runtime only; never called by page reads."""
from __future__ import annotations
import hashlib, json, os, urllib.request, uuid
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
    url=f"https://api.worldbank.org/v2/country/{country.lower()}/indicator/{indicator}?format=json&per_page=12&mrv=6"; req=urllib.request.Request(url,headers={"User-Agent":"AGI-Macro-Intelligence/1.0"})
    with urllib.request.urlopen(req,timeout=25) as response: raw=response.read()
    payload=json.loads(raw); rows=payload[1] if isinstance(payload,list) and len(payload)>1 and isinstance(payload[1],list) else []
    return next((r for r in rows if r.get("value") is not None),None),hashlib.sha256(raw).hexdigest(),url

def collect_world_bank():
    run_id=str(uuid.uuid4()); errors=[]; observations=[]
    _rest("macro_public_ingestion_runs",method="POST",rows={"run_id":run_id,"source":"World Bank","status":"RUNNING","started_at":_now().isoformat()},prefer="return=minimal")
    for series_id,(indicator,unit,country) in WORLD_BANK_SERIES.items():
        try:
            row,payload_hash,url=_wb_fetch(country,indicator); period=str((row or {}).get("date") or "")
            if not row or not period[:4].isdigit(): errors.append(f"{series_id}:no_observation"); continue
            fetched=_now(); observations.append({"series_id":series_id,"country_code":country,"period_date":f"{period[:4]}-12-31","value_numeric":row.get("value"),"unit":unit,"frequency":"annual","release_date":fetched.isoformat(),"available_at":fetched.isoformat(),"vintage_date":fetched.date().isoformat(),"revision_number":0,"is_forecast":False,"source":"World Bank Indicators API","source_url":url,"source_payload_hash":payload_hash,"quality_status":"PROVISIONAL","metadata":{"indicator":indicator,"country_label":(row.get("country") or {}).get("value")}})
        except Exception as exc: errors.append(f"{series_id}:{str(exc)[:100]}")
    if observations:_rest("macro_public_observations",method="POST",rows=observations,query="?on_conflict=series_id,country_code,period_date,vintage_date,revision_number",prefer="resolution=merge-duplicates,return=minimal")
    status="COMPLETE" if observations and not errors else ("COMPLETE_WITH_WARNINGS" if observations else "FAILED")
    _rest("macro_public_ingestion_runs",method="PATCH",rows={"status":status,"completed_at":_now().isoformat(),"rows_received":len(WORLD_BANK_SERIES),"rows_accepted":len(observations),"rows_quarantined":len(errors),"error":";".join(errors)[:1000] or None,"receipt":{"series":[r["series_id"] for r in observations],"errors":errors}},query=f"?run_id=eq.{run_id}",prefer="return=minimal")
    return {"ok":bool(observations),"source":"World Bank","run_id":run_id,"status":status,"accepted":len(observations),"errors":errors}

def source_status():
    return [{"source":s,"status":"CONNECTED" if s=="World Bank" else "REGISTERED","collection":"LIVE_API" if s=="World Bank" else "AWAITING_VERIFIED_CONNECTOR"} for s in ("RBI","MoSPI","Ministry of Commerce","World Bank","IMF","BIS","OECD")]

def run_public_ingestion():
    seeded=seed_registry(); wb=collect_world_bank(); return {"ok":bool(seeded.get("ok") and wb.get("ok")),"registry":seeded,"collectors":[wb],"sources":source_status()}
