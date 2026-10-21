"""E01 Macro & Regime Engine — P0 threshold vertical slice (E01-001–005).

Consumes Feature Registry / FeatureSnapshots only. No provider payloads.
HMM/ML remain feature-flagged placeholders.
"""

from app.engines.e01.service import E01Service

__all__ = ["E01Service"]
