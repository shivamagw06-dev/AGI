"""IRE-02 — Institutional Reporting Engine + Reason Composer (deterministic, no LLM)."""

from institutional_reporting.composer import compose_report
from institutional_reporting.models import InstitutionalReport, InstitutionalReportInput
from institutional_reporting.reason_composer import compose_reasons
from institutional_reporting.reasoning import Reason
from institutional_reporting.schema import IRE_VERSION, IRE_WORKSTREAM_ID

__all__ = [
    "compose_report",
    "compose_reasons",
    "Reason",
    "InstitutionalReport",
    "InstitutionalReportInput",
    "IRE_WORKSTREAM_ID",
    "IRE_VERSION",
]
