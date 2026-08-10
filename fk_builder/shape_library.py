"""Load the bundled MOX controller-shape library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_mox_shapes() -> dict[str, dict[str, Any]]:
    """Return bundled MOX shapes keyed by their stable shape ID."""
    path = Path(__file__).resolve().parent / "data" / "mox_shapes.json"
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    return dict(payload.get("shapes", {}))
