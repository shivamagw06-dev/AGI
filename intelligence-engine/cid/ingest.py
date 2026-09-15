"""Ingest verified LEO evidence into the Company Intelligence Dossier."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cid.coverage import compute_coverage
from cid.identity import resolve_identity
from cid.schema import EVIDENCE_TO_CATEGORY, empty_dossier
from cid.store import get_cid_store


DOC_BUCKETS = {
    "annual_reports": "annual_reports",
    "quarterly_results": "quarterly_results",
    "investor_presentations": "investor_presentations",
    "conference_calls": "conference_call_transcripts",
}


def ingest_leo_evidence(
    ticker: str | None,
    evidence_objects: list[dict[str, Any]],
    *,
    plan: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    forecast_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Normalised + verified LEO evidence → update living CID.
    Never overwrites evidence_timeline history.
    """
    t = (ticker or (plan or {}).get("ticker") or "").upper() or None
    if not t:
        return {"enabled": False, "reason": "no_ticker"}

    store = get_cid_store()
    dossier = store.get(t) or empty_dossier(t, company=(plan or {}).get("company"))
    now = datetime.now(timezone.utc).isoformat()
    if not dossier.get("created_at"):
        dossier["created_at"] = now

    # Identity
    ident = resolve_identity(t, query=(plan or {}).get("query"))
    dossier["identity"] = {**(dossier.get("identity") or {}), **{k: v for k, v in ident.items() if v}}
    if ident.get("sector_id"):
        dossier["identity"]["sector_id"] = ident["sector_id"]

    # Attach SIF framework + sector KPIs
    _attach_sif(dossier, t, sif_pkg=sif_pkg, plan=plan)

    # Attach Finance Academy links
    if isinstance(finance_academy, dict) and finance_academy:
        _attach_academy(dossier, finance_academy)

    # Soft valuation / forecast packs
    if isinstance(valuation_pack, dict) and valuation_pack:
        _attach_valuation(dossier, valuation_pack, now)
    if isinstance(forecast_pack, dict) and forecast_pack:
        _attach_forecasts(dossier, forecast_pack, now)

    # Ingest each evidence object
    seen_timeline_ids = {e.get("evidence_id") for e in (dossier.get("evidence_timeline") or []) if e.get("evidence_id")}
    for obj in evidence_objects or []:
        if not isinstance(obj, dict):
            continue
        eid = obj.get("evidence_id")
        etype = obj.get("evidence_type") or "news"
        cat = EVIDENCE_TO_CATEGORY.get(etype)

        # Timeline — append only, never overwrite
        if eid and eid not in seen_timeline_ids:
            dossier.setdefault("evidence_timeline", []).append(
                {
                    "at": now,
                    "evidence_id": eid,
                    "evidence_type": etype,
                    "category": cat,
                    "title": obj.get("title"),
                    "source_id": obj.get("source_id"),
                    "confidence": obj.get("confidence"),
                    "verification_status": obj.get("verification_status"),
                    "value_text": (obj.get("value_text") or "")[:400],
                    "url": obj.get("url"),
                }
            )
            seen_timeline_ids.add(eid)

        entry = {
            "evidence_id": eid,
            "title": obj.get("title"),
            "source_id": obj.get("source_id"),
            "published": obj.get("published") or now,
            "confidence": obj.get("confidence"),
            "verification_status": obj.get("verification_status"),
            "url": obj.get("url"),
            "extracted_facts": obj.get("extracted_facts") or [],
            "version": obj.get("version") or 1,
        }

        if cat in DOC_BUCKETS:
            bucket = DOC_BUCKETS[cat]
            docs = dossier.setdefault("documents", {})
            arr = docs.setdefault(bucket, [])
            if not any(x.get("evidence_id") == eid for x in arr):
                arr.append(entry)
                docs[bucket] = arr[-60:]
            if cat == "annual_reports":
                dossier["latest_filing"] = entry
            if cat == "quarterly_results":
                dossier["latest_filing"] = entry
                _append_fs_version(dossier, entry, period="quarterly", now=now)
            if cat == "investor_presentations":
                dossier["latest_presentation"] = entry
            if cat == "conference_calls":
                pass
            if cat == "annual_reports":
                _append_fs_version(dossier, entry, period="annual", now=now)

        if cat == "corporate_announcements" or etype == "corporate_announcement":
            anns = dossier.setdefault("announcements", [])
            if not any(x.get("evidence_id") == eid for x in anns):
                classified = _classify_announcement(obj)
                anns.append({**entry, **classified})
                dossier["announcements"] = anns[-120:]
                dossier["latest_announcement"] = anns[-1]
                _update_catalysts_from_announcement(dossier, classified, entry)

        if etype == "market_data":
            _update_market_data(dossier, obj, now)
        if etype == "valuation_metrics":
            _update_valuation_from_evidence(dossier, obj, now)
        if etype == "financial_statements":
            _append_fs_version(dossier, entry, period="quarterly", now=now)
            docs = dossier.setdefault("documents", {})
            arr = docs.setdefault("quarterly_results", [])
            if not any(x.get("evidence_id") == eid for x in arr):
                arr.append(entry)
        if etype == "sector_kpis":
            # already attached via SIF; merge fact checklist
            facts = obj.get("extracted_facts") or []
            kpi_vals = dossier.setdefault("sector_kpis", {}).setdefault("observed", {})
            for f in facts:
                if isinstance(f, dict) and f.get("field"):
                    kpi_vals[str(f["field"])] = f.get("value_text")

        # Soft financial metrics from extracted facts
        _update_metrics_from_facts(dossier, obj)

        # Soft risk classification from text
        _soft_risks_from_text(dossier, obj)

    # Cap timeline (keep history, bound memory)
    dossier["evidence_timeline"] = (dossier.get("evidence_timeline") or [])[-500:]

    # Recompute coverage
    cov = compute_coverage(dossier)
    dossier["coverage"] = cov["coverage"]
    dossier["coverage_score"] = cov["coverage_score"]
    dossier["coverage_grade"] = cov["coverage_grade"]
    dossier["missing_evidence"] = cov["missing_evidence"]
    dossier["updated_at"] = now

    return store.put(dossier)


