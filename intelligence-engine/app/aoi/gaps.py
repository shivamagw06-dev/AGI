"""Gap detection — missing documents and weak knowledge remediation tasks."""

from __future__ import annotations

from app.aoi.models import GapTask
from app.aoi.registry import CompanyRegistry
from app.aoi.sources_config import EXPECTED_DOC_TYPES_PER_COMPANY
from app.aoi.store import AoiStore


_DOC_LABELS = {
    "annual_report": "Annual Report",
    "quarterly_result": "Quarterly Result",
    "investor_presentation": "Q Presentation",
    "earnings_transcript": "Conference Call / Transcript",
    "esg_report": "ESG Report",
    "shareholding": "Shareholding Pattern",
}


def detect_gaps(store: AoiStore, registry: CompanyRegistry) -> list[GapTask]:
    tasks: list[GapTask] = []
    for co in registry.nifty50():
        arts = [a for a in store.artifacts.values() if a.company_id == co.company_id and a.status not in {"failed"}]
        types = {a.doc_type for a in arts}
        for dtype in EXPECTED_DOC_TYPES_PER_COMPANY:
            if dtype in types:
                continue
            label = _DOC_LABELS.get(dtype, dtype)
            tasks.append(
                GapTask(
                    company_id=co.company_id,
                    kind=f"missing_{dtype}",
                    severity="high" if dtype in {"annual_report", "quarterly_result"} else "medium",
                    title=f"Missing {label}: {co.nse_symbol}",
                    detail=f"{co.company_name} lacks structured {label} in AOI corpus.",
                    suggested_action=f"Run connector discovery for {dtype} on company IR / exchange filings.",
                )
            )
        q = store.quality.get(co.company_id)
        if q and q.overall < 50:
            tasks.append(
                GapTask(
                    company_id=co.company_id,
                    kind="low_quality",
                    severity="critical",
                    title=f"Low knowledge quality: {co.nse_symbol}",
                    detail=f"Overall quality {q.overall}.",
                    suggested_action="Prioritise IR + NSE/BSE refresh and re-extract facts.",
                )
            )
    store.gaps = tasks
    return tasks
