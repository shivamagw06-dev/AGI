"""Soft collectors — bridge CGL / KF / FSE / IEP / KIL by evidence class."""

from institutional_coverage_factory.collectors.dispatch import (
    COLLECTOR_IDS,
    dispatch_collectors,
    run_collector,
)

__all__ = ["COLLECTOR_IDS", "dispatch_collectors", "run_collector"]
