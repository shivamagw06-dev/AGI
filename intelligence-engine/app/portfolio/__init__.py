"""AGI Portfolio Office — packaging over existing intelligence engines."""

from app.portfolio.normalize import MODEL_PORTFOLIOS, build_snapshot, parse_csv_holdings, sector_exposure
from app.portfolio.pack import (
    attach_portfolio_to_run,
    build_portfolio_package,
    evaluate_scenario,
    ingest_to_snapshot,
    package_from_metadata,
)
from app.portfolio.recommend import attach_to_package, build_action_center, generate_recommendations

__all__ = [
    "MODEL_PORTFOLIOS",
    "build_snapshot",
    "parse_csv_holdings",
    "sector_exposure",
    "build_portfolio_package",
    "ingest_to_snapshot",
    "evaluate_scenario",
    "attach_portfolio_to_run",
    "package_from_metadata",
    "generate_recommendations",
    "build_action_center",
    "attach_to_package",
]
