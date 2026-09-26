from fastapi import APIRouter, Depends
from app.api.routes import require_token
from app.founder_portfolio.service import FounderPortfolioService
router = APIRouter(prefix="/v1/founder-portfolio", tags=["founder-portfolio"])
@router.get("/health", dependencies=[Depends(require_token)])
async def health(): return FounderPortfolioService().health()
@router.get("/report/latest", dependencies=[Depends(require_token)])
async def latest_report(): return {"ok": True, "report": await FounderPortfolioService().latest_report()}
@router.post("/refresh", dependencies=[Depends(require_token)])
async def refresh():
    report = await FounderPortfolioService().refresh(); return {"ok": report.get("status") == "OK", "report": report}
