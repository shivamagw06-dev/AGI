"""Thin Intelligence Engine client for KAIP/KRIG published knowledge (read-only)."""

from app.kaip_client.client import KaipClient, KaipClientError, KrigClient

__all__ = ["KaipClient", "KaipClientError", "KrigClient"]
