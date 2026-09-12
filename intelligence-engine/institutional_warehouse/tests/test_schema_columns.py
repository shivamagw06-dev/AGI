"""Schema integrity — no duplicate physical columns (breaks SQLite CREATE TABLE)."""

from institutional_warehouse.schema import TABS, workbook


def test_no_duplicate_column_keys():
    for tab in TABS:
        keys = [c.key for c in tab.columns]
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        assert not dupes, f"{tab.id} has duplicate columns: {dupes}"


def test_ingestion_health_feed_not_source_key():
    """Provenance already owns 'source'; identity must use another key."""
    tab = next(t for t in TABS if t.id == "ingestion_health")
    assert tab.key == ("feed",)
    assert "feed" in {c.key for c in tab.columns}
    assert "source" in {c.key for c in tab.columns}  # provenance only once


def test_workbook_loads():
    pack = workbook()
    assert pack["ok"] is True
    assert pack["tab_count"] == len(TABS)
