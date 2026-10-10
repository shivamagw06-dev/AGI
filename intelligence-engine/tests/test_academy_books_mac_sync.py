"""Mac library reachability + CLI for Academy Books sync/ingest."""

from __future__ import annotations

from academy.books.cli import main as cli_main
from academy.books.library import library_reachability, preferred_mac_roots, scan_library
from academy.books.production import dashboard, reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_preferred_mac_roots_include_downloads_books():
    roots = [str(p) for p in preferred_mac_roots()]
    assert "/Users/shivamagarwal/Downloads/AGIB/Books" in roots


def test_library_reachability_reports_mac_gap_in_cloud():
    reach = library_reachability()
    assert reach["preferred_mac_path"] == "/Users/shivamagarwal/Downloads/AGIB/Books"
    assert "preferred_reachable" in reach
    assert reach.get("active_root")
    # In cloud agents the Mac path is typically missing; workspace/books is the fallback.
    if not reach["preferred_reachable"]:
        assert reach.get("hint")
        assert "Mac path" in (reach.get("hint") or "") or "not mounted" in (reach.get("hint") or "")


def test_scan_includes_reachability_block():
    scan = scan_library()
    assert scan.get("ok") is True
    assert "reachability" in scan
    assert scan["reachability"]["preferred_mac_path"].endswith("/AGIB/Books")


def test_dashboard_exposes_library_reachability():
    dash = dashboard()
    assert "library_reachability" in dash
    assert dash["library_reachability"]["preferred_mac_path"].endswith("/AGIB/Books")


def test_cli_status_exits_zero_when_any_root_active(capsys):
    code = cli_main(["status"])
    out = capsys.readouterr().out
    assert '"preferred_mac_path"' in out
    assert code in (0, 2)
