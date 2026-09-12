"""Company Dossier Engine (CDE) — living incremental dossiers with provenance."""

from __future__ import annotations

from typing import Any

from app.ail.catalog import COMPANIES
from app.ail.models import DossierVersion, ProvenancedField, utc_now
from app.ail.store import AilStore

DOSSIER_FIELDS = [
    "company_overview",
    "business_model",
    "products",
    "segments",
    "geographies",
    "customers",
    "suppliers",
    "management",
    "board",
    "promoters",
    "shareholding",
    "subsidiaries",
    "competitors",
    "industry_position",
    "financial_statements",
    "quarterly_results",
    "annual_reports",
    "investor_presentations",
    "conference_calls",
    "guidance",
    "capital_allocation",
    "capex",
    "m_and_a",
    "partnerships",
    "patents",
    "esg",
    "government_exposure",
    "risks",
    "catalysts",
    "valuation",
    "timeline",
    "current_investment_thesis",
    "forecast",
    "open_risks",
]


class CompanyDossierEngine:
    def __init__(self, store: AilStore) -> None:
        self.store = store

    def ensure_base(self, ticker: str) -> DossierVersion:
        t = ticker.upper()
        active = self.store.active_dossier(t)
        if active:
            return active
        profile = COMPANIES.get(t) or {"company": t}
        fields: dict[str, ProvenancedField] = {}
        for key in DOSSIER_FIELDS:
            fields[key] = ProvenancedField(value=None, evidence_ids=[], confidence=0.0)
        # seed structural fields without evidence yet — filled by bootstrap claims
        fields["company_overview"].value = profile.get("overview")
        fields["business_model"].value = profile.get("business_model")
        fields["segments"].value = profile.get("segments")
        fields["geographies"].value = profile.get("geographies")
        fields["competitors"].value = profile.get("competitors")
        fields["industry_position"].value = profile.get("industry_position")
        dossier = DossierVersion(
            ticker=t,
            company=str(profile.get("company") or t),
            version=1,
            fields=fields,
        )
        return self.store.put_dossier(dossier)

    def apply_claim(
        self,
        ticker: str,
        *,
        field: str,
        value: Any,
        evidence_ids: list[str],
        confidence: float = 0.7,
    ) -> DossierVersion:
        """Incremental update — create new version only if field value/evidence changes."""
        t = ticker.upper()
        current = self.ensure_base(t)
        key = field if field in current.fields else field
        if key not in DOSSIER_FIELDS:
            key = "company_overview"
        prev = current.fields.get(key) or ProvenancedField()
        new_ids = list(dict.fromkeys([*(prev.evidence_ids or []), *evidence_ids]))
        if prev.value == value and set(prev.evidence_ids or []) == set(new_ids):
            return current

        new_fields = {k: ProvenancedField(**v.to_dict()) for k, v in current.fields.items()}
        new_fields[key] = ProvenancedField(
            value=value,
            evidence_ids=new_ids,
            confidence=max(float(prev.confidence or 0), float(confidence)),
            updated_at=utc_now().isoformat(),
        )
        dossier = DossierVersion(
            ticker=t,
            company=current.company,
            fields=new_fields,
        )
        return self.store.put_dossier(dossier)

    def get(self, ticker: str) -> dict[str, Any]:
        d = self.ensure_base(ticker)
        return {
            "programme": "CDE",
            "ticker": d.ticker,
            "company": d.company,
            "version": d.version,
            "dossier_id": d.dossier_id,
            "fields": {k: v.to_dict() for k, v in d.fields.items()},
            "history_versions": len(self.store.dossiers.get(d.ticker, [])),
            "invariant": "no_free_text_without_evidence_ids_after_bootstrap",
        }