def ensure_dossier(ticker: str, *, query: str | None = None) -> dict[str, Any]:
    """Ensure a dossier exists and is identity/SIF hydrated even without new evidence."""
    t = (ticker or "").upper()
    store = get_cid_store()
    existing = store.get(t)
    if existing and (existing.get("evidence_timeline") or existing.get("sector_kpis")):
        # Refresh SIF/identity lightly
        _attach_sif(existing, t)
        ident = resolve_identity(t, query=query)
        existing["identity"] = {**(existing.get("identity") or {}), **{k: v for k, v in ident.items() if v}}
        cov = compute_coverage(existing)
        existing.update(
            {
                "coverage": cov["coverage"],
                "coverage_score": cov["coverage_score"],
                "coverage_grade": cov["coverage_grade"],
                "missing_evidence": cov["missing_evidence"],
            }
        )
        return store.put(existing)
    # Create shell + attach framework
    d = store.ensure(t)
    ident = resolve_identity(t, query=query)
    d["identity"] = {**(d.get("identity") or {}), **{k: v for k, v in ident.items() if v}}
    _attach_sif(d, t)
    cov = compute_coverage(d)
    d.update(
        {
            "coverage": cov["coverage"],
            "coverage_score": cov["coverage_score"],
            "coverage_grade": cov["coverage_grade"],
            "missing_evidence": cov["missing_evidence"],
        }
    )
    return store.put(d)


