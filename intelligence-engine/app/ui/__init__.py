"""UI Aggregation Layer — client-facing facades over Investment Office platforms.

Architecture v1.0.1 LOCKED.
No redesign of platforms or engines.
Does not expose internal engine names to public clients.
Soft-consumes AWS / KIP / RSP / RMS / IOC / CRE / Validation only.
"""

from app.ui.service import UiService

__all__ = ["UiService"]
