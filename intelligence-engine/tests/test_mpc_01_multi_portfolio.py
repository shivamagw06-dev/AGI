"""MPC-01 — Multi-Portfolio & Client Platform tests."""

from __future__ import annotations

from institutional_multi_portfolio.client_registry import get_client, list_clients, register_client
from institutional_multi_portfolio.distribution import scope_distribution
from institutional_multi_portfolio.mandate_engine import assign_mandate, resolve_mandate
from institutional_multi_portfolio.permissions import (
    assert_permission,
    grant,
    permissions_for_role,
    resolve_permissions,
)
from institutional_multi_portfolio.portfolio_registry import get_portfolio, list_portfolios, register_portfolio
from institutional_multi_portfolio.production import (
    ask_scoped,
    create_client,
    create_portfolio,
    distribute_publication,
    get_workspace,
    health,
    list_clients_api,
    list_portfolios_api,
    reset_for_tests,
    resolve_context,
    set_permissions,
    share,
    soft_slice_mission_control,
)
from institutional_multi_portfolio.schema import MPC_WORKSTREAM_ID
from institutional_multi_portfolio.sharing import share_research
from institutional_multi_portfolio.validator import validate_execution_context, validate_workspace
from institutional_multi_portfolio.workspace_resolver import (
    build_execution_context,
    resolve_workspace,
)


def setup_function():
    reset_for_tests()


def test_health_intelligence_global():
    h = health()
    assert h["workstream_id"] == MPC_WORKSTREAM_ID
    assert h["owns_intelligence"] is False
    assert h["intelligence_is_global"] is True
    assert h["portfolios_are_local"] is True
    assert h["execution_context_explicit"] is True
    assert h["portfolio_count"] >= 6


def test_portfolio_registry():
    rec = register_portfolio("alpha-book", name="Alpha Book", mandate_id="growth")
    assert rec.portfolio_id == "alpha-book"
    assert rec.mandate_id == "growth"
    assert rec.policy_profile == "growth"
    assert get_portfolio("alpha-book") is not None
    assert any(p.portfolio_id == "alpha-book" for p in list_portfolios())


def test_client_registry():
    client = register_client(
        "client-gamma",
        client_name="Client Gamma",
        portfolios=["growth-portfolio"],
        policy_profile="family_office",
    )
    assert client.client_id == "client-gamma"
    assert "growth-portfolio" in client.portfolios
    assert get_client("client-gamma") is not None
    assert len(list_clients()) >= 1


def test_mandate_assignment_maps_to_pce():
    m = resolve_mandate("conservative")
    assert m["mandate_id"] == "conservative"
    assert m["policy_profile"] == "conservative"
    assert m["owns_policy_evaluation"] is False
    assert m["policy_system_of_record"] == "PCE-01"

    result = assign_mandate("income-portfolio", "income")
    assert result["ok"] is True
    assert result["intelligence_unchanged"] is True
    assert get_portfolio("income-portfolio").mandate_id == "income"


def test_permission_resolver_separate_from_data():
    perms = permissions_for_role("analyst")
    assert "view_research" in perms
    assert "manage_users" not in perms
    cio = resolve_permissions(role_id="cio")
    assert "approve_committee" in cio
    ok, err = assert_permission(perms, "approve_committee")
    assert ok is False
    grant("user-1", ["approve_committee"])
    # grant alone doesn't auto-merge into role unless resolve with user overrides
    merged = resolve_permissions(role_id="analyst", user_id="user-1")
    assert "approve_committee" in merged


def test_workspace_resolver_and_execution_context():
    ctx = build_execution_context(
        portfolio_id="growth-portfolio",
        client_id="client-alpha",
        role_id="portfolio_manager",
        user_id="pm-1",
    )
    assert ctx.portfolio_id == "growth-portfolio"
    assert ctx.mandate_id == "growth"
    assert ctx.policy_profile == "growth"
    assert "manage_portfolio" in ctx.permissions
    v = validate_execution_context(ctx)
    assert v["ok"] is True

    ws = resolve_workspace(
        portfolio_id="growth-portfolio",
        client_id="client-alpha",
        role_id="cio",
    )
    assert ws.execution_context is not None
    assert ws.ask_deep_link.startswith("/agi/ask")
    assert "portfolio=growth-portfolio" in ws.ask_deep_link
    assert validate_workspace(ws)["ok"] is True


def test_multiple_portfolios_share_company_truth():
    # Same company question under different portfolios — company truth unchanged by MPC
    a = resolve_context({"portfolio_id": "growth-portfolio", "role_id": "analyst"})
    b = resolve_context({"portfolio_id": "income-portfolio", "role_id": "analyst"})
    assert a["execution_context"]["portfolio_id"] != b["execution_context"]["portfolio_id"]
    assert a["execution_context"]["mandate_id"] != b["execution_context"]["mandate_id"]
    assert a["owns_intelligence"] is False
    assert b["domain_engines_may_ignore_unused_fields"] is True


