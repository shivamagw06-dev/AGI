"""P2.3 Ownership Intelligence — NSE Master + XBRL (evidence layer only)."""

from __future__ import annotations

from decision_engine.readiness_gate import compute_coverage_board
from ownership_intelligence.dates import fiscal_quarter_label, parse_nse_date
from ownership_intelligence.enrich import merge_ownership_into_dossier
from ownership_intelligence.intelligence import derive_observations
from ownership_intelligence.master import normalize_master_row
from ownership_intelligence.production import analyse, health, package_for_ask_agi
from ownership_intelligence.schema import IC10_UNIVERSE, WORKSTREAM_ID
from ownership_intelligence.xbrl import parse_shp_xbrl
from phase2_investment_intelligence.contract import validate_engine_payload
from phase2_investment_intelligence.workstreams import WORKSTREAMS


def _master_row(
    *,
    date: str,
    promoter: str,
    public: str,
    emp: str = "0",
    symbol: str = "TCS",
    xbrl: str = "https://example.test/shp.xml",
) -> dict:
    return {
        "date": date,
        "pr_and_prgrp": promoter,
        "public_val": public,
        "employeeTrusts": emp,
        "symbol": symbol,
        "name": symbol,
        "isin": "INE000000000",
        "recordId": "1",
        "submissionDate": date,
        "broadcastDate": date + " 10:00:00",
        "xbrl": xbrl,
        "remarksWeb": "N",
    }


def _xbrl(
    *,
    promoter: float,
    public: float,
    fii: float,
    dii: float,
    mf: float,
    insurance: float,
    pledged: bool = False,
    pledge_pct: float | None = 0.0,
) -> str:
    """Minimal SHP-shaped XBRL for unit tests."""

    def fact(ctx: str, pct_unit: float) -> str:
        return (
            f'<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares '
            f'contextRef="{ctx}" unitRef="pure" decimals="4">{pct_unit:.4f}'
            f"</in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares>"
        )

    contexts = [
        "ShareholdingOfPromoterAndPromoterGroup_ContextI",
        "PublicShareholding_ContextI",
        "InstitutionsForeign_ContextI",
        "InstitutionsDomestic_ContextI",
        "MutualFundsOrUTI_ContextI",
        "InsuranceCompanies_ContextI",
        "Banks_ContextI",
        "AlternativeInvestmentFunds_ContextI",
        "ProvidentFundsOrPensionFunds_ContextI",
    ]
    ctx_xml = "".join(
        f'<xbrli:context id="{c}">'
        f"<xbrli:entity><xbrli:identifier scheme='s'>1</xbrli:identifier></xbrli:entity>"
        f"<xbrli:period><xbrli:instant>2026-06-30</xbrli:instant></xbrli:period>"
        f"</xbrli:context>"
        for c in contexts
    )
    facts = "".join(
        [
            fact("ShareholdingOfPromoterAndPromoterGroup_ContextI", promoter / 100.0),
            fact("PublicShareholding_ContextI", public / 100.0),
            fact("InstitutionsForeign_ContextI", fii / 100.0),
            fact("InstitutionsDomestic_ContextI", dii / 100.0),
            fact("MutualFundsOrUTI_ContextI", mf / 100.0),
            fact("InsuranceCompanies_ContextI", insurance / 100.0),
            fact("Banks_ContextI", 0.0001),
            fact("AlternativeInvestmentFunds_ContextI", 0.001),
            fact("ProvidentFundsOrPensionFunds_ContextI", 0.005),
        ]
    )
    pledge_bool = "true" if pledged else "false"
    pledge_fact = ""
    if pledge_pct is not None:
        pledge_fact = (
            f'<in-bse-shp:PercentageOfSharesPledgedOrOtherwiseEncumbered '
            f'contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI" '
            f'unitRef="pure" decimals="4">{pledge_pct / 100.0:.4f}'
            f"</in-bse-shp:PercentageOfSharesPledgedOrOtherwiseEncumbered>"
        )
    return (
        '<?xml version="1.0"?>'
        '<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
        'xmlns:in-bse-shp="http://www.bseindia.com/xbrl/shp">'
        f"{ctx_xml}{facts}{pledge_fact}"
        f"<in-bse-shp:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledgedForPromoterAndPromoterGroup>"
        f"{pledge_bool}</in-bse-shp:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledgedForPromoterAndPromoterGroup>"
        "</xbrli:xbrl>"
    )


