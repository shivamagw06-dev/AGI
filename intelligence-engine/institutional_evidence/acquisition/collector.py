"""Evidence Acquisition — every document gets identity metadata (no anonymous docs)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema import DOCUMENT_TYPES, PHASE1_TOP20


def list_document_types() -> List[str]:
    return list(DOCUMENT_TYPES)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _doc(
    *,
    company: str,
    ticker: str,
    document_type: str,
    source: str,
    url: str = "",
    content_type: str = "application/json",
    published_at: Optional[str] = None,
    status: str = "acquired",
    payload: Optional[Dict[str, Any]] = None,
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
    from ..governance.layer0 import govern_inbound_dataset

    blob = f"{ticker}|{document_type}|{source}|{url}|{published_at or ''}"
    checksum = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    gov = govern_inbound_dataset(
        {"hash": checksum, "checksum": checksum, "keys": sorted((payload or {}).keys())[:20]},
        provider_id=source,
        document_type=document_type,
        url=url,
        entity_id=entity_id,
    )
    return {
        "document_id": f"doc_{uuid.uuid4().hex[:16]}",
        "company": company,
        "ticker": ticker.upper(),
        "entity_id": entity_id,
        "document_type": document_type,
        "source": source,
        "published_at": published_at,
        "downloaded_at": _now(),
        "checksum": checksum,
        "hash": checksum,
        "url": url,
        "content_type": content_type,
        "status": status if gov.get("admitted") else "governance_rejected",
        "payload_keys": sorted((payload or {}).keys())[:20],
        "governance": gov.get("governance"),
    }


def _try_fse_raw(ticker: str) -> Optional[Dict[str, Any]]:
    try:
        from financial_statements_engine.production import get_raw_filings  # type: ignore

        return get_raw_filings(ticker)
    except Exception:
        return None


def _try_earnings(ticker: str) -> Optional[Dict[str, Any]]:
    try:
        from earnings_intelligence.production import get_earnings_pack  # type: ignore

        return get_earnings_pack(ticker)
    except Exception:
        try:
            from earnings_intelligence.pack import build_earnings_pack  # type: ignore

            return build_earnings_pack(ticker)
        except Exception:
            return None


def _try_live(ticker: str) -> Optional[Dict[str, Any]]:
    try:
        from live_institutional_data.production import get_company_snapshot  # type: ignore

        return get_company_snapshot(ticker)
    except Exception:
        return None


def acquire_company_documents(
    ticker: str,
    *,
    company: Optional[str] = None,
    trigger_ingest: bool = False,
) -> Dict[str, Any]:
    """
    Collect institutional documents for a ticker.

    Primary: NSE/BSE/IR/earnings/shareholding/corp actions (via existing engines).
    Secondary: Yahoo/Groww/news/macro when available.
    Every document receives full identity metadata.
    """
    t = str(ticker or "").upper().strip()
    name = company or next((c["company"] for c in PHASE1_TOP20 if c["ticker"] == t), t)
    try:
        from ..entity.resolve import entity_id_for_ticker

        entity_id = entity_id_for_ticker(t)
    except Exception:
        entity_id = None
    documents: List[Dict[str, Any]] = []
    sources_hit: List[str] = []
    errors: List[str] = []

    if trigger_ingest:
        try:
            from financial_statements_engine.production import run_ingest  # type: ignore

            run_ingest(t, force=False)
            sources_hit.append("fse_ingest")
        except Exception as exc:
            errors.append(f"fse_ingest:{exc}")

    raw = _try_fse_raw(t)
    if isinstance(raw, dict) and raw:
        documents.append(
            _doc(
                company=name,
                ticker=t,
                entity_id=entity_id,
                document_type="nse_xbrl",
                source="nse",
                url=str(raw.get("url") or raw.get("source_url") or ""),
                published_at=str(raw.get("as_of") or raw.get("published_at") or "") or None,
                payload=raw if isinstance(raw, dict) else None,
                status="acquired" if raw.get("ok", True) else "partial",
            )
        )
        sources_hit.append("nse_xbrl")

    earn = _try_earnings(t)
    if isinstance(earn, dict) and earn:
        documents.append(
            _doc(
                company=name,
                ticker=t,
                entity_id=entity_id,
                document_type="quarterly_results",
                source="earnings_intelligence",
                published_at=str(earn.get("as_of") or "") or None,
                payload=earn,
                status="acquired",
            )
        )
        qh = earn.get("quarter_history") or earn.get("quarters") or []
        ah = earn.get("annual_history") or earn.get("annuals") or []
        if qh or ah:
            documents.append(
                _doc(
                    company=name,
                    ticker=t,
                    entity_id=entity_id,
                    document_type="annual_report",
                    source="earnings_intelligence",
                    payload={"quarters": len(qh) if isinstance(qh, list) else 0,
                             "annuals": len(ah) if isinstance(ah, list) else 0},
                    status="acquired",
                )
            )
        sources_hit.append("earnings_intelligence")

    live = _try_live(t)
    if isinstance(live, dict) and live:
        documents.append(
            _doc(
                company=name,
                ticker=t,
                entity_id=entity_id,
                document_type="market_secondary",
                source="live_institutional_data",
                payload=live if isinstance(live, dict) else None,
                status="acquired",
            )
        )
        sources_hit.append("live_institutional_data")

    # Secondary market quotes (never substitute for statements)
    for src_name, loader in (
        ("yahoo", lambda: __import__("yahoo_finance_provider.production", fromlist=["get_quote"]).get_quote(t)),  # type: ignore
        ("groww", lambda: None),
    ):
        try:
            q = loader()
            if isinstance(q, dict) and q:
                documents.append(
                    _doc(
                        company=name,
                        ticker=t,
                        entity_id=entity_id,
                        document_type="market_secondary",
                        source=src_name,
                        payload=q,
                        status="acquired",
                    )
                )
                sources_hit.append(src_name)
        except Exception:
            pass

    anonymous = [d for d in documents if not d.get("document_id") or not d.get("hash")]
    ungoverened = [d for d in documents if not d.get("governance")]
    return {
        "ok": True,
        "ticker": t,
        "company": name,
        "entity_id": entity_id,
        "document_count": len(documents),
        "documents": documents,
        "sources_hit": sorted(set(sources_hit)),
        "anonymous_documents": len(anonymous),
        "ungoverned_documents": len(ungoverened),
        "errors": errors,
        "rule": "Layer 0 governance + entity_id on every document — no anonymous ingress",
    }
