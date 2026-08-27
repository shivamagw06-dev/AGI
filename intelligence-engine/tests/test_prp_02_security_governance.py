"""PRP-02 — Security & Governance tests."""

from __future__ import annotations

import os

import pytest

from institutional_security.audit import emit, has_audit_for_action, list_events
from institutional_security.authentication import authenticate_password, authenticate_sso_oidc
from institutional_security.authorization import authorize, build_security_context
from institutional_security.correlation import ensure_correlation_id, get_correlation_id
from institutional_security.encryption import decrypt_at_rest, encrypt_at_rest, hash_secret, verify_secret
from institutional_security.gateway import gate
from institutional_security.permissions import assert_permission, resolve_permissions
from institutional_security.production import (
    create_api_key,
    health,
    login,
    logout,
    refresh,
    reset_for_tests,
    revoke_api_key,
    soft_slice_mission_control,
)
from institutional_security.roles import list_roles, normalize_role
from institutional_security.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    PRP_WORKSTREAM_ID,
)
from institutional_security.session import get_session
from institutional_security.tenant import assert_tenant_access, list_tenants
from institutional_security.validator import validate_privileged_audit, validate_security_context


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("AGI_PRP_02_ENFORCE", raising=False)
    reset_for_tests()
    yield
    reset_for_tests()


def test_health_and_freeze_invariants():
    h = health()
    assert h["workstream_id"] == PRP_WORKSTREAM_ID
    assert h["status"] == "ok"
    assert h["adds_intelligence_engines"] is False
    assert h["architecture_frozen"] is True
    assert h["enters_intelligence_layer"] is False
    assert ADDS_INTELLIGENCE_ENGINES is False
    assert ARCHITECTURE_FROZEN is True
    assert "Security decides who" in GUIDING_PRINCIPLE


def test_authentication_password_and_session_lifecycle():
    res = login({"username": "analyst.demo", "password": "analyst-pass"})
    assert res["ok"] is True
    assert res["session_id"]
    assert res["security_context"]["role"] == "research_analyst"
    assert res["correlation_id"]
    sid = res["session_id"]
    assert get_session(sid) is not None
    ref = refresh({"session_id": sid})
    assert ref["ok"] is True
    out = logout({"session_id": sid, "user_id": "analyst.demo"})
    assert out["ok"] is True
    assert get_session(sid) is None


def test_authentication_failure():
    bad = login({"username": "analyst.demo", "password": "wrong"})
    assert bad["ok"] is False
    assert bad["rejected"] is True


def test_sso_oidc_and_rbac():
    identity, err = authenticate_sso_oidc(
        method="oidc",
        subject="cio.demo",
        claims={"sub": "cio.demo", "role": "chief_investment_officer"},
    )
    assert err is None
    assert identity["authentication_method"] == "oidc"
    roles = {r["role_id"] for r in list_roles()}
    assert "chief_investment_officer" in roles
    assert normalize_role("CIO") == "chief_investment_officer"
    perms = resolve_permissions(role="chief_investment_officer")
    assert "committee.approve" in perms
    assert "platform.admin" not in perms


def test_authorization_analyst_vs_readonly():
    analyst = build_security_context(
        user_id="analyst.demo",
        tenant_id="agi-default",
        role="research_analyst",
    )
    ok, _ = authorize(analyst, permission="publication.generate")
    assert ok is True
    ro = build_security_context(
        user_id="readonly.demo",
        tenant_id="agi-default",
        role="read_only",
    )
    ok2, err = authorize(ro, permission="publication.generate")
    assert ok2 is False
    assert "insufficient permission" in (err or "")


def test_api_keys_create_auth_rotate_revoke():
    admin = login({"username": "admin.demo", "password": "admin-pass"})
    assert admin["ok"]
    created = create_api_key(
        {
            "session_id": admin["session_id"],
            "kind": "service",
            "permissions": ["research.read", "publication.generate"],
            "label": "batch",
        }
    )
    assert created["ok"] is True
    raw = created["api_key"]
    kid = created["api_key_id"]
    # Authenticate via gateway with API key
    g = gate({"api_key": raw}, operation="ask", resource="ask")
    assert g["ok"] is True
    assert g["security_context"]["authentication_method"] == "api_key"
    revoked = revoke_api_key(kid, {"session_id": admin["session_id"]})
    assert revoked["ok"] is True
    g2 = gate({"api_key": raw}, operation="ask", resource="ask")
    assert g2["ok"] is False


def test_tenant_isolation():
    ok, err = assert_tenant_access(
        tenant_id="agi-default",
        resource_tenant_id="tenant-beta",
        resource_kind="portfolio",
    )
    assert ok is False
    assert "tenant mismatch" in (err or "")
    ok2, _ = assert_tenant_access(
        tenant_id="agi-default",
        resource_tenant_id="x",
        resource_kind="intelligence",
    )
    assert ok2 is True  # global intelligence not tenant-gated
    tenants = list_tenants()
    assert len(tenants) >= 2


