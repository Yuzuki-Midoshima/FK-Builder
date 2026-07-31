"""Standalone Maya launcher for Finger-FK-Builder."""

from __future__ import annotations

from pathlib import Path
import sys


def launch():
    """Clear stale package modules and show the standalone tool."""
    tool_root = str(Path(__file__).resolve().parent)
    if tool_root not in sys.path:
        sys.path.insert(0, tool_root)

    # The tool may previously have been imported from another directory.
    # Remove that cached package so Python resolves it from this tool root.
    module_names = [
        name
        for name in sys.modules
        if name == "finger_fk_builder"
        or name.startswith("finger_fk_builder.")
    ]
    for name in sorted(module_names, reverse=True):
        del sys.modules[name]

    from finger_fk_builder.main import show

    return show()


if __name__ == "__main__":
    launch()
