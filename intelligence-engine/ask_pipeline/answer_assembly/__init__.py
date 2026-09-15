"""AGIB v3.4 Track B — Institutional Answer Assembly Engine."""

from ask_pipeline.answer_assembly.engine import assemble_answer_plan, bind_reasoning_to_answer
from ask_pipeline.answer_assembly.schema import AAE_VERSION, MODULE_CODE, PROGRAMME

__all__ = [
    "AAE_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "assemble_answer_plan",
    "bind_reasoning_to_answer",
]