def test_parse_nse_date_not_truncated():
    assert parse_nse_date("30-JUN-2026") == "2026-06-30"
    assert parse_nse_date("31-MAR-2026") == "2026-03-31"
    assert fiscal_quarter_label("2026-06-30") == "Q1 FY27"


def test_master_field_mapping_pr_and_prgrp():
    row = normalize_master_row(
        _master_row(date="30-JUN-2026", promoter="71.77", public="28.23"),
        entity="TCS",
    )
    assert row["promoter"] == 71.77
    assert row["public"] == 28.23
    assert row["period_end"] == "2026-06-30"
    assert row["raw"]["pr_and_prgrp"] == "71.77"


def test_xbrl_parser_categories_and_pledge():
    raw = _xbrl(
        promoter=71.77,
        public=28.23,
        fii=9.06,
        dii=13.47,
        mf=5.68,
        insurance=6.71,
        pledged=False,
        pledge_pct=0.0,
    )
    d = parse_shp_xbrl(raw)
    assert d["ok"] is True
    assert abs(d["promoter"] - 71.77) < 0.01
    assert abs(d["fii"] - 9.06) < 0.01
    assert abs(d["dii"] - 13.47) < 0.01
    assert abs(d["mutual_funds"] - 5.68) < 0.01
    assert abs(d["insurance"] - 6.71) < 0.01
    assert d["promoter_pledge"] is False
    assert d["promoter_pledge_pct"] == 0.0


def test_analyse_injected_ic_profiles_differentiate():
    profiles = {
        "TCS": dict(promoter=71.77, public=28.23, fii=9.06, dii=13.47, mf=5.68, insurance=6.71),
        "HDFCBANK": dict(promoter=0.0, public=100.0, fii=41.83, dii=41.92, mf=30.62, insurance=7.37),
        "HAL": dict(promoter=71.64, public=28.36, fii=9.34, dii=11.98, mf=6.79, insurance=4.4),
        "RELIANCE": dict(promoter=50.48, public=49.52, fii=17.2, dii=21.19, mf=10.11, insurance=9.2),
        "ETERNAL": dict(promoter=0.0, public=95.39, fii=29.08, dii=39.32, mf=31.68, insurance=4.21),
    }
    packs = {}
    for t, p in profiles.items():
        master = [
            _master_row(date="30-JUN-2026", promoter=str(p["promoter"]), public=str(p["public"]), symbol=t),
            _master_row(date="31-MAR-2026", promoter=str(p["promoter"]), public=str(p["public"]), symbol=t),
        ]
        xbrl = {
            "2026-06-30": _xbrl(**p, pledged=False, pledge_pct=0.0),
            "2026-03-31": _xbrl(**p, pledged=False, pledge_pct=0.0),
        }
        packs[t] = analyse(
            t,
            injected_master=master,
            injected_xbrl_by_period=xbrl,
            persist=False,
            xbrl_quarters=2,
        )
        assert packs[t]["ok"] is True
        assert packs[t]["missing"] is False
        assert packs[t]["promoter"] is not None
        assert packs[t]["public"] is not None
        assert packs[t]["fii"] is not None
        assert packs[t]["dii"] is not None
        assert packs[t]["mutual_funds"] is not None
        assert packs[t]["insurance"] is not None
        assert packs[t]["promoter_pledge"] is False
        assert packs[t]["as_of_quarter"] == "2026-06-30"
        assert packs[t]["intelligence"]["observations"]
        v = validate_engine_payload(packs[t])
        assert v["ok"] is True, v

    # Differentiation — no hardcoded company logic; structure differs
    assert packs["TCS"]["promoter"] > 60
    assert packs["HDFCBANK"]["promoter"] == 0.0
    assert packs["HDFCBANK"]["fii"] + packs["HDFCBANK"]["dii"] > 70
    assert "Institutionally owned" in packs["HDFCBANK"]["intelligence"]["observations"]
    assert "Promoter controlled" in packs["TCS"]["intelligence"]["observations"]
    assert "Promoter controlled" in packs["HAL"]["intelligence"]["observations"]
    assert "Mixed promoter + institutional ownership" in packs["RELIANCE"]["intelligence"]["observations"]


