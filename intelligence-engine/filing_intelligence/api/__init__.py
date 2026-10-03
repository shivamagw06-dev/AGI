"""API surface; routes wired in app.api.routes."""

API_ROUTES = [
    "GET /v1/filing-intelligence/health",
    "GET /v1/filing-intelligence/dashboard",
    "GET /v1/filing-intelligence/company/{ticker}",
    "GET /v1/filing-intelligence/history/{ticker}",
    "GET /v1/filing-intelligence/timeline/{ticker}",
    "POST /v1/filing-intelligence/analyse",
    "GET /v1/filing-intelligence/evidence/{ticker}",
    "POST /v1/filing-intelligence/ingest",
    "GET /v1/filing-intelligence/quality-gates",
    "GET /admin/filing-intelligence",
]
