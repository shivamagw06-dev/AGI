"""API surface; routes in app.api.routes."""

API_ROUTES = [
    "GET /v1/management-intelligence/health",
    "GET /v1/management-intelligence/dashboard",
    "GET /v1/management-intelligence/company/{ticker}",
    "GET /v1/management-intelligence/history/{ticker}",
    "GET /v1/management-intelligence/guidance/{ticker}",
    "POST /v1/management-intelligence/analyse",
    "GET /v1/management-intelligence/quality-gates",
    "GET /admin/management-intelligence",
]