def test_cid_merge_and_readiness_not_missing():
    master = [
        _master_row(date="30-JUN-2026", promoter="71.77", public="28.23"),
        _master_row(date="31-MAR-2026", promoter="71.77", public="28.23"),
    ]
    xbrl = {
        "2026-06-30": _xbrl(
            promoter=71.77, public=28.23, fii=9.06, dii=13.47, mf=5.68, insurance=6.71
        )
    }
    pack = analyse(
        "TCS",
        injected_master=master,
        injected_xbrl_by_period=xbrl,
        persist=False,
        xbrl_quarters=1,
    )
    dossier = merge_ownership_into_dossier({"ticker": "TCS", "management": {"ownership": {}}}, pack)
    assert dossier["ownership"]["promoter"] == 71.77
    assert dossier["ownership"]["fii"] == 9.06
    assert dossier["shareholding"]["promoter"] == 71.77
    assert dossier["ownership"]["missing"] is False

    board = compute_coverage_board(layers={}, cid=dossier, company_analysis={})
    dims = board.get("dimensions") or {}
    # Gate reports ownership populated (threshold logic unchanged)
    assert float(dims.get("ownership") or 0) >= 80.0


def test_workstream_marked_implemented():
    row = next(w for w in WORKSTREAMS if w["id"] == "P2.3")
    assert row["status"] == "implemented"
    assert row["package"] == "ownership_intelligence"
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["engine"] == "ownership_intelligence"


def test_package_for_ask_agi_degrades_without_ticker():
    pack = package_for_ask_agi("what is ownership?")
    assert pack.get("skipped") is True
    assert pack["failure_mode"]["block_unrelated_engines"] is False


def test_shareholding_connector_maps_master_fields():
    from institutional_data.connectors.shareholding import ShareholdingConnector

    c = ShareholdingConnector()
    injected = [
        {
            "entity": "TCS",
            "period": "2026-06-30",
            "period_end": "2026-06-30",
            "promoter": 71.77,
            "public": 28.23,
            "fii": 9.06,
            "dii": 13.47,
            "mutual_funds": 5.68,
            "insurance": 6.71,
            "pledged": 0.0,
            "promoter_pledge": False,
            "source": "nse_master",
        }
    ]
    res = c.collect(entity="TCS", injected=injected)
    assert res.ok is True
    norm = c.normalize(res.records, entity="TCS")
    assert norm[0]["promoter"] == 71.77
    assert norm[0]["period_end"] == "2026-06-30"
    assert c.validate(norm)["ok"] is True


def test_observations_no_buy_sell_language():
    obs = derive_observations(
        {"promoter": 71.77, "fii": 9.0, "dii": 13.0, "mutual_funds": 5.0, "insurance": 6.0, "public": 28.0, "promoter_pledge": False, "promoter_pledge_pct": 0.0},
        qoq={"deltas_pp": {"fii": 0.5, "mutual_funds": 0.3}},
    )
    blob = " ".join(obs).lower()
    assert "buy" not in blob
    assert "sell" not in blob or "fii selling" in blob  # analytical "FII selling" ok
    assert "promoter controlled" in blob


def test_ic10_universe_constant():
    assert len(IC10_UNIVERSE) == 10
    assert "ETERNAL" in IC10_UNIVERSE
