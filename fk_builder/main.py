"""Maya entry point for FK-Builder."""

from __future__ import annotations

import importlib
from typing import Any

from PySide6 import QtWidgets
from shiboken6 import wrapInstance

from .ui import FKBuilderWindow

_WINDOW: FKBuilderWindow | None = None


def maya_main_window() -> QtWidgets.QWidget | None:
    """Return Maya's main window as a Qt widget."""
    try:
        from maya import OpenMayaUI

        pointer = OpenMayaUI.MQtUtil.mainWindow()
        return wrapInstance(int(pointer), QtWidgets.QWidget) if pointer else None
    except (ImportError, RuntimeError, TypeError):
        return None


def show() -> Any:
    """Create and show one persistent window instance."""
    global _WINDOW
    if _WINDOW is not None:
        _WINDOW.close()
        _WINDOW.deleteLater()
    _WINDOW = FKBuilderWindow(parent=maya_main_window())
    _WINDOW.show()
    _WINDOW.raise_()
    _WINDOW.activateWindow()
    return _WINDOW


def reload_and_show() -> Any:
    """Reload all package modules and show the latest UI during development."""
    global FKBuilderWindow

    from . import builder, controller, hierarchy, ui, utils

    # Reload dependencies before the modules which import them.
    for module in (utils, controller, hierarchy, builder, ui):
        importlib.reload(module)
    FKBuilderWindow = ui.FKBuilderWindow
    return show()


if __name__ == "__main__":
    show()
