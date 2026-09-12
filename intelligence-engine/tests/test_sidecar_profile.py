"""The narrow sidecar profile must actually be narrow.

`warehouse_only` selected the profile by exporting WAREHOUSE_* and leaving
everything else unset, on the belief that every loop defaults to off. Two of
them default to *on*, so the profile that existed to keep the engine light
started the forecast runtime, the historical-valuation runtime and three
universe-wide median passes as well.

These assert the defaults rather than the intention, because the intention was
what was wrong.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]


def _worker():
    spec = importlib.util.spec_from_file_location(
        "gw_under_test", ENGINE / "scripts" / "gather_worker.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_two_heavy_runtimes_really_do_default_to_on():
    """The fact the profile was built on top of. If these ever become false by
    default the profile still holds, but the reason for it should be re-read."""
    gw = _worker()
    for name in ("FIE_RUNTIME", "HVIE_RUNTIME"):
        os.environ.pop(name, None)
    assert gw._truthy("FIE_RUNTIME", "true") is True
    assert gw._truthy("HVIE_RUNTIME", "true") is True


@pytest.mark.parametrize("profile,expected", [
    ("warehouse_only", True),
    ("full", False),
    ("forecast_only", False),
    ("", False),
])
def test_profile_is_read_where_the_work_starts(monkeypatch, profile, expected):
    gw = _worker()
    if profile:
        monkeypatch.setenv("AGI_GATHER_SIDECAR_PROFILE", profile)
    else:
        monkeypatch.delenv("AGI_GATHER_SIDECAR_PROFILE", raising=False)
    assert gw.warehouse_only() is expected


def test_profile_survives_the_whitespace_render_adds(monkeypatch):
    """Render's dashboard stores values in textareas; a trailing newline is
    invisible there and fatal to a string comparison."""
    gw = _worker()
    monkeypatch.setenv("AGI_GATHER_SIDECAR_PROFILE", " Warehouse_Only\n")
    assert gw.warehouse_only() is True


def test_the_shell_sets_the_heavy_flags_false_rather_than_leaving_them_unset():
    """Belt and braces: the launcher must not rely on a default staying false."""
    script = (ENGINE / "scripts" / "start_engine.sh").read_text()
    block = script.split('if [[ "${SIDECAR_PROFILE}" == "warehouse_only" ]]; then')[1]
    block = block.split("fi")[0]
    for flag in ("FIE_RUNTIME=false", "HVIE_RUNTIME=false"):
        assert flag in block, f"{flag} must be exported by the warehouse_only profile"