def _attach_sif(
    dossier: dict[str, Any],
    ticker: str,
    *,
    sif_pkg: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> None:
    sector_id = None
    fw_dict: dict[str, Any] = {}
    if isinstance(sif_pkg, dict) and sif_pkg.get("sector_id"):
        sector_id = sif_pkg.get("sector_id")
        fw_dict = {
            "sector_id": sector_id,
            "sector_name": sif_pkg.get("sector_name"),
            "framework_version": sif_pkg.get("framework_version") or sif_pkg.get("sif_version"),
            "priority_metrics": sif_pkg.get("priority_metrics") or [],
            "valuation_framework": sif_pkg.get("valuation_framework"),
        }
    else:
        try:
            from sif.detection import detect_sector
            from sif.frameworks import get_framework

            det = detect_sector(ticker, ticker)
            sector_id = det.get("sector_id") or (plan or {}).get("sector_id")
            fw = get_framework(sector_id)
            if fw:
                fw_dict = {
                    "sector_id": fw.sector_id,
                    "sector_name": fw.name,
                    "framework_version": fw.version,
                    "priority_metrics": list(fw.priority_metrics or []),
                    "required_kpis": list(getattr(fw, "required_kpis", None) or fw.priority_metrics or []),
                    "valuation_methodology": list(fw.valuation_methodology or []),
                    "preferred_multiples": list(fw.preferred_multiples or []),
                }
        except Exception:
            return

    if not fw_dict:
        return
    dossier["sector_framework"] = fw_dict
    dossier["identity"]["sector_id"] = fw_dict.get("sector_id")
    dossier["identity"]["sector"] = dossier["identity"].get("sector") or fw_dict.get("sector_name")
    kpis = dossier.setdefault("sector_kpis", {})
    kpis["sector_id"] = fw_dict.get("sector_id")
    kpis["framework_version"] = fw_dict.get("framework_version")
    kpis["priority_metrics"] = fw_dict.get("priority_metrics") or fw_dict.get("required_kpis") or []
    kpis["required_kpis"] = fw_dict.get("required_kpis") or kpis["priority_metrics"]
    # Valuation methodology preference from SIF
    val = dossier.setdefault("valuation", {})
    if fw_dict.get("valuation_methodology") or fw_dict.get("valuation_framework"):
        methods = fw_dict.get("valuation_methodology")
        if not methods and isinstance(fw_dict.get("valuation_framework"), dict):
            methods = fw_dict["valuation_framework"].get("methodology") or []
        if methods:
            val["preferred_methodology"] = list(methods)[:6]


def _attach_academy(dossier: dict[str, Any], academy: dict[str, Any]) -> None:
    fa = dossier.setdefault("finance_academy", {})
    concept_ids = list(academy.get("concept_ids") or [])
    fa["active_concepts"] = concept_ids[:24]
    fa["courses"] = list(academy.get("courses") or [])[:12]
    # Bucket by course tags when present
    economics, accounting, acf, books = [], [], [], []
    for c in academy.get("concepts") or []:
        if not isinstance(c, dict):
            continue
        cid = c.get("concept_id") or c.get("id")
        tags = " ".join(str(x) for x in (c.get("tags") or [])).lower()
        course = str(c.get("course_id") or c.get("course") or "").lower()
        if "book" in course or "book" in tags:
            books.append(cid)
        elif "econ" in course or "econ" in tags:
            economics.append(cid)
        elif "account" in course or "account" in tags:
            accounting.append(cid)
        else:
            acf.append(cid)
    if economics:
        fa["economics"] = economics[:16]
    if accounting:
        fa["accounting"] = accounting[:16]
    if acf or concept_ids:
        fa["corporate_finance"] = (acf or concept_ids)[:16]
    if books:
        fa["books"] = books[:16]
    # Soft frameworks / formulas from Academy Books package
    books_pkg = academy.get("academy_books") if isinstance(academy.get("academy_books"), dict) else {}
    if books_pkg.get("frameworks") and not fa.get("frameworks"):
        fa["frameworks"] = books_pkg.get("frameworks")[:8]
    if books_pkg.get("formulas") and not fa.get("formulas"):
        fa["formulas"] = books_pkg.get("formulas")[:8]


def _attach_valuation(dossier: dict[str, Any], pack: dict[str, Any], now: str) -> None:
    val = dossier.setdefault("valuation", {})
    current = {}
    if pack.get("latest_valuation"):
        current = pack.get("latest_valuation") if isinstance(pack.get("latest_valuation"), dict) else {"raw": pack.get("latest_valuation")}
    elif pack.get("company"):
        current = pack.get("company") if isinstance(pack.get("company"), dict) else {}
    if current:
        val["current"] = current
        hist = val.setdefault("historical", [])
        hist.append({"at": now, "valuation": current})
        val["historical"] = hist[-40:]
    if pack.get("assumptions"):
        val["sensitivity"] = pack.get("assumptions") if isinstance(pack.get("assumptions"), dict) else {"assumptions": pack.get("assumptions")}
    if pack.get("scenarios"):
        val["scenarios"] = list(pack.get("scenarios") or [])[:12]
    mos = pack.get("margin_of_safety") or (current or {}).get("margin_of_safety")
    if mos is not None:
        val["margin_of_safety"] = mos
    if pack.get("confidence") is not None:
        val["confidence"] = pack.get("confidence")


def _attach_forecasts(dossier: dict[str, Any], pack: dict[str, Any], now: str) -> None:
    fc = dossier.setdefault("forecasts", {})
    for key, dest in (
        ("revenue", "revenue"),
        ("eps", "eps"),
        ("margin", "margin"),
        ("cash_flow", "cash_flow"),
        ("roic", "roic"),
    ):
        if pack.get(key) is not None:
            arr = fc.setdefault(dest, [])
            arr.append({"at": now, "value": pack.get(key)})
            fc[dest] = arr[-40:]
    if pack.get("accuracy"):
        fc["accuracy"] = pack.get("accuracy")
    if pack.get("current_predictions"):
        hist = fc.setdefault("historical", [])
        hist.append({"at": now, "predictions": pack.get("current_predictions")})
        fc["historical"] = hist[-40:]


def _append_fs_version(dossier: dict[str, Any], entry: dict[str, Any], *, period: str, now: str) -> None:
    fs = dossier.setdefault("financial_statements", {})
    versions = fs.setdefault("versions", [])
    versions.append({**entry, "period": period, "recorded_at": now})
    fs["versions"] = versions[-80:]
    # Placeholder statement rows for annual/quarterly continuity
    for stmt in ("income_statement", "balance_sheet", "cash_flow"):
        block = fs.setdefault(stmt, {"annual": [], "quarterly": []})
        arr = block.setdefault(period, [])
        if not any(x.get("evidence_id") == entry.get("evidence_id") for x in arr):
            arr.append({"evidence_id": entry.get("evidence_id"), "title": entry.get("title"), "at": now})
            block[period] = arr[-40:]


def _classify_announcement(obj: dict[str, Any]) -> dict[str, Any]:
    blob = " ".join(
        str(x)
        for x in (
            obj.get("title"),
            obj.get("value_text"),
            obj.get("evidence_type"),
            (obj.get("raw") or {}).get("doc_type") if isinstance(obj.get("raw"), dict) else "",
        )
    ).lower()
    kind = "general"
    for label, keys in (
        ("board_meeting", ("board",)),
        ("results", ("result", "quarter", "annual", "earning")),
        ("dividend", ("dividend",)),
        ("buyback", ("buyback", "buy-back")),
        ("split", ("split",)),
        ("bonus", ("bonus",)),
        ("rights", ("rights issue", "rights")),
        ("acquisition", ("acquisition", "merger", "amalgamation")),
        ("management_change", ("appoint", "resign", "ceo", "cfo", "director")),
        ("shareholding", ("shareholding", "promoter")),
        ("bulk_deal", ("bulk deal",)),
        ("block_deal", ("block deal",)),
    ):
        if any(k in blob for k in keys):
            kind = label
            break
    return {"announcement_kind": kind}


def _update_catalysts_from_announcement(dossier: dict[str, Any], classified: dict[str, Any], entry: dict[str, Any]) -> None:
    cats = dossier.setdefault("catalysts", {})
    kind = classified.get("announcement_kind")
    item = {"title": entry.get("title"), "kind": kind, "at": entry.get("published")}
    if kind in {"results", "dividend", "buyback", "acquisition"}:
        cats.setdefault("positive", []).append(item)
        cats["positive"] = cats["positive"][-30:]
    if kind in {"management_change"}:
        cats.setdefault("upcoming_events", []).append(item)
        cats["upcoming_events"] = cats["upcoming_events"][-30:]
    if kind == "results":
        cats.setdefault("quarterly_results", []).append(item)
        cats["quarterly_results"] = cats["quarterly_results"][-20:]


def _update_market_data(dossier: dict[str, Any], obj: dict[str, Any], now: str) -> None:
    md = dossier.setdefault("market_data", {})
    for f in obj.get("extracted_facts") or []:
        if not isinstance(f, dict):
            continue
        field = str(f.get("field") or "").lower()
        val = f.get("value_text") or f.get("value")
        if "price" in field or field == "ltp":
            md["current_price"] = val
        elif "market_cap" in field or field == "mcap":
            md["market_cap"] = val
        elif "volume" in field:
            md["volume"] = val
        elif "high" in field:
            md["fifty_two_week_high"] = val
        elif "low" in field:
            md["fifty_two_week_low"] = val
        elif "beta" in field:
            md["beta"] = val
        elif "yield" in field:
            md["dividend_yield"] = val
        elif any(x in field for x in ("pe", "pb", "ev", "multiple")):
            md.setdefault("valuation_multiples", {})[field] = val
    md["updated_at"] = now
    # Keep a light historical print
    if md.get("current_price") is not None:
        hist = md.setdefault("historical_prices", [])
        hist.append({"at": now, "price": md.get("current_price")})
        md["historical_prices"] = hist[-120:]


def _update_valuation_from_evidence(dossier: dict[str, Any], obj: dict[str, Any], now: str) -> None:
    val = dossier.setdefault("valuation", {})
    current = dict(val.get("current") or {})
    for f in obj.get("extracted_facts") or []:
        if isinstance(f, dict) and f.get("field"):
            current[str(f["field"])] = f.get("value_text")
    if current:
        val["current"] = current
        hist = val.setdefault("historical", [])
        hist.append({"at": now, "valuation": current, "source": obj.get("source_id")})
        val["historical"] = hist[-40:]


def _update_metrics_from_facts(dossier: dict[str, Any], obj: dict[str, Any]) -> None:
    metrics = dossier.setdefault("financial_metrics", {})
    keys = (
        "revenue_growth",
        "ebitda_margin",
        "operating_margin",
        "net_margin",
        "roe",
        "roa",
        "roic",
        "roce",
        "debt_equity",
        "current_ratio",
        "interest_coverage",
        "cash_conversion",
        "working_capital",
        "fcf",
        "eps",
        "nim",
        "casa",
        "gnpa",
        "nnpa",
        "cet1",
    )
    for f in obj.get("extracted_facts") or []:
        if not isinstance(f, dict):
            continue
        field = str(f.get("field") or "").lower().replace("/", "_").replace(" ", "_")
        for k in keys:
            if k in field or field == k:
                metrics[k] = f.get("value_text") or f.get("value")


def _soft_risks_from_text(dossier: dict[str, Any], obj: dict[str, Any]) -> None:
    blob = f"{obj.get('title') or ''} {obj.get('value_text') or ''}".lower()
    if not blob.strip():
        return
    risks = dossier.setdefault("risks", {})
    mapping = (
        ("regulatory", ("sebi", "rbi", "regulation", "compliance", "penalty")),
        ("governance", ("governance", "promoter", "related party", "audit")),
        ("financial", ("leverage", "debt", "liquidity", "default", "impairment")),
        ("macro", ("inflation", "rate hike", "recession", "fx", "currency")),
        ("industry", ("competition", "disruption", "cycle", "commodity")),
        ("execution", ("delay", "execution", "capex overrun", "guidance cut")),
        ("business", ("demand", "volume", "customer", "pricing")),
    )
    for bucket, keys in mapping:
        if any(k in blob for k in keys):
            arr = risks.setdefault(bucket, [])
            title = obj.get("title") or obj.get("fact_key") or bucket
            if not any(x.get("title") == title for x in arr):
                arr.append({"title": title, "source_id": obj.get("source_id"), "evidence_id": obj.get("evidence_id")})
                risks[bucket] = arr[-20:]
    # Simple score: count filled buckets / 7
    filled = sum(1 for b, _ in mapping if risks.get(b))
    risks["risk_score"] = round(filled / 7.0, 3)
    risks["trend"] = "elevated" if filled >= 4 else ("moderate" if filled >= 2 else "contained")
