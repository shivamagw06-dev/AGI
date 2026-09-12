"""Groww collector — portfolio holdings / exposure (fixture-backed)."""

from __future__ import annotations

import os
from typing import Any

from knowledge_factory.collectors.base import ok_dataset, unavailable
from knowledge_factory.fixtures import seed


def collect_portfolio(*, live: bool | None = None) -> dict[str, Any]:
    live = bool(os.environ.get("KF_LIVE_GROWW")) if live is None else live
    if live:
        return unavailable("groww", None, "groww_live_not_configured")
    book = seed.groww_book_fixture()
    return ok_dataset(kind="portfolio_book", entity="BOOK", source="groww", payload=book)
