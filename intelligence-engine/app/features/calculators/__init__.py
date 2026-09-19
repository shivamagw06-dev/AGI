"""Built-in feature calculators for WS03."""

from app.features.calculators.external import register_external_category_stubs
from app.features.calculators.fund import register_fund_calculators
from app.features.calculators.macro import register_macro_calculators
from app.features.calculators.tech import register_tech_calculators
from app.features.calculators.universe import register_universe_calculators
from app.features.calculators.vol import register_vol_calculators


def register_builtin_calculators(service: object) -> None:
    register_universe_calculators(service)
    register_tech_calculators(service)
    register_vol_calculators(service)
    register_macro_calculators(service)
    register_fund_calculators(service)
    register_external_category_stubs(service)
