"""FIML facade — library access layer (not an intelligence engine)."""

from app.fiml.flags import FimlFlags
from app.fiml.service import FimlService

__all__ = ["FimlFlags", "FimlService"]
