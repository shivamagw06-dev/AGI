"""Continuous Research Evaluation (CRE) — P0.

Not a research engine. Not a trading engine.
Evaluates quality of implemented engines from replay/shadow outputs only.
No production influence. PROMOTION remains evidence-only when false.
"""

from app.cre.service import CREService

__all__ = ["CREService"]
