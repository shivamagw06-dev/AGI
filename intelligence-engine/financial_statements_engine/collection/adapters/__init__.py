"""Source adapters for FSE-02 collectors — discovery/download only."""

from financial_statements_engine.collection.adapters.nse import discover_nse

__all__ = ["discover_nse"]
