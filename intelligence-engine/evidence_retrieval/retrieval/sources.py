"""Soft-read evidence candidates from existing AGIB knowledge — never raw APIs."""

from __future__ import annotations

from typing import Any

from evidence_retrieval.store import utc_now


def _item(
    *,
    evidence_id: str,
    evidence_type: str,
    knowledge_object: str,
    source: str,
    title: str,
    payload: Any,
    company: str | None = None,
    confidence: float = 0.7,
    available_from: str | None = None,
    collector: str | None = None,
    document_id: str | None = None,
    section: str | None = None,
    page: int | None = None,
    paragraph: int | None = None,
    checksum: str | None = None,
    version: str = "1",
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "knowledge_object": knowledge_object,
        "source": source,
        "collector": collector or source,
        "company": company,
        "title": title,
        "payload": payload,
        "confidence": confidence,
        "available_from": available_from or utc_now()[:10],
        "retrieved_at": utc_now(),
        "document_id": document_id,
        "section": section,
        "page": page,
        "paragraph": paragraph,
        "checksum": checksum,
        "version": version,
        "fabricated": False,
    }


def discover_candidates(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    """Query KF / IDI / LIDI / RO soft surfaces only."""
    items: list[dict[str, Any]] = []
    companies = discovery.get("companies") or []
    needed = set(discovery.get("evidence_types_required") or [])
    as_of = discovery.get("as_of")

    for ticker in companies or ["INFY"]:
        items.extend(_company_intel(ticker, needed))
        items.extend(_events(ticker, needed))
        items.extend(_documents(ticker, needed, as_of=as_of))
        items.extend(_historical(ticker, needed))
        items.extend(_ownership(ticker, needed))

    if "GOVERNMENT_POLICIES" in needed or "government" in (discovery.get("topics") or []):
        items.extend(_government(needed))
    if "MACRO_INDICATORS" in needed or "macro" in (discovery.get("topics") or []):
        items.extend(_macro(needed))
    if "ALTERNATIVE_DATA" in needed or "alt_data" in (discovery.get("topics") or []):
        items.extend(_alt(needed))
    if "RELATIONSHIP_GRAPH" in needed or "industry" in (discovery.get("topics") or []):
        for ticker in companies or ["INFY"]:
            items.extend(_relationships(ticker, needed))
            items.extend(_industry(ticker, needed))
    if companies:
        items.extend(_expectations(companies[0], needed))
        items.extend(_research_office(companies[0], needed))
        items.extend(_lidi(companies[0], needed))

    # Point-in-time filter
    if as_of:
        day = str(as_of)[:10]
        items = [i for i in items if str(i.get("available_from") or "")[:10] <= day]

    return items


def _company_intel(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.company_intelligence.production import get_company

        obj = get_company(ticker)
        if not obj or obj.get("unavailable"):
            return []
        return [
            _item(
                evidence_id=f"ici_{ticker}",
                evidence_type="FINANCIAL_METRICS" if "FINANCIAL_METRICS" in needed else "OWNERSHIP",
                knowledge_object="CompanyIntelligenceObject",
                source="knowledge_factory",
                collector="company_intelligence",
                title=f"{ticker} company intelligence",
                payload={"coverage_level": obj.get("coverage_level"), "summary_keys": list(obj.keys())[:20]},
                company=ticker,
                confidence=0.8,
                available_from=(obj.get("as_of") or obj.get("updated_at") or utc_now())[:10],
            )
        ]
    except Exception:
        return []


def _events(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    if "CORPORATE_EVENTS" not in needed and "TIMELINES" not in needed:
        # still soft-include lightly for company questions
        pass
    try:
        from knowledge_factory.corporate_events.production import company as ce_company

        row = ce_company(ticker) if callable(ce_company) else None
        if not row:
            from knowledge_factory.corporate_events import store as ce_store

            row = {"events": ce_store.list_all() if hasattr(ce_store, "list_all") else []}
        events = row.get("events") or row.get("timeline") or []
        if isinstance(events, dict):
            events = events.get("events") or []
        out = []
        for i, e in enumerate(list(events)[:20]):
            if not isinstance(e, dict):
                continue
            out.append(
                _item(
                    evidence_id=f"evt_{ticker}_{i}",
                    evidence_type="CORPORATE_EVENTS",
                    knowledge_object="CorporateEventObject",
                    source="knowledge_factory",
                    collector="corporate_events",
                    title=str(e.get("headline") or e.get("event_type") or "event"),
                    payload=e,
                    company=ticker,
                    confidence=0.75,
                    available_from=str(e.get("event_date") or e.get("available_from") or utc_now())[:10],
                )
            )
        return out
    except Exception:
        return []


def _documents(ticker: str, needed: set[str], *, as_of: str | None) -> list[dict[str, Any]]:
    doc_types = {
        "DOCUMENT_SECTIONS",
        "ACCOUNTING_NOTES",
        "RISK_FACTORS",
        "MANAGEMENT_COMMENTARY",
        "CONFERENCE_CALLS",
        "INVESTOR_PRESENTATIONS",
    }
    if needed and not (needed & doc_types) and "FINANCIAL_METRICS" not in needed:
        # still allow docs for company questions
        pass
    try:
        from knowledge_factory.institutional_documents import store as idi_store
        from knowledge_factory.institutional_documents.replay import replay_as_of

        if as_of:
            vis = replay_as_of(as_of, ticker=ticker)
            doc_metas = vis.get("documents") or []
            docs = []
            for m in doc_metas:
                d = idi_store.get_document(m["document_id"])
                if d:
                    docs.append(d)
        else:
            docs = idi_store.list_documents(ticker=ticker)
        out = []
        for d in docs[:30]:
            chunks = idi_store.get_chunks(str(d["document_id"]))[:8]
            for c in chunks:
                et = "DOCUMENT_SECTIONS"
                sec = str(c.get("section") or "")
                if sec == "RISK_FACTORS":
                    et = "RISK_FACTORS"
                elif sec == "MANAGEMENT_DISCUSSION":
                    et = "MANAGEMENT_COMMENTARY"
                elif sec == "NOTES":
                    et = "ACCOUNTING_NOTES"
                elif d.get("type") == "CONFERENCE_CALL_TRANSCRIPT":
                    et = "CONFERENCE_CALLS"
                elif d.get("type") == "INVESTOR_PRESENTATION":
                    et = "INVESTOR_PRESENTATIONS"
                out.append(
                    _item(
                        evidence_id=f"doc_{c.get('chunk_id')}",
                        evidence_type=et,
                        knowledge_object=str(d.get("type") or "Document"),
                        source="institutional_documents",
                        collector=d.get("collector") or "idi",
                        title=f"{d.get('title')} / {c.get('heading')}",
                        payload={"text": (c.get("text") or "")[:500], "heading": c.get("heading")},
                        company=ticker,
                        confidence=float(d.get("confidence") or 0.85),
                        available_from=d.get("available_from"),
                        document_id=d.get("document_id"),
                        section=c.get("section"),
                        page=c.get("page"),
                        paragraph=c.get("paragraph"),
                        checksum=c.get("checksum"),
                        version=str(d.get("version") or "1"),
                    )
                )
        return out
    except Exception:
        return []


def _historical(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.production import company_object

        obj = company_object(ticker)
        if not obj:
            return []
        return [
            _item(
                evidence_id=f"hist_{ticker}",
                evidence_type="HISTORICAL_VALUATION" if "HISTORICAL_VALUATION" in needed else "FINANCIAL_METRICS",
                knowledge_object="HistoricalCompanyObject",
                source="knowledge_factory",
                collector="historical_depth",
                title=f"{ticker} historical object",
                payload={"keys": list(obj.keys())[:25] if isinstance(obj, dict) else {}},
                company=ticker,
                confidence=0.7,
            )
        ]
    except Exception:
        return []


def _ownership(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    if "OWNERSHIP" not in needed:
        return []
    try:
        from knowledge_factory.company_intelligence.production import get_company

        obj = get_company(ticker) or {}
        own = obj.get("ownership") or obj.get("shareholding") or {}
        if not own:
            return []
        return [
            _item(
                evidence_id=f"own_{ticker}",
                evidence_type="OWNERSHIP",
                knowledge_object="OwnershipObject",
                source="knowledge_factory",
                collector="company_intelligence",
                title=f"{ticker} ownership",
                payload=own,
                company=ticker,
                confidence=0.75,
            )
        ]
    except Exception:
        return []


def _government(needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.government_intelligence.production import dashboard

        dash = dashboard()
        return [
            _item(
                evidence_id="gov_dash",
                evidence_type="GOVERNMENT_POLICIES",
                knowledge_object="GovernmentIntelligenceObject",
                source="knowledge_factory",
                collector="government_intelligence",
                title="Government intelligence coverage",
                payload={"keys": list(dash.keys())[:20] if isinstance(dash, dict) else {}},
                confidence=0.7,
                available_from=utc_now()[:10],
            )
        ]
    except Exception:
        return []


def _macro(needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.production import macro_intelligence_coverage

        m = macro_intelligence_coverage()
        return [
            _item(
                evidence_id="macro_cov",
                evidence_type="MACRO_INDICATORS",
                knowledge_object="MacroObject",
                source="knowledge_factory",
                collector="macro_intelligence",
                title="Macro intelligence coverage",
                payload=m if isinstance(m, dict) else {"value": m},
                confidence=0.7,
            )
        ]
    except Exception:
        try:
            from live_data import store as lidi_store

            snap = lidi_store.get_latest_snapshot("rbi_dbie", "LATEST")
            if not snap:
                return []
            return [
                _item(
                    evidence_id="lidi_macro",
                    evidence_type="MACRO_INDICATORS",
                    knowledge_object="MacroObject",
                    source="live_data",
                    collector="lidi_rbi_dbie_v1",
                    title="RBI DBIE validated snapshot",
                    payload=(snap.get("payload") or {}),
                    confidence=0.8,
                    available_from=snap.get("effective_date"),
                    checksum=snap.get("checksum"),
                )
            ]
        except Exception:
            return []


def _alt(needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.alternative_data_intelligence.production import dashboard

        dash = dashboard()
        return [
            _item(
                evidence_id="alt_dash",
                evidence_type="ALTERNATIVE_DATA",
                knowledge_object="AlternativeDataObject",
                source="knowledge_factory",
                collector="alternative_data_intelligence",
                title="Alternative data coverage",
                payload={"keys": list(dash.keys())[:20] if isinstance(dash, dict) else {}},
                confidence=0.65,
            )
        ]
    except Exception:
        return []


def _relationships(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.economic_relationship_intelligence.production import company as rel_company

        row = rel_company(ticker)
        return [
            _item(
                evidence_id=f"rel_{ticker}",
                evidence_type="RELATIONSHIP_GRAPH",
                knowledge_object="EconomicRelationshipObject",
                source="knowledge_factory",
                collector="economic_relationship_intelligence",
                title=f"{ticker} relationships",
                payload=row if isinstance(row, dict) else {},
                company=ticker,
                confidence=0.7,
            )
        ]
    except Exception:
        return []


def _industry(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.industry_intelligence.production import dashboard

        dash = dashboard()
        return [
            _item(
                evidence_id=f"ind_{ticker}",
                evidence_type="RELATIONSHIP_GRAPH",
                knowledge_object="IndustryIntelligenceObject",
                source="knowledge_factory",
                collector="industry_intelligence",
                title="Industry intelligence",
                payload={"keys": list(dash.keys())[:15] if isinstance(dash, dict) else {}},
                company=ticker,
                confidence=0.7,
            )
        ]
    except Exception:
        return []


def _expectations(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.market_expectations_intelligence.production import company as exp_company

        row = exp_company(ticker)
        return [
            _item(
                evidence_id=f"exp_{ticker}",
                evidence_type="FINANCIAL_METRICS",
                knowledge_object="ExpectationObject",
                source="knowledge_factory",
                collector="market_expectations_intelligence",
                title=f"{ticker} expectations",
                payload=row if isinstance(row, dict) else {},
                company=ticker,
                confidence=0.65,
            )
        ]
    except Exception:
        return []


def _research_office(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    try:
        from research_office.production import company as ro_company

        row = ro_company(ticker)
        return [
            _item(
                evidence_id=f"ro_{ticker}",
                evidence_type="TIMELINES",
                knowledge_object="ResearchPublication",
                source="research_office",
                collector="research_office",
                title=f"{ticker} research office",
                payload={"keys": list(row.keys())[:15] if isinstance(row, dict) else {}},
                company=ticker,
                confidence=0.7,
            )
        ]
    except Exception:
        return []


def _lidi(ticker: str, needed: set[str]) -> list[dict[str, Any]]:
    try:
        from live_data import store as lidi_store

        last = lidi_store.get_last_run() or {}
        publish = last.get("publish") or {}
        if not publish:
            return []
        return [
            _item(
                evidence_id=f"lidi_{ticker}",
                evidence_type="FINANCIAL_METRICS",
                knowledge_object="LiveMarketObject",
                source="live_data",
                collector="lidi",
                title="LIDI validated publish",
                payload={"pack_ids": publish.get("pack_ids"), "object_counts": publish.get("object_counts")},
                company=ticker,
                confidence=0.85,
                available_from=(last.get("finished_at") or utc_now())[:10],
            )
        ]
    except Exception:
        return []
