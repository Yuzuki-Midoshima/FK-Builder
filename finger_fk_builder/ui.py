"""PySide6 user interface for Finger FK Builder."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtWidgets

from .builder import FingerFKBuilder
from .utils import FingerFKError, selected_joint, selected_transform


class CollapsibleSection(QtWidgets.QWidget):
    """A compact disclosure section for optional settings."""

    def __init__(
        self,
        title: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.toggle = QtWidgets.QToolButton(text=title, checkable=True)
        self.toggle.setChecked(False)
        self.toggle.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.content = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 2, 0, 4)
        self.content.setVisible(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toggle)
        layout.addWidget(self.content)
        self.toggle.toggled.connect(self._set_expanded)
        self._set_expanded(False)

    @QtCore.Slot(bool)
    def _set_expanded(self, expanded: bool) -> None:
        icon = (
            QtCore.Qt.DownArrow
            if expanded
            else QtCore.Qt.RightArrow
        )
        self.toggle.setArrowType(icon)
        self.content.setVisible(expanded)


class FingerFKBuilderWindow(QtWidgets.QDialog):
    """Minimal portfolio UI; all scene operations are delegated."""

    WINDOW_TITLE = "Finger-FK-Builder"
    COLOR_OPTIONS = (
        ("No Color", None),
        ("Red", 13),
        ("Blue", 6),
        ("Yellow", 17),
        ("Green", 14),
        ("Purple", 9),
        ("Light Blue", 18),
        ("Cyan", 27),
        ("Violet", 29),
        ("Pink", 20),
        ("Orange", 21),
        ("Dark Red", 4),
        ("White", 16),
    )
    DEFAULT_FINGER_COLORS = {
        "thumb": 13,
        "index": 6,
        "middle": 17,
        "ring": 14,
        "pinky": 9,
    }
    COLOR_PRESETS = {
        "cool": {
            "thumb": 18,
            "index": 6,
            "middle": 14,
            "ring": 27,
            "pinky": 29,
        },
        "warm": {
            "thumb": 13,
            "index": 21,
            "middle": 17,
            "ring": 20,
            "pinky": 4,
        },
    }

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        cmds: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self.builder = FingerFKBuilder(cmds=cmds)
        self.cmds = self.builder.cmds
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName("FingerFKBuilderWindow")
        self.setMinimumWidth(380)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self._create_widgets()
        self._create_layout()
        self._connect_signals()
        self.log("Ready.", clear=True)

    def _create_widgets(self) -> None:
        self.root_field = QtWidgets.QLineEdit()
        self.root_field.setReadOnly(True)
        self.set_button = QtWidgets.QPushButton("SET")
        self.visibility_field = QtWidgets.QLineEdit()
        self.visibility_field.setReadOnly(True)
        self.visibility_field.setPlaceholderText(
            "Optional - leave empty to skip"
        )
        self.visibility_set_button = QtWidgets.QPushButton("SET")
        self.visibility_clear_button = QtWidgets.QPushButton("CLEAR")
        self.size_spin = QtWidgets.QDoubleSpinBox()
        self.size_spin.setRange(0.001, 10000.0)
        self.size_spin.setDecimals(3)
        self.size_spin.setValue(1.0)
        self.lock_section = CollapsibleSection("Channel Lock")
        self.lock_checkboxes: dict[str, QtWidgets.QCheckBox] = {}
        lock_grid = QtWidgets.QGridLayout()
        rows = (
            ("Translate", "translate", True),
            ("Rotate", "rotate", False),
            ("Scale", "scale", True),
        )
        for row, (label, prefix, checked) in enumerate(rows):
            lock_grid.addWidget(QtWidgets.QLabel(label), row, 0)
            for column, axis in enumerate("XYZ", start=1):
                attribute = prefix + axis
                checkbox = QtWidgets.QCheckBox(axis)
                checkbox.setChecked(checked)
                self.lock_checkboxes[attribute] = checkbox
                lock_grid.addWidget(checkbox, row, column)

        visibility = QtWidgets.QCheckBox("Visibility")
        visibility.setChecked(True)
        self.lock_checkboxes["visibility"] = visibility
        lock_grid.addWidget(visibility, len(rows), 0, 1, 4)
        self.lock_section.content_layout.addLayout(lock_grid)

        self.color_section = CollapsibleSection("Controller Color")
        self.color_combos: dict[str, QtWidgets.QComboBox] = {}
        color_form = QtWidgets.QFormLayout()
        for finger in ("thumb", "index", "middle", "ring", "pinky"):
            combo = QtWidgets.QComboBox()
            for label, color_index in self.COLOR_OPTIONS:
                combo.addItem(label, color_index)
            default_index = combo.findData(
                self.DEFAULT_FINGER_COLORS[finger]
            )
            combo.setCurrentIndex(default_index)
            self.color_combos[finger] = combo
            color_form.addRow(finger.title(), combo)

        self.cool_set_button = QtWidgets.QPushButton("COOL SET")
        self.warm_set_button = QtWidgets.QPushButton("WARM SET")
        self.reset_color_button = QtWidgets.QPushButton("RESET")
        self.cool_set_button.setCheckable(True)
        self.warm_set_button.setCheckable(True)
        preset_style = (
            "QPushButton:checked {"
            " background-color: #3f3f3f;"
            " border: 1px solid #777777;"
            "}"
        )
        reset_style = (
            "QPushButton:pressed {"
            " background-color: #3f3f3f;"
            " border: 1px solid #777777;"
            "}"
        )
        self.cool_set_button.setStyleSheet(preset_style)
        self.warm_set_button.setStyleSheet(preset_style)
        self.reset_color_button.setStyleSheet(reset_style)
        self.color_preset_group = QtWidgets.QButtonGroup(self)
        self.color_preset_group.setExclusive(True)
        self.color_preset_group.addButton(self.cool_set_button)
        self.color_preset_group.addButton(self.warm_set_button)
        self.cool_set_button.setFixedWidth(88)
        self.warm_set_button.setFixedWidth(88)
        self.reset_color_button.setFixedWidth(88)
        preset_buttons = QtWidgets.QVBoxLayout()
        preset_buttons.addStretch(1)
        preset_buttons.addWidget(self.cool_set_button)
        preset_buttons.addSpacing(6)
        preset_buttons.addWidget(self.warm_set_button)
        preset_buttons.addSpacing(6)
        preset_buttons.addWidget(self.reset_color_button)
        preset_buttons.addStretch(1)

        color_row = QtWidgets.QHBoxLayout()
        color_row.addLayout(color_form)
        color_row.addSpacing(18)
        color_row.addLayout(preset_buttons)
        color_row.addStretch(1)
        self.color_section.content_layout.addLayout(color_row)

        self.include_end_radio = QtWidgets.QRadioButton("Include")
        self.exclude_end_radio = QtWidgets.QRadioButton("Exclude")
        self.include_end_radio.setChecked(True)
        self.end_joint_group = QtWidgets.QButtonGroup(self)
        self.end_joint_group.addButton(self.include_end_radio)
        self.end_joint_group.addButton(self.exclude_end_radio)
        self.build_button = QtWidgets.QPushButton("BUILD FK")
        self.build_button.setMinimumHeight(36)
        self.log_output = QtWidgets.QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(200)
        self.log_output.setMinimumHeight(150)

    def _create_layout(self) -> None:
        form = QtWidgets.QFormLayout()
        root_row = QtWidgets.QHBoxLayout()
        root_row.addWidget(self.root_field, 1)
        root_row.addWidget(self.set_button)
        form.addRow("Root Joint", root_row)
        visibility_row = QtWidgets.QHBoxLayout()
        visibility_row.addWidget(self.visibility_field, 1)
        visibility_row.addWidget(self.visibility_set_button)
        visibility_row.addWidget(self.visibility_clear_button)
        form.addRow("Visibility Control (Optional)", visibility_row)
        form.addRow("Controller Size", self.size_spin)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.lock_section)
        layout.addWidget(self.color_section)
        end_joint_row = QtWidgets.QHBoxLayout()
        end_joint_row.addWidget(QtWidgets.QLabel("End Joint Controller"))
        end_joint_row.addStretch(1)
        end_joint_row.addWidget(self.include_end_radio)
        end_joint_row.addWidget(self.exclude_end_radio)
        layout.addLayout(end_joint_row)
        layout.addWidget(self.build_button)
        layout.addWidget(QtWidgets.QLabel("Log"))
        layout.addWidget(self.log_output)

    def _connect_signals(self) -> None:
        self.set_button.clicked.connect(self.set_root_joint)
        self.visibility_set_button.clicked.connect(
            self.set_visibility_controller
        )
        self.visibility_clear_button.clicked.connect(
            self.clear_visibility_controller
        )
        self.cool_set_button.clicked.connect(
            lambda: self.apply_color_preset("cool")
        )
        self.warm_set_button.clicked.connect(
            lambda: self.apply_color_preset("warm")
        )
        self.reset_color_button.clicked.connect(
            lambda: self.apply_color_preset("default")
        )
        for combo in self.color_combos.values():
            combo.currentIndexChanged.connect(
                self.sync_color_preset_buttons
            )
        self.build_button.clicked.connect(self.build_fk)
        self.sync_color_preset_buttons()

    @QtCore.Slot()
    def set_root_joint(self) -> None:
        try:
            root = selected_joint(self.cmds)
            joints = self.builder.inspect(root)
        except (FingerFKError, RuntimeError) as exc:
            self.log("Error: {0}".format(exc), clear=True)
            return
        self.root_field.setText(root)
        self.log("{0} joints detected.".format(len(joints)), clear=True)

    @QtCore.Slot()
    def set_visibility_controller(self) -> None:
        try:
            controller = selected_transform(self.cmds)
        except FingerFKError as exc:
            self.log("Error: {0}".format(exc), clear=True)
            return
        self.visibility_field.setText(controller)
        self.log(
            "Visibility Controller set: {0}".format(controller),
            clear=True,
        )

    @QtCore.Slot()
    def clear_visibility_controller(self) -> None:
        """Remove the optional visibility-controller assignment."""
        self.visibility_field.clear()
        self.log("Visibility Controller: Not used.", clear=True)

    @QtCore.Slot()
    def build_fk(self) -> None:
        self.log_output.clear()
        try:
            result = self.builder.build(
                root_joint=self.root_field.text().strip(),
                controller_size=self.size_spin.value(),
                log=self.log,
                lock_channels=self.selected_lock_channels(),
                visibility_controller=(
                    self.visibility_field.text().strip() or None
                ),
                finger_colors=self.selected_finger_colors(),
                include_end_joint=self.include_end_radio.isChecked(),
            )
        except Exception as exc:
            self.log("Error: {0}".format(exc))
            return
        self.log("{0} controllers created.".format(len(result.controllers)))
        self.log("Build Complete.")

    def log(self, message: str, clear: bool = False) -> None:
        if clear:
            self.log_output.clear()
        self.log_output.appendPlainText(message)

    def selected_lock_channels(self) -> tuple[str, ...]:
        """Return channel names currently enabled in the lock section."""
        return tuple(
            attribute
            for attribute, checkbox in self.lock_checkboxes.items()
            if checkbox.isChecked()
        )

    def selected_finger_colors(self) -> dict[str, int | None]:
        """Return Maya color indices selected for each finger."""
        return {
            finger: combo.currentData()
            for finger, combo in self.color_combos.items()
        }

    def apply_color_preset(self, preset_name: str) -> None:
        """Apply a default, warm, or cool palette to all fingers."""
        preset = (
            self.DEFAULT_FINGER_COLORS
            if preset_name == "default"
            else self.COLOR_PRESETS[preset_name]
        )
        for finger, color_index in preset.items():
            combo = self.color_combos[finger]
            combo.blockSignals(True)
            index = combo.findData(color_index)
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.blockSignals(False)
        buttons = {
            "cool": self.cool_set_button,
            "warm": self.warm_set_button,
        }
        if preset_name in buttons:
            buttons[preset_name].setChecked(True)
        else:
            self._clear_color_preset_selection()

    @QtCore.Slot()
    def sync_color_preset_buttons(self) -> None:
        """Highlight only the preset matching the current color choices."""
        selected = self.selected_finger_colors()
        matching_button = None
        if selected == self.COLOR_PRESETS["cool"]:
            matching_button = self.cool_set_button
        elif selected == self.COLOR_PRESETS["warm"]:
            matching_button = self.warm_set_button
        if matching_button is None:
            self._clear_color_preset_selection()
        else:
            matching_button.setChecked(True)

    def _clear_color_preset_selection(self) -> None:
        """Clear the persistent COOL/WARM selection."""
        self.color_preset_group.setExclusive(False)
        self.cool_set_button.setChecked(False)
        self.warm_set_button.setChecked(False)
        self.color_preset_group.setExclusive(True)
