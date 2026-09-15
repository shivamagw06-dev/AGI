"""Extraction adapters — parse raw documents into structured values only."""

from financial_statements_engine.extraction.nse_xbrl import extract_from_earnings_pack

__all__ = ["extract_from_earnings_pack"]
