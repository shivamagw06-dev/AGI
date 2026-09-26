"""API surface documented here; routes live in app.api.routes (soft-wire)."""

API_ROUTES = [
    "GET /v1/peer-intelligence/health",
    "GET /v1/peer-intelligence/dashboard",
    "GET /v1/peer-intelligence/company/{ticker}",
    "GET /v1/peer-intelligence/compare",
    "POST /v1/peer-intelligence/analyse",
    "GET /v1/peer-intelligence/history/{ticker}",
    "GET /v1/peer-intelligence/rankings",
    "GET /v1/peer-intelligence/quality-gates",
    "GET /admin/peer-intelligence",
]
