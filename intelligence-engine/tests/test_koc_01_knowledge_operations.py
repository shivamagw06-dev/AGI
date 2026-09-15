"""KOC V1.2 — Institutional Knowledge Mission Control tests."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge_operations.schema import (
    DOCUMENT_UPLOAD_TYPES,
    KOC_PLATFORM,
    KOC_VERSION,
    KOC_WORKSTREAM_ID,
    MISSION,
    UPLOAD_PIPELINE,
)
from knowledge_operations.production import (
    find_missing_knowledge,
    get_coverage,
    get_gap_ai,
    get_missing_inbox,
    get_overview,
    get_status,
    get_system_health,
    global_search,
    health,
    soft_slice_mission_control,
    upload_knowledge,
    get_audit,
    run_action,
    run_cgl,
)


def test_koc_v12_identity():
    st = get_status()
    assert st["workstream_id"] == "KOC-01"
    assert KOC_VERSION.startswith("koc-01-v1.2")
    assert KOC_PLATFORM == "AGI V1.2"
    assert health()["admin_only"] is True
    assert "Institutional Knowledge" in MISSION
    assert "annual_report" in DOCUMENT_UPLOAD_TYPES
    assert UPLOAD_PIPELINE[0] == "Upload"
    assert "Knowledge Snapshot" in UPLOAD_PIPELINE


def test_system_health_bar():
    bar = get_system_health()
    assert bar["ok"] is True
    assert "cgl" in bar["bar"]
    assert "kil" in bar["bar"]
    assert "icf" in bar["bar"]
    assert "scheduler" in bar["bar"]
    assert "auto_repair" in bar["bar"]
    assert bar["bar"]["koc"]["version"].startswith("koc-01")


def test_missing_inbox_has_icc_gain():
    inbox = get_missing_inbox(scope="TOP20", limit=20)
    assert inbox["ok"] is True
    assert "Highest-Impact" in inbox["title"]
    items = inbox.get("items") or []
    if items:
        assert "estimated_icc_gain_pct" in items[0]
        assert items[0]["estimated_icc_gain_pct"] > 0
        ranks = [i.get("priority_rank", 9) for i in items]
        assert ranks == sorted(ranks)


def test_gap_ai_estimates_uplift():
    gaps = get_gap_ai(scope="TOP20", limit=10)
    assert gaps["ok"] is True
    assert gaps["title"] == "Knowledge Gap AI"
    if gaps.get("items"):
        g = gaps["items"][0]
        assert g["coverage_expected"] >= g["coverage_now"]
        assert "estimated_new_claims" in g
    one = find_missing_knowledge("RELIANCE")
    assert one["ok"] is True
    assert one["ticker"] == "RELIANCE"


def test_overview_control_room_surfaces():
    desk = get_overview(scope="TOP20")
    assert desk["ok"] is True
    assert desk["workstream_id"] == KOC_WORKSTREAM_ID
    assert desk["version"].startswith("koc-01-v1.2")
    assert "system_health" in desk
    assert "gap_ai" in desk
    assert "kpis" in desk
    assert "cgl_status" in desk["kpis"]
    assert "missing_inbox" in desk
    assert "coverage_table" in desk
    assert desk["security"]["never_overwrite"] is True
    cov = get_coverage(scope="TOP20")
    assert cov["ok"] is True
    assert "table" in cov


def test_global_search_companies():
    res = global_search("Reliance", limit=10)
    assert res["ok"] is True
    companies = (res.get("results") or {}).get("companies") or []
    assert any(c.get("ticker") == "RELIANCE" for c in companies)


def test_upload_is_append_only_and_audited():
    payload = base64.b64encode(b"%PDF-1.4 koc v12 test").decode("ascii")
    res = upload_knowledge(
        ticker="RELIANCE",
        document_type="investor_presentation",
        filename="reliance_q1_deck_v12.pdf",
        content_base64=payload,
        actor="test_admin@agi.local",
    )
    assert res["ok"] is True
    assert res["upload"]["immutable"] is True
    assert res["audit"]["action"] == "upload_knowledge"
    aud = get_audit(limit=10, ticker="RELIANCE")
    assert aud["count"] >= 1


def test_action_aliases_audited():
    out = run_action("run_coverage_scan", actor="test_admin")
    assert out.get("ok") is True or out.get("error")
    assert "audit" in out
    # Dedicated façade
    cgl = run_cgl(actor="test_admin")
    assert "audit" in cgl


def test_mission_control_soft_slice():
    slice_ = soft_slice_mission_control()
    assert slice_.get("status") == "ok"
    assert "Knowledge Operations" in slice_["board"]
    assert "system_health" in slice_
