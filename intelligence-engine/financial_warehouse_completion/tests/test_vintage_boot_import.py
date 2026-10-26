"""The HTTP boot path must not replay a large historical warehouse import."""
import pytest

from financial_warehouse_completion import capiq_vintages as cv


@pytest.mark.parametrize("flag", [None, "false", "0", "off"])
def test_boot_does_not_parse_or_write_by_default(monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv("CAPIQ_VINTAGES_BOOT_IMPORT", raising=False)
    else:
        monkeypatch.setenv("CAPIQ_VINTAGES_BOOT_IMPORT", flag)

    def forbidden(*args, **kwargs):
        raise AssertionError("Boot must not open the workbook or mutate the warehouse")

    monkeypatch.setattr(cv, "parse", forbidden)
    monkeypatch.setattr(cv, "write", forbidden)
    assert cv.seed_on_startup() == {
        "ok": True, "skipped": True, "reason": "explicit_import_required",
    }


def test_opt_in_retains_import_behavior(monkeypatch):
    monkeypatch.setenv("CAPIQ_VINTAGES_BOOT_IMPORT", " TRUE\n")
    parsed = {"ok": True, "rows": [{"symbol": "TEST"}]}
    writes = []
    monkeypatch.setattr(cv, "parse", lambda: parsed)
    monkeypatch.setattr(cv, "write", lambda data: writes.append(data) or {"ok": True, "written": 1})
    assert cv.seed_on_startup()["written"] == 1
    assert writes == [parsed]


def test_failed_parse_never_writes(monkeypatch):
    monkeypatch.setenv("CAPIQ_VINTAGES_BOOT_IMPORT", "true")
    monkeypatch.setattr(cv, "parse", lambda: {"ok": False, "error": "missing workbook"})
    monkeypatch.setattr(cv, "write", lambda data: pytest.fail("Must not write failed parse"))
    assert cv.seed_on_startup()["reason"] == "missing workbook"
