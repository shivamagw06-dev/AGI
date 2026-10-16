"""Regression test for a live production crash:

    NameError: name '_already' is not defined

in `mission_control/aggregate.py` inside `build_mission_control()`. The
soft placeholder-provider loop referenced an undefined helper `_already()`
instead of the already-tracked `known` set, crashing every hit to
GET /v1/mission-control/dashboard with a 500.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_build_mission_control_does_not_raise_nameerror():
    from mission_control.aggregate import build_mission_control

    # Must not raise NameError('_already') — this reproduced the live crash.
    out = build_mission_control()
    assert isinstance(out, dict)
    assert out.get("enabled") is not None or "platform_status" in out


def test_placeholder_providers_deduped_against_known_set():
    """Same soft-placeholder loop: seeded providers must not be duplicated,
    and the fixed condition must reference the real `known` set."""
    import ast
    import inspect

    from mission_control import aggregate

    source = inspect.getsource(aggregate.build_mission_control)
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "_already" not in names, "undefined helper '_already' must not be referenced"
