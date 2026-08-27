"""NSE / BSE SHP XBRL downloader + normalizer.

Extracts institutional ownership categories via contextRef category totals.
Missing tags never fail the parse — fields stay None.
"""

from __future__ import annotations

import re
from typing import Any

from ownership_intelligence.dates import parse_nse_date

# Category totals use *_ContextI ids in SHP V1.1 XBRL
CTX_TO_FIELD = {
    "ShareholdingOfPromoterAndPromoterGroup_ContextI": "promoter",
    "PublicShareholding_ContextI": "public",
    "InstitutionsForeign_ContextI": "fii",
    "InstitutionsForeignPortfolioInvestorCategoryOne_ContextI": "fpi_cat1",
    "InstitutionsForeignPortfolioInvestorCategoryTwo_ContextI": "fpi_cat2",
    "InstitutionsDomestic_ContextI": "dii",
    "MutualFundsOrUTI_ContextI": "mutual_funds",
    "InsuranceCompanies_ContextI": "insurance",
    "Banks_ContextI": "banks",
    "AlternativeInvestmentFunds_ContextI": "aif",
    "ProvidentFundsOrPensionFunds_ContextI": "pension",
    "NonInstitutions_ContextI": "retail",  # non-institutions ≈ retail/others public
    "OtherNonInstitutions_ContextI": "others",
    "ShareholdingByCompaniesOrBodiesCorporateWhereCentralOrStateGovernmentIsPromoter_ContextI": "government",
    "ForeignCompanies_ContextI": "foreign_companies",
    "ForeignNationals_ContextI": "foreign_nationals",
}


