"""Connector surface — every collector exposes collect/validate/normalize/store/health/coverage."""

from institutional_data.connectors.base import Connector, ConnectorResult
from institutional_data.connectors.registry import all_connectors, get_connector

__all__ = ["Connector", "ConnectorResult", "get_connector", "all_connectors"]
