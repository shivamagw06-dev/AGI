"""AIG Institutional Reasoning Soft Policy.

Teaches AGIB how to think before it answers.
Not a top-level intelligence engine. Soft-wire only.
"""

from __future__ import annotations

from institutional_reasoning.flags import flags_dict, is_enabled
from institutional_reasoning.production import health, package_for_ask_agi, quality_gates, system_prompt
from institutional_reasoning.prompt import INSTITUTIONAL_REASONING_SYSTEM_PROMPT, TOP_RULE
from institutional_reasoning.schema import MODULE_CODE, PROGRAMME, VERSION

__all__ = [
    "INSTITUTIONAL_REASONING_SYSTEM_PROMPT",
    "MODULE_CODE",
    "PROGRAMME",
    "TOP_RULE",
    "VERSION",
    "flags_dict",
    "health",
    "is_enabled",
    "package_for_ask_agi",
    "quality_gates",
    "system_prompt",
]