def download_xbrl(url: str, *, opener=None) -> bytes:
    from live_data.collectors.base import http_get, nse_session_opener

    op = opener or nse_session_opener()
    return http_get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/xml,text/xml,*/*",
            "Referer": "https://www.nseindia.com/",
        },
        timeout=60,
        opener=op,
    )


def _pct_value(raw: str) -> float | None:
    try:
        v = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    # XBRL uses unit shares; percentages stored as 0.7164 style decimals
    if v <= 1.5:
        v *= 100.0
    return round(v, 4)


def _pct_for_context(text: str, ctx: str) -> float | None:
    # Attribute order may vary
    for m in re.finditer(
        r"<[^>]*ShareholdingAsAPercentageOfTotalNumberOfShares[^>]*>",
        text,
    ):
        tag = m.group(0)
        if f'contextRef="{ctx}"' not in tag:
            continue
        rest = text[m.end() : m.end() + 48]
        vm = re.match(r"\s*([0-9.]+)", rest)
        if vm:
            return _pct_value(vm.group(1))
    return None


def _bool_tag(text: str, local_name: str) -> bool | None:
    m = re.search(rf"{re.escape(local_name)}[^>]*>([^<]+)<", text, re.I)
    if not m:
        return None
    v = m.group(1).strip().lower()
    if v in {"true", "yes", "y", "1"}:
        return True
    if v in {"false", "no", "n", "0"}:
        return False
    return None


def _pledge_pct(text: str) -> float | None:
    """Promoter pledge as % of total share capital (SHP V1.1 field names vary)."""
    patterns = (
        r"EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares"
        r'[^>]*contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI"[^>]*>([^<]+)<',
        r"EncumberedSharesHeldAsPercentageOfTotalNumberOfShares"
        r'[^>]*contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI"[^>]*>([^<]+)<',
        r"NumberOfSharesPledgedOrOtherwiseEncumberedAsAPercentageOfTotalSharesHeld"
        r'[^>]*contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI"[^>]*>([^<]+)<',
        r"PercentageOfSharesPledgedOrOtherwiseEncumbered"
        r'[^>]*contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI"[^>]*>([^<]+)<',
        r"PercentageOfSharesPledged[^>]*contextRef=\"[^\"]*Promoter[^\"]*\"[^>]*>([^<]+)<",
    )
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return _pct_value(m.group(1))
    # Attribute-order tolerant scan for promoter pledge %
    for local in (
        "EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares",
        "EncumberedSharesHeldAsPercentageOfTotalNumberOfShares",
    ):
        for m in re.finditer(rf"<[^>]*{local}[^>]*>", text, re.I):
            tag = m.group(0)
            if 'contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI"' not in tag:
                continue
            rest = text[m.end() : m.end() + 48]
            vm = re.match(r"\s*([0-9.]+)", rest)
            if vm:
                return _pct_value(vm.group(1))
    return None


def parse_shp_xbrl(raw: bytes | str) -> dict[str, Any]:
    """Normalize SHP XBRL into ownership category percentages."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    fields: dict[str, Any] = {}
    for ctx, field in CTX_TO_FIELD.items():
        fields[field] = _pct_for_context(text, ctx)

    # FII total fallback from FPI cat1+cat2
    if fields.get("fii") is None:
        c1, c2 = fields.get("fpi_cat1"), fields.get("fpi_cat2")
        if c1 is not None or c2 is not None:
            fields["fii"] = round((c1 or 0.0) + (c2 or 0.0), 4)

    pledged_flag = _bool_tag(
        text, "WhetherAnySharesHeldByPromotersAreEncumberedUnderPledgedForPromoterAndPromoterGroup"
    )
    if pledged_flag is None:
        pledged_flag = _bool_tag(text, "WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged")

    pledge_pct = _pledge_pct(text)
    # If pledge explicitly false and no %, treat as 0.0 for pack completeness
    if pledge_pct is None and pledged_flag is False:
        pledge_pct = 0.0

    # Instant date from promoter context if present
    as_of = None
    m = re.search(
        r'id="ShareholdingOfPromoterAndPromoterGroup_ContextI".*?<xbrli:instant>([^<]+)</xbrli:instant>',
        text,
        re.S | re.I,
    )
    if m:
        as_of = parse_nse_date(m.group(1))

    return {
        "ok": any(fields.get(k) is not None for k in ("promoter", "public", "fii", "dii", "mutual_funds")),
        "as_of": as_of,
        "promoter": fields.get("promoter"),
        "promoter_group": fields.get("promoter"),  # SHP category is Promoter + Promoter Group
        "public": fields.get("public"),
        "fii": fields.get("fii"),
        "fpi_cat1": fields.get("fpi_cat1"),
        "fpi_cat2": fields.get("fpi_cat2"),
        "dii": fields.get("dii"),
        "mutual_funds": fields.get("mutual_funds"),
        "insurance": fields.get("insurance"),
        "banks": fields.get("banks"),
        "pension": fields.get("pension"),
        "aif": fields.get("aif"),
        "government": fields.get("government"),
        "corporate_bodies": fields.get("government"),  # govt bodies corporate bucket when present
        "retail": fields.get("retail"),
        "others": fields.get("others"),
        "promoter_pledge": pledged_flag,
        "promoter_pledge_pct": pledge_pct,
        "source": "nse_xbrl",
        "fields_present": sorted(k for k, v in fields.items() if v is not None),
    }


def enrich_quarter_with_xbrl(
    quarter: dict[str, Any],
    *,
    opener=None,
    injected_xbrl: bytes | str | None = None,
) -> dict[str, Any]:
    """Download/parse XBRL for one master quarter and merge detail fields."""
    out = dict(quarter)
    url = quarter.get("xbrl_url")
    try:
        if injected_xbrl is not None:
            detail = parse_shp_xbrl(injected_xbrl)
            out["xbrl_mode"] = "injected"
        elif url:
            raw = download_xbrl(str(url), opener=opener)
            detail = parse_shp_xbrl(raw)
            out["xbrl_mode"] = "live"
            out["xbrl_bytes"] = len(raw)
        else:
            out["xbrl_error"] = "xbrl_url_missing"
            return out
    except Exception as exc:  # noqa: BLE001 — never fail pack on one tag/file
        out["xbrl_error"] = f"{type(exc).__name__}:{str(exc)[:160]}"
        return out

    # Prefer XBRL detail when present; keep master promoter/public as fallback
    for key in (
        "promoter",
        "promoter_group",
        "public",
        "fii",
        "dii",
        "mutual_funds",
        "insurance",
        "banks",
        "pension",
        "aif",
        "government",
        "corporate_bodies",
        "retail",
        "others",
        "promoter_pledge",
        "promoter_pledge_pct",
        "fpi_cat1",
        "fpi_cat2",
    ):
        if detail.get(key) is not None:
            out[key] = detail.get(key)
    if out.get("promoter") is None and quarter.get("promoter") is not None:
        out["promoter"] = quarter.get("promoter")
    if out.get("public") is None and quarter.get("public") is not None:
        out["public"] = quarter.get("public")
    if out.get("employee_trusts") is None:
        out["employee_trusts"] = quarter.get("employee_trusts")
    out["xbrl_ok"] = bool(detail.get("ok"))
    out["xbrl_fields_present"] = detail.get("fields_present") or []
    out["detail_source"] = "nse_master+xbrl" if detail.get("ok") else "nse_master"
    return out
