"""IO-01 — Institutional Observation Engine."""

from institutional_observation.flags import is_enabled
from institutional_observation.observation import InstitutionalObservation
from institutional_observation.production import (
    get_company_observations,
    health,
    observe_company,
    observation_company,
    soft_slice_mission_control,
)
from institutional_observation.schema import IO_VERSION, IO_WORKSTREAM_ID


def package_version() -> str:
    return IO_VERSION


__all__ = [
    "InstitutionalObservation",
    "IO_VERSION",
    "IO_WORKSTREAM_ID",
    "is_enabled",
    "package_version",
    "health",
    "observe_company",
    "observation_company",
    "get_company_observations",
    "soft_slice_mission_control",
]