def test_cross_tenant_portfolio_gate():
    beta = login({"username": "analyst.beta", "password": "beta-pass"})
    assert beta["ok"]
    g = gate(
        {
            "session_id": beta["session_id"],
            "portfolio_id": "agi-core-equity",  # owned by agi-default
            "resource_tenant_id": "agi-default",
        },
        operation="workspace.read",
        resource="workspace",
    )
    assert g["ok"] is False
    assert g["error"] in {"insufficient_permission", "forbidden"} or "tenant" in (
        g.get("reason") or ""
    )


def test_audit_immutable_and_correlation():
    cid = ensure_correlation_id("corr_test_prp02")
    assert get_correlation_id() == "corr_test_prp02"
    ev = emit(
        action="publication.generate",
        resource="publication",
        resource_id="pub-1",
        user_id="pm.demo",
        tenant_id="agi-default",
        correlation_id=cid,
    )
    assert ev.event_id.startswith("aud_")
    assert ev.correlation_id == cid
    assert has_audit_for_action(
        action="publication.generate",
        resource_id="pub-1",
        correlation_id=cid,
    )
    v = validate_privileged_audit(
        action="publication.generate",
        resource_id="pub-1",
        correlation_id=cid,
    )
    assert v["ok"] is True
    rows = list_events(correlation_id=cid)
    assert any(r["event_id"] == ev.event_id for r in rows)


def test_encryption_roundtrip():
    h = hash_secret("secret")
    assert verify_secret("secret", h)
    assert not verify_secret("nope", h)
    sealed = encrypt_at_rest("session-material")
    assert decrypt_at_rest(sealed) == "session-material"


def test_validator_security_context():
    ctx = build_security_context(
        user_id="pm.demo",
        tenant_id="agi-default",
        role="portfolio_manager",
    )
    v = validate_security_context(ctx)
    assert v["ok"] is True
    bad = validate_security_context({"user_id": "", "tenant_id": "", "role": ""})
    assert bad["ok"] is False


def test_soft_slice_security_center():
    board = soft_slice_mission_control()
    assert board["security_center"] is True
    assert board["workstream_id"] == PRP_WORKSTREAM_ID
    assert "active_sessions" in board
    assert board["enters_intelligence_layer"] is False


def test_integration_analyst_ask_authorized():
    from institutional_orchestrator.production import ask, reset_for_tests as reset_uag

    reset_uag()
    sess = login({"username": "analyst.demo", "password": "analyst-pass"})
    result = ask(
        {
            "question": "What is the decision on HDFCBANK?",
            "session_id": sess["session_id"],
            "bypass_cache": True,
        }
    )
    # Gate allows research.read; ask may ok or rejected by UAG validation — not auth
    assert result.get("error") != "authentication_failed"
    assert result.get("error") != "insufficient_permission"
    if result.get("ok"):
        assert result.get("security_context") or result.get("correlation_id")


def test_integration_readonly_cannot_publish():
    from institutional_publishing.production import generate, reset_for_tests as reset_pub

    reset_pub()
    sess = login({"username": "readonly.demo", "password": "ro-pass"})
    result = generate(
        {
            "session_id": sess["session_id"],
            "type": "MorningBrief",
            "portfolio_id": "agi-core-equity",
            "async": False,
        }
    )
    assert result.get("ok") is False
    assert result.get("rejected") is True
    assert result.get("error") == "insufficient_permission"


def test_integration_pm_can_publish_with_audit():
    from institutional_publishing.production import generate, reset_for_tests as reset_pub

    reset_pub()
    sess = login({"username": "pm.demo", "password": "pm-pass"})
    result = generate(
        {
            "session_id": sess["session_id"],
            "type": "MorningBrief",
            "portfolio_id": "agi-core-equity",
            "async": False,
        }
    )
    # Composition may succeed or fail validation — authorization must pass
    assert result.get("error") != "insufficient_permission"
    if result.get("ok"):
        assert result.get("security_context")
        assert result.get("correlation_id")
        pub_id = (result.get("publication") or {}).get("publication_id") or ""
        assert has_audit_for_action(action="publication.generate", resource_id=pub_id) or list_events(
            action="publication.generate", limit=5
        )


def test_integration_cio_committee_permission():
    cio = build_security_context(
        user_id="cio.demo",
        tenant_id="agi-default",
        role="chief_investment_officer",
    )
    ok, _ = authorize(cio, permission="committee.approve")
    assert ok is True
    analyst = build_security_context(
        user_id="analyst.demo",
        tenant_id="agi-default",
        role="research_analyst",
    )
    ok2, _ = authorize(analyst, permission="committee.approve")
    assert ok2 is False


def test_permission_assert_helper():
    perms = resolve_permissions(role="portfolio_manager")
    ok, err = assert_permission(perms, "portfolio.manage")
    assert ok and err is None


def test_password_auth_direct():
    identity, err = authenticate_password("pm.demo", "pm-pass")
    assert err is None
    assert identity["user_id"] == "pm.demo"
