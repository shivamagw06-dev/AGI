"""FAA v1.1 — production live acquisition tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.faa.cache import DocumentCache
from app.faa.discovery import DiscoveryService
from app.faa.fetch import FetchService
from app.faa.flags import FaaFlags
from app.faa.http_client import HttpClient, HttpResponse
from app.faa.models import CandidateDocument, sha256_text
from app.faa.service import FaaService
from app.faa.store import FaaStore
from app.fre.service import FreService
from app.fre.store import FreStore
from app.main import app


def _stack(*, live: bool = False):
    fre = FreService(store=FreStore())
    flags = FaaFlags(
        faa=True,
        faa_live_fetch=live,
        faa_discovery=True,
        faa_fetch=True,
        faa_processing=True,
        faa_index=True,
        faa_pdf=True,
        faa_notify_fre=True,
        faa_scheduler=True,
        faa_max_workers=4,
    )
    faa = FaaService(fre=fre, flags=flags)
    fre.bind(faa=faa)
    return fre, faa


def test_faa_health_locked_and_observability():
    _, faa = _stack()
    h = faa.health()
    assert h["programme"] == "FAA"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert h["does_not_answer"] is True
    assert h["never_reasons"] is True
    assert h["fre_bound"] is True
    assert "worker_count" in h
    assert "queue_depth" in h
    assert "cache" in h
    assert "versions" in h
    ids = {c["connector_id"] for c in h["connectors"]}
    for required in {"company_ir", "nse", "bse", "sebi", "rbi", "mca", "pib", "news", "rss", "search_api"}:
        assert required in ids


def test_discovery_plans_for_major_names():
    disco = DiscoveryService(live_fetch=False)
    for q in [
        "Should I buy Reliance?",
        "Analyse Infosys",
        "TCS quarterly results",
        "HDFC Bank filings",
    ]:
        tasks, candidates = disco.discover(q)
        assert len(tasks) >= 6
        assert any(t.connector_id == "company_ir" for t in tasks)
        assert any(t.connector_id in {"nse", "bse"} for t in tasks)
        assert candidates
        # Institutional plan covers report / filing / news classes
        dtypes = {t.document_type for t in tasks}
        assert "annual_report" in dtypes or "quarterly_report" in dtypes
        assert "exchange_filing" in dtypes or "news" in dtypes


def test_acquire_major_names_without_seed():
    fre, faa = _stack(live=False)
    for q in [
        "Should I buy Reliance?",
        "Analyse Infosys",
        "TCS quarterly results",
        "HDFC Bank filings",
        "NSE filing for Reliance Industries",
        "Government notification RBI monetary policy",
    ]:
        result = faa.acquire(q, limit=16)
        assert result["discovered"] >= 1
        assert result["does_not_answer"] is True
        assert result["indexed_to_fre"] >= 1 or result["skipped_cached"] >= 1


def test_discovery_government_and_nse_tasks():
    disco = DiscoveryService(live_fetch=False)
    tasks, candidates = disco.discover("RBI monetary policy and NSE filings for Reliance")
    assert any(t.connector_id == "rbi" for t in tasks)
    assert any(t.connector_id == "nse" for t in tasks)
    assert any("nseindia" in (c.url or "") or c.connector_id == "nse" for c in candidates)


def test_acquire_indexes_without_seed_dependency():
    """FAA acquisition records are independent of FRE seed corpus content."""
    fre, faa = _stack(live=False)
    result = faa.acquire("Should I buy Reliance?", limit=20)
    assert result["does_not_answer"] is True
    assert result["discovered"] >= 1
    assert result["indexed_to_fre"] >= 1
    # Indexed docs should carry FAA connector provenance
    faa_docs = [
        d
        for d in fre.store.documents.values()
        if (d.metadata or {}).get("faa_connector") or (d.source in {"company_ir", "nse", "bse", "news", "rss", "rbi"})
    ]
    assert faa_docs
    assert any((d.metadata or {}).get("faa_fetch_id") for d in faa_docs)


def test_cache_and_duplicate_detection():
    fre, faa = _stack(live=False)
    first = faa.acquire("Analyse Infosys", limit=12)
    second = faa.acquire("Analyse Infosys", limit=12)
    assert first["indexed_to_fre"] >= 1
    assert second["skipped_cached"] >= 1
    assert faa.cache.snapshot()["hit_ratio"] >= 0


def test_immutable_versioning_on_change():
    store = FaaStore()
    from app.faa.models import DocumentVersion

    v1 = store.put_version(
        DocumentVersion(url="https://example.com/ar.pdf", checksum="aaa", title="AR v1", connector_id="company_ir")
    )
    v2 = store.put_version(
        DocumentVersion(url="https://example.com/ar.pdf", checksum="bbb", title="AR v2", connector_id="company_ir")
    )
    assert v1.status == "superseded"
    assert v1.superseded_by == v2.document_id
    assert v2.version == 2
    assert v2.status == "active"
    # identical checksum returns existing
    v3 = store.put_version(
        DocumentVersion(url="https://example.com/ar.pdf", checksum="bbb", title="AR v2 again", connector_id="company_ir")
    )
    assert v3.document_id == v2.document_id


def test_live_fetch_mocked_http_downloads_and_indexes():
    fre, faa = _stack(live=True)
    html = b"""<!doctype html><html><body>
    <h1>Reliance Industries FY26 Annual Report Highlights</h1>
    <p>Consolidated revenue increased 18% year on year.</p>
    <p>EBITDA rose supported by Jio and Retail.</p>
    </body></html>"""

    def fake_get(url, **kwargs):
        return HttpResponse(
            status_code=200,
            content=html,
            headers={"content-type": "text/html; charset=utf-8", "etag": '"v1"'},
            url=url,
            elapsed_ms=12.0,
            attempts=1,
        )

    with patch.object(HttpClient, "get", side_effect=fake_get):
        result = faa.acquire("Should I buy Reliance?", limit=10)

    assert result["live_fetch"] is True
    assert result["fetched"] >= 1
    assert result["indexed_to_fre"] >= 1
    assert result["timings"]["fetch_ms"] >= 0
    live_docs = [d for d in result["documents"] if d.get("metadata", {}).get("faa_live_fetch")]
    assert live_docs
    assert any("ril.com" in (d.get("url") or "") or d.get("symbol") == "RELIANCE" for d in live_docs)


def test_live_fetch_retry_on_failure_then_success():
    flags = FaaFlags(faa=True, faa_live_fetch=True, faa_max_workers=2)
    fre = FreService(store=FreStore())
    faa = FaaService(fre=fre, flags=flags)
    fre.bind(faa=faa)

    calls = {"n": 0}

    def flaky_get(url, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return HttpResponse(status_code=503, content=b"", headers={}, url=url, elapsed_ms=5, attempts=1)
        return HttpResponse(
            status_code=200,
            content=b"<html><body>Infosys Q1 guidance mid-single digit growth</body></html>",
            headers={"content-type": "text/html"},
            url=url,
            elapsed_ms=8,
            attempts=2,
        )

    with patch.object(HttpClient, "get", side_effect=flaky_get):
        result = faa.acquire("Analyse Infosys", limit=6)
    assert result["live_fetch"] is True
    assert result["discovered"] >= 1


def test_http_client_retries_on_503():
    client = HttpClient(max_retries=3, backoff_base=0.01)
    attempts = {"n": 0}

    class FakeResp:
        def __init__(self, status_code, content=b"ok"):
            self.status_code = status_code
            self.content = content
            self.headers = {"content-type": "text/html"}
            self.url = "https://example.com/x"

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            attempts["n"] += 1
            if attempts["n"] < 3:
                return FakeResp(503, b"")
            return FakeResp(200, b"<html>ok</html>")

    with patch("httpx.Client", FakeClient):
        resp = client.get("https://example.com/x", connector_id="company_ir")
    assert resp.status_code == 200
    assert resp.attempts == 3
    assert attempts["n"] == 3


def test_connector_failure_does_not_break_pipeline():
    fre, faa = _stack(live=True)

    def boom(url, **kwargs):
        return HttpResponse(status_code=0, content=b"", headers={}, url=url, elapsed_ms=1, attempts=3, error="timeout")

    with patch.object(HttpClient, "get", side_effect=boom):
        result = faa.acquire("Should I buy Reliance?", limit=8)
    assert result["failed"] >= 1 or result["fetched"] == 0
    assert result["does_not_answer"] is True


def test_etag_not_modified_skips_download():
    cache = DocumentCache()
    cache.put(
        url="https://www.ril.com/InvestorRelations/Overview.aspx",
        checksum="abc123",
        etag='"abc"',
        title="IR",
        connector_id="company_ir",
        live_fetch=True,
    )
    fetch = FetchService(cache, live_fetch=True, max_workers=1)
    cand = CandidateDocument(
        title="Reliance IR",
        url="https://www.ril.com/InvestorRelations/Overview.aspx",
        connector_id="company_ir",
        document_type="investor_relations",
        company="Reliance Industries",
        symbol="RELIANCE",
    )
    # URL cached => skip before HTTP
    got = fetch.fetch_one(cand)
    assert got.skipped is True


def test_content_type_detection_pdf_and_rss():
    fetch = FetchService(DocumentCache(), live_fetch=True)
    assert fetch._detect_content_type("https://x.com/a.pdf", "application/octet-stream", b"%PDF-1.4") == "application/pdf"
    assert fetch._detect_content_type("https://x.com/feed.xml", "application/xml", b"<?xml version='1.0'?><rss>") == "application/xml"
    rss_text = fetch._extract_xml_rss(b"<?xml version='1.0'?><rss><channel><title>SEBI</title><item><title>Circular</title><link>https://sebi.gov.in/x</link></item></channel></rss>")
    assert "Circular" in rss_text or "SEBI" in rss_text


def test_fre_query_acquisition_block_from_faa():
    fre, _ = _stack(live=False)
    pack = fre.query("Should I buy Reliance?", limit=5)
    assert pack["acquisition"]["programme"] == "FAA"
    assert pack["acquisition"]["discovered"] is not None
    assert pack["top_evidence"]


@pytest.mark.asyncio
async def test_faa_http_health_and_acquire_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer dev-intelligence-token"}
        health = await client.get("/v1/faa/health", headers=headers)
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "FAA"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert "worker_count" in body

        disco = await client.get("/v1/faa/discover", params={"q": "Should I buy Reliance?"}, headers=headers)
        assert disco.status_code == 200
        assert disco.json()["candidates"]

        acq = await client.post(
            "/v1/faa/acquire",
            params={"q": "Should I buy Reliance?", "limit": 12},
            headers=headers,
        )
        assert acq.status_code == 200
        data = acq.json()
        assert data["does_not_answer"] is True
        assert data["discovered"] >= 1
