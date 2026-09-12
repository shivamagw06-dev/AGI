# MPC-01 — engine notes

Package: `institutional_multi_portfolio`.

## Explicit context

Prefer `execution_context` on request payloads over implicit globals.

Soft consumers:

- UAG-01 `ask()` — reads `portfolio_id` / `policy_profile` from context
- PUB-01 `generate()` — scopes portfolio + optional MPC publication scope
- RW-01 UI — resolves workspace for portfolio strip

## Façades

- `list_portfolios_api` / `create_portfolio`
- `list_clients_api` / `create_client`
- `get_workspace` / `resolve_context` / `ask_scoped`
- `set_permissions` / `distribute_publication`
- `soft_slice_mission_control` → Platform Operations Center

## Tests

`tests/test_mpc_01_multi_portfolio.py`
