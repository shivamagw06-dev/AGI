"""AGIB v3.4 Track D — Institutional Communication Engine (ICE)."""

from institutional_communication.production import communicate, communicate_from_ask
from institutional_communication.schema import ICE_VERSION, MODULE_CODE, PROGRAMME

__all__ = [
    "ICE_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "communicate",
    "communicate_from_ask",
]
