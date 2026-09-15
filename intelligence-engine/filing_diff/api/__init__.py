"""API surface; routes in app.api.routes."""

API_ROUTES = [
    "GET /v1/filing-diff/health",
    "GET /v1/filing-diff/dashboard",
    "GET /v1/filing-diff/company/{ticker}",
    "POST /v1/filing-diff/analyse",
    "GET /v1/filing-diff/timeline/{ticker}",
    "GET /v1/filing-diff/changes/{ticker}",
    "GET /v1/filing-diff/quality-gates",
    "GET /admin/filing-diff",
]
