"""Entity Intelligence — verified entity contract (P0).

Single authority for entity identification. Sits BEFORE Knowledge Unification.
Wrong-company binding is a release blocker.
"""

from __future__ import annotations

EI_VERSION = "1.0.0"
PROGRAMME = "Entity Intelligence & Verified Entity Contract"
SPEC = "AGI-ENTITY-INTELLIGENCE-1.0"

# Contract states — no other state is allowed for company-shaped asks.
STATE_VERIFIED_ENTITY = "verified_entity"
STATE_VERIFIED_CONCEPT = "verified_concept"
STATE_VERIFIED_INDUSTRY = "verified_industry"
STATE_VERIFIED_MACRO = "verified_macro"
STATE_CLARIFICATION_REQUIRED = "clarification_required"
STATE_UNSUPPORTED_ENTITY = "unsupported_entity"

CONTRACT_STATES = (
    STATE_VERIFIED_ENTITY,
    STATE_VERIFIED_CONCEPT,
    STATE_VERIFIED_INDUSTRY,
    STATE_VERIFIED_MACRO,
    STATE_CLARIFICATION_REQUIRED,
    STATE_UNSUPPORTED_ENTITY,
)

# Confidence thresholds (spec)
CONFIDENCE_VERIFIED = 0.95
CONFIDENCE_CLARIFY_MIN = 0.80
# Below CLARIFY_MIN → do not execute planner (clarification or unsupported)

COVERAGE_FULL = "full_institutional"
COVERAGE_LIMITED = "limited_public_private"
COVERAGE_INSUFFICIENT = "insufficient_institutional"
COVERAGE_NONE = "none"

LISTING_PUBLIC = "public"
LISTING_PRIVATE = "private"
LISTING_UNKNOWN = "unknown"
