"""P5 Investment Operations Layer — orchestrates existing intelligence into office workflows."""

from investment_operations.production import health, morning_office, research_queue, run_desk
from investment_operations.schema import ENGINE_CODE, VERSION

__all__ = ["ENGINE_CODE", "VERSION", "health", "morning_office", "research_queue", "run_desk"]