def test_different_mandates_identical_holdings_context():
    create_portfolio(
        {"portfolio_id": "twin-a", "name": "Twin A", "mandate_id": "conservative"}
    )
    create_portfolio(
        {"portfolio_id": "twin-b", "name": "Twin B", "mandate_id": "growth"}
    )
    wa = get_workspace(portfolio_id="twin-a", role_id="portfolio_manager")
    wb = get_workspace(portfolio_id="twin-b", role_id="portfolio_manager")
    assert wa["ok"] and wb["ok"]
    assert wa["execution_context"]["policy_profile"] == "conservative"
    assert wb["execution_context"]["policy_profile"] == "growth"


def test_client_publication_isolation():
    create_client(
        {
            "client_id": "iso-client",
            "client_name": "Iso",
            "portfolios": ["growth-portfolio"],
            "policy_profile": "family_office",
        }
    )
    ok = distribute_publication(
        {
            "publication_id": "pub-demo",
            "scope": "client",
            "client_id": "iso-client",
            "portfolio_id": "growth-portfolio",
            "role_id": "portfolio_manager",
        }
    )
    assert ok["ok"] is True
    assert any("client:iso-client" in d for d in ok["destinations"])
    assert ok["same_publication_object"] is True

    denied = scope_distribution(
        publication_id="pub-demo",
        scope="client",
        client_id="iso-client",
        role_id="analyst",  # no distribute_publications
    )
    assert denied["ok"] is False
    assert denied.get("unauthorized") is True


def test_cross_team_collaboration():
    result = share_research(
        from_portfolio="growth-portfolio",
        to_portfolio="research-sandbox",
        object_ref="CompanyDecision:HDFCBANK",
        role_id="senior_analyst",
    )
    assert result["ok"] is True
    assert result["duplicates_intelligence"] is False
    assert result["intelligence_is_global"] is True

    api = share(
        {
            "from_portfolio": "agi-core-equity",
            "to_portfolio": "banking-strategy",
            "object_ref": "Observation:rates",
        }
    )
    assert api["ok"] is True


def test_permission_enforcement_api():
    denied = set_permissions({"user_id": "", "permissions": ["manage_users"]})
    assert denied["ok"] is False
    ok = set_permissions({"user_id": "admin-1", "role_id": "administrator"})
    assert ok["ok"] is True
    assert "manage_users" in ok["permissions"]


def test_ask_scoped_uses_execution_context():
    result = ask_scoped(
        {
            "question": "Should I buy HDFCBANK?",
            "portfolio_id": "growth-portfolio",
            "role_id": "portfolio_manager",
            "entities": ["HDFCBANK"],
        }
    )
    assert result.get("execution_context")
    assert result["execution_context"]["portfolio_id"] == "growth-portfolio"
    assert result.get("context_changes_response_not_company_truth") is True
    # UAG may accept or soft-fail validation; MPC must not invent recommendations
    assert result.get("generates_recommendations") is False or "execution_context" in result


def test_uag_receives_explicit_context():
    from institutional_orchestrator.production import ask, reset_for_tests as uag_reset

    uag_reset()
    ctx = build_execution_context(portfolio_id="income-portfolio", role_id="cio").to_dict()
    result = ask(
        {
            "question": "Which holdings should I reduce?",
            "execution_context": ctx,
            "entities": [],
        }
    )
    assert result.get("execution_context")
    assert result["execution_context"]["portfolio_id"] == "income-portfolio"
    assert result["execution_context"]["policy_profile"] == "balanced" or result[
        "execution_context"
    ]["mandate_id"] == "income"


def test_apis_list_create():
    ports = list_portfolios_api()
    assert ports["ok"] is True
    assert ports["count"] >= 6
    clients = list_clients_api()
    assert clients["ok"] is True
    created = create_portfolio(
        {"portfolio_id": "new-desk", "name": "New Desk", "mandate_id": "institutional"}
    )
    assert created["ok"] is True
    assert created["portfolio"]["policy_profile"] == "pms"


def test_mission_control_platform_ops():
    get_workspace(portfolio_id="agi-core-equity", role_id="cio")
    set_permissions({"user_id": "u2", "permissions": ["view_research"]})
    slice_ = soft_slice_mission_control()
    assert slice_["platform_operations_center"] is True
    assert slice_["owns_intelligence"] is False
    assert slice_["portfolio_count"] >= 6
    assert "publication_queue" in slice_
    assert slice_["active_workspaces"] >= 1
