"""AOI feature flags — configuration driven enablement."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class AoiFlags:
    aoi: bool = True
    aoi_scheduler: bool = True
    aoi_publish: bool = True
    aoi_live_fetch: bool = False  # offline-safe by default; enable for live HTTP
    aoi_company_ir: bool = True
    aoi_nse: bool = True
    aoi_bse: bool = True
    aoi_rbi: bool = True
    aoi_sebi: bool = True
    aoi_mof: bool = True
    aoi_mospi: bool = True
    aoi_fred: bool = True
    aoi_imf: bool = True
    aoi_worldbank: bool = True
    aoi_pib: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "AoiFlags":
        s = settings or get_settings()
        return cls(
            aoi=bool(getattr(s, "aoi", True)),
            aoi_scheduler=bool(getattr(s, "aoi_scheduler", True)),
            aoi_publish=bool(getattr(s, "aoi_publish", True)),
            aoi_live_fetch=bool(getattr(s, "aoi_live_fetch", False)),
            aoi_company_ir=bool(getattr(s, "aoi_company_ir", True)),
            aoi_nse=bool(getattr(s, "aoi_nse", True)),
            aoi_bse=bool(getattr(s, "aoi_bse", True)),
            aoi_rbi=bool(getattr(s, "aoi_rbi", True)),
            aoi_sebi=bool(getattr(s, "aoi_sebi", True)),
            aoi_mof=bool(getattr(s, "aoi_mof", True)),
            aoi_mospi=bool(getattr(s, "aoi_mospi", True)),
            aoi_fred=bool(getattr(s, "aoi_fred", True)),
            aoi_imf=bool(getattr(s, "aoi_imf", True)),
            aoi_worldbank=bool(getattr(s, "aoi_worldbank", True)),
            aoi_pib=bool(getattr(s, "aoi_pib", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "AOI": self.aoi,
            "AOI_SCHEDULER": self.aoi_scheduler,
            "AOI_PUBLISH": self.aoi_publish,
            "AOI_LIVE_FETCH": self.aoi_live_fetch,
            "AOI_COMPANY_IR": self.aoi_company_ir,
            "AOI_NSE": self.aoi_nse,
            "AOI_BSE": self.aoi_bse,
            "AOI_RBI": self.aoi_rbi,
            "AOI_SEBI": self.aoi_sebi,
            "AOI_MOF": self.aoi_mof,
            "AOI_MOSPI": self.aoi_mospi,
            "AOI_FRED": self.aoi_fred,
            "AOI_IMF": self.aoi_imf,
            "AOI_WORLDBANK": self.aoi_worldbank,
            "AOI_PIB": self.aoi_pib,
        }

    def connector_enabled(self, connector_id: str) -> bool:
        mapping = {
            "company_ir": self.aoi_company_ir,
            "nse": self.aoi_nse,
            "bse": self.aoi_bse,
            "rbi": self.aoi_rbi,
            "sebi": self.aoi_sebi,
            "mof": self.aoi_mof,
            "mospi": self.aoi_mospi,
            "fred": self.aoi_fred,
            "imf": self.aoi_imf,
            "worldbank": self.aoi_worldbank,
            "pib": self.aoi_pib,
        }
        return bool(mapping.get(connector_id, True))
