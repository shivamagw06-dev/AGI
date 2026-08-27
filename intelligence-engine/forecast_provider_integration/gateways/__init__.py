"""Knowledge-platform collector gateways — never imported by forecast reasoning path."""

from forecast_provider_integration.gateways.groww import GrowwMarketGateway
from forecast_provider_integration.gateways.yahoo import YahooFinancialGateway
from forecast_provider_integration.gateways.nse import NseDisclosureGateway
from forecast_provider_integration.gateways.bse import BseActionsGateway
from forecast_provider_integration.gateways.company_ir import CompanyIrGateway

__all__ = [
    "GrowwMarketGateway",
    "YahooFinancialGateway",
    "NseDisclosureGateway",
    "BseActionsGateway",
    "CompanyIrGateway",
]
