# AGI v4.0 — Live Integration

```text
COMPANY: AGI
RELEASE: AGI v4.0 Investment Office
STATUS: Landed on main for Hostinger + Render deploy
DATE: 2026-07-28
```

## What went live

1. **Phase 5.1–5.5 on main** — ITE → IDO → IPO → IMO → ILO (+ ICC)
2. **Ask pipeline** exposes thin `investment_office_os` on every Ask
3. **SearchView** + Ask Research Workspace section for Office objects
4. **Node gateway** proxies `/api/intelligence/{thesis,decision,portfolio,monitoring,learning}/*`
5. **Admin desks** — Investment Office + Mission Control paint v4.0 tiles

## Live URLs

| Surface | URL |
|---------|-----|
| Website | https://agarwalglobalinvestments.com |
| Ask | https://agarwalglobalinvestments.com/ask |
| Admin Investment Office | https://agarwalglobalinvestments.com/admin/investment-office |
| Admin Mission Control | https://agarwalglobalinvestments.com/admin/mission-control |
| API gateway | https://finance-news-backend-19i5.onrender.com |

## Deploy triggers

* Push to `main` → Hostinger workflow (frontend root artifacts)
* Push to `main` → Render redeploy (Node API + intelligence-engine Blueprint)

## Hard guarantees held

* No positions / orders / execution  
* Monitoring recommends review only  
* Learning = process memory (no Knowledge Factory mutation)  
* Soft-wire only into Ask / Mission Control / Investment Office UI  
