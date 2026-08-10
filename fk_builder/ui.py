"""PySide6 user interface for FK-Builder."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtWidgets

from .builder import FKBuilder
from .shape_library import ShapeLibraryError, load_shape_libraries
from .shape_picker import ShapePickerDialog
from .utils import FKBuilderError, selected_joint, selected_transform


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


class ChannelLockSection(CollapsibleSection):
    """Dynamic per-controller channel lock configuration."""

    ATTRIBUTES = tuple(
        prefix + axis
        for prefix in ("translate", "rotate", "scale")
        for axis in "XYZ"
    ) + ("visibility",)
    DEFAULTS = {
        "translateX", "translateY", "translateZ",
        "scaleX", "scaleY", "scaleZ", "visibility",
    }

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("チャンネルロック", parent)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("すべて同じ設定", "all")
        self.mode_combo.addItem("名前の文字で識別", "name")
        self.mode_combo.addItem("階層分岐で識別", "branch")
        self.rows_layout = QtWidgets.QVBoxLayout()
        self.add_button = QtWidgets.QPushButton("グループを追加")
        self.unlock_button = QtWidgets.QPushButton("すべて解除")
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addStretch(1)
        buttons.addWidget(self.unlock_button)
        self.content_layout.addWidget(self.mode_combo)
        self.content_layout.addLayout(self.rows_layout)
        self.content_layout.addLayout(buttons)
        self._branches: list[tuple[str, str]] = []
        defaults = tuple(attr in self.DEFAULTS for attr in self.ATTRIBUTES)
        self._name_values: list[tuple[str, tuple[bool, ...]]] = [
            ("L_", defaults), ("R_", defaults)
        ]
        self._rows: list[
            tuple[str, QtWidgets.QLineEdit | None, dict[str, QtWidgets.QCheckBox]]
        ] = []
        self.mode_combo.currentIndexChanged.connect(self._change_mode)
        self.add_button.clicked.connect(self._add_name_group)
        self.unlock_button.clicked.connect(self.unlock_all)
        self._rebuild()

    def set_branches(self, branches: list[tuple[str, str]]) -> None:
        self._branches = list(branches)
        if self.mode_combo.currentData() == "branch":
            self._rebuild()

    def settings(self) -> tuple[str, dict[str, tuple[str, ...]], list[tuple]]:
        groups = {}
        rules = []
        for key, field, boxes in self._rows:
            selected = tuple(
                attr for attr in self.ATTRIBUTES if boxes[attr].isChecked()
            )
            if field is None:
                groups[key] = selected
            elif field.text().strip():
                rules.append((field.text().strip(), selected))
        return self.mode_combo.currentData(), groups, rules

    def unlock_all(self) -> None:
        for _key, _field, boxes in self._rows:
            for checkbox in boxes.values():
                checkbox.setChecked(False)

    def _capture_names(self) -> None:
        values = []
        for _key, field, boxes in self._rows:
            if field is not None:
                values.append((field.text(), tuple(boxes[a].isChecked() for a in self.ATTRIBUTES)))
        if values:
            self._name_values = values

    def _change_mode(self) -> None:
        self._capture_names()
        self._rebuild()

    def _add_name_group(self) -> None:
        self._capture_names()
        self._name_values.append(("", tuple(a in self.DEFAULTS for a in self.ATTRIBUTES)))
        self._rebuild()

    def _remove_name_group(self, index: int) -> None:
        self._capture_names()
        self._name_values.pop(index)
        self._rebuild()

    def _clear(self) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()

    def _rebuild(self) -> None:
        self._clear()
        mode = self.mode_combo.currentData()
        self.add_button.setVisible(mode == "name")
        defaults = tuple(a in self.DEFAULTS for a in self.ATTRIBUTES)
        if mode == "all":
            self._add_row("__all__", "すべて", None, defaults)
        elif mode == "name":
            for index, (pattern, values) in enumerate(self._name_values):
                self._add_row("name_{0}".format(index), "", pattern, values, index)
        elif not self._branches:
            self.rows_layout.addWidget(QtWidgets.QLabel("ルートジョイントを設定してください"))
        else:
            for key, label in self._branches:
                self._add_row(key, label, None, defaults)

    def _add_row(self, key, label, pattern, values, remove_index=None) -> None:
        row = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(row)
        outer.setContentsMargins(0, 0, 0, 0)
        header = QtWidgets.QHBoxLayout()
        field = None
        if pattern is None:
            header.addWidget(QtWidgets.QLabel(label))
        else:
            field = QtWidgets.QLineEdit(pattern)
            field.setPlaceholderText("識別文字（例: L_）")
            header.addWidget(field)
        header.addStretch(1)
        if remove_index is not None:
            remove = QtWidgets.QToolButton()
            remove.setText("×")
            remove.clicked.connect(lambda _checked=False, i=remove_index: self._remove_name_group(i))
            header.addWidget(remove)
        outer.addLayout(header)
        grid = QtWidgets.QGridLayout()
        boxes = {}
        labels = (("移動", "translate"), ("回転", "rotate"), ("スケール", "scale"))
        for row_index, (text, prefix) in enumerate(labels):
            grid.addWidget(QtWidgets.QLabel(text), row_index, 0)
            for column, axis in enumerate("XYZ", 1):
                attr = prefix + axis
                checkbox = QtWidgets.QCheckBox(axis)
                checkbox.setChecked(values[self.ATTRIBUTES.index(attr)])
                boxes[attr] = checkbox
                grid.addWidget(checkbox, row_index, column)
        visibility = QtWidgets.QCheckBox("表示")
        visibility.setChecked(values[-1])
        boxes["visibility"] = visibility
        grid.addWidget(visibility, 3, 0, 1, 4)
        outer.addLayout(grid)
        self._rows.append((key, field, boxes))
        self.rows_layout.addWidget(row)


class ControllerOffsetSection(CollapsibleSection):
    """Dynamic curve position/rotation settings grouped like colors."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("コントローラー位置・回転", parent)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("すべて同じ設定", "all")
        self.mode_combo.addItem("名前の文字で識別", "name")
        self.mode_combo.addItem("階層分岐で識別", "branch")
        self.rows_layout = QtWidgets.QVBoxLayout()
        self.add_button = QtWidgets.QPushButton("グループを追加")
        self.add_button.setVisible(False)
        self.content_layout.addWidget(self.mode_combo)
        self.content_layout.addLayout(self.rows_layout)
        self.content_layout.addWidget(
            self.add_button, alignment=QtCore.Qt.AlignLeft
        )
        self._branches: list[tuple[str, str]] = []
        self._name_values: list[tuple[str, tuple[float, ...]]] = [
            ("L_", (0.0,) * 6),
            ("R_", (0.0,) * 6),
        ]
        self._rows: list[
            tuple[str, QtWidgets.QLineEdit | None, list[QtWidgets.QDoubleSpinBox]]
        ] = []
        self.mode_combo.currentIndexChanged.connect(self._change_mode)
        self.add_button.clicked.connect(self._add_name_group)
        self._rebuild()

    def set_branches(self, branches: list[tuple[str, str]]) -> None:
        self._branches = list(branches)
        if self.mode_combo.currentData() == "branch":
            self._rebuild()

    def settings(self) -> tuple[str, dict[str, tuple], list[tuple]]:
        offsets: dict[str, tuple] = {}
        rules: list[tuple] = []
        for key, pattern_field, spins in self._rows:
            position = tuple(spin.value() for spin in spins[:3])
            rotation = tuple(spin.value() for spin in spins[3:])
            if pattern_field is None:
                offsets[key] = (position, rotation)
            elif pattern_field.text().strip():
                rules.append((pattern_field.text().strip(), position, rotation))
        return self.mode_combo.currentData(), offsets, rules

    def _change_mode(self) -> None:
        self._capture_names()
        self._rebuild()

    def _capture_names(self) -> None:
        values = []
        for _key, field, spins in self._rows:
            if field is not None:
                values.append((field.text(), tuple(spin.value() for spin in spins)))
        if values:
            self._name_values = values

    def _add_name_group(self) -> None:
        self._capture_names()
        self._name_values.append(("", (0.0,) * 6))
        self._rebuild()

    def _remove_name_group(self, remove_index: int) -> None:
        self._capture_names()
        self._name_values.pop(remove_index)
        self._rebuild()

    def _clear_rows(self) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()

    def _rebuild(self) -> None:
        self._clear_rows()
        mode = self.mode_combo.currentData()
        self.add_button.setVisible(mode == "name")
        if mode == "all":
            self._add_row("__all__", "すべて", None, (0.0,) * 6)
        elif mode == "name":
            for index, (pattern, values) in enumerate(self._name_values):
                self._add_row(
                    "name_{0}".format(index), "", pattern, values, index
                )
        elif not self._branches:
            self.rows_layout.addWidget(
                QtWidgets.QLabel("ルートジョイントを設定してください")
            )
        else:
            for key, label in self._branches:
                self._add_row(key, label, None, (0.0,) * 6)

    def _add_row(
        self,
        key: str,
        label: str,
        pattern: str | None,
        values: tuple[float, ...],
        remove_index: int | None = None,
    ) -> None:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QtWidgets.QHBoxLayout()
        pattern_field = None
        if pattern is None:
            name_label = QtWidgets.QLabel(label)
            header.addWidget(name_label)
        else:
            pattern_field = QtWidgets.QLineEdit(pattern)
            pattern_field.setPlaceholderText("識別文字（例: L_）")
            header.addWidget(pattern_field)
        header.addStretch(1)
        if remove_index is not None:
            remove = QtWidgets.QToolButton()
            remove.setText("×")
            remove.clicked.connect(
                lambda _checked=False, index=remove_index: self._remove_name_group(
                    index
                )
            )
            header.addWidget(remove)
        layout.addLayout(header)

        spins = []
        for group_index, group_label in enumerate(("位置", "回転")):
            value_row = QtWidgets.QHBoxLayout()
            value_label = QtWidgets.QLabel(group_label)
            value_label.setMinimumWidth(32)
            value_row.addWidget(value_label)
            for axis_index, axis in enumerate("XYZ"):
                value_index = group_index * 3 + axis_index
                spin = QtWidgets.QDoubleSpinBox()
                spin.setRange(-10000.0, 10000.0)
                spin.setDecimals(3)
                spin.setValue(values[value_index])
                spins.append(spin)
                axis_label = QtWidgets.QLabel(axis)
                axis_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                value_row.addWidget(axis_label)
                value_row.addWidget(spin)
            layout.addLayout(value_row)
        self._rows.append((key, pattern_field, spins))
        self.rows_layout.addWidget(row)


class FKBuilderWindow(QtWidgets.QDialog):
    """Minimal portfolio UI; all scene operations are delegated."""

    WINDOW_TITLE = "FK-Builder"
    COLOR_OPTIONS = (
        ("色なし", None),
        ("赤", 13),
        ("青", 6),
        ("黄", 17),
        ("緑", 14),
        ("紫", 9),
        ("水色", 18),
        ("シアン", 27),
        ("青紫", 29),
        ("ピンク", 20),
        ("オレンジ", 21),
        ("暗い赤", 4),
        ("白", 16),
    )
    DEFAULT_SEQUENCE = (13, 6, 17, 14, 9)
    COOL_SEQUENCE = (18, 6, 14, 27, 29)
    WARM_SEQUENCE = (13, 21, 17, 20, 4)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        cmds: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self.builder = FKBuilder(cmds=cmds)
        self.cmds = self.builder.cmds
        self._shape_library_warning = ""
        try:
            self._available_shapes = load_shape_libraries()
        except ShapeLibraryError as exc:
            self._available_shapes = load_shape_libraries(
                include_external=False
            )
            self._shape_library_warning = str(exc)
        self._selected_shape_key = ""
        self._shape_picker: ShapePickerDialog | None = None
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName("FKBuilderWindow")
        self.setMinimumWidth(380)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self._create_widgets()
        self._create_layout()
        self._connect_signals()
        self.log("準備完了。", clear=True)
        if self._shape_library_warning:
            self.log(
                "外部シェイプライブラリ警告: {0}".format(
                    self._shape_library_warning
                )
            )

    def _create_widgets(self) -> None:
        self.root_field = QtWidgets.QLineEdit()
        self.root_field.setReadOnly(True)
        self.set_button = QtWidgets.QPushButton("設定")
        self.visibility_field = QtWidgets.QLineEdit()
        self.visibility_field.setReadOnly(True)
        self.visibility_field.setPlaceholderText(
            "未設定でも作成できます"
        )
        self.visibility_set_button = QtWidgets.QPushButton("設定")
        self.visibility_clear_button = QtWidgets.QPushButton("解除")
        self.visibility_attribute_field = QtWidgets.QLineEdit("FK-finger")
        self.visibility_attribute_field.setPlaceholderText("例: FK-finger")
        self.size_spin = QtWidgets.QDoubleSpinBox()
        self.size_spin.setRange(0.001, 10000.0)
        self.size_spin.setDecimals(3)
        self.size_spin.setValue(1.0)
        self.offset_section = ControllerOffsetSection()
        self.lock_section = ChannelLockSection()

        self.color_section = CollapsibleSection("コントローラーカラー")
        self.color_mode_combo = QtWidgets.QComboBox()
        self.color_mode_combo.addItem("すべて同じ色", "all")
        self.color_mode_combo.addItem("名前の文字で識別", "name")
        self.color_mode_combo.addItem("階層分岐で識別", "branch")
        self.color_combos: dict[str, QtWidgets.QComboBox] = {}
        self.name_rule_inputs: dict[str, QtWidgets.QLineEdit] = {}
        self._name_rule_values: list[tuple[str, int | None]] = [
            ("L_", 6),
            ("R_", 13),
        ]
        self._branch_color_groups: list[tuple[str, str]] = []
        self._color_rule_counter = 0
        self.color_form = QtWidgets.QFormLayout()
        self._configure_color_groups([])
        self.add_color_group_button = QtWidgets.QPushButton("グループを追加")
        self.add_color_group_button.setVisible(False)

        self.cool_set_button = QtWidgets.QPushButton("寒色セット")
        self.warm_set_button = QtWidgets.QPushButton("暖色セット")
        self.reset_color_button = QtWidgets.QPushButton("リセット")
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
        self.cool_set_button.setFixedWidth(96)
        self.warm_set_button.setFixedWidth(96)
        self.reset_color_button.setFixedWidth(96)
        self.cool_set_button.setEnabled(False)
        self.warm_set_button.setEnabled(False)
        self.reset_color_button.setEnabled(False)
        preset_buttons = QtWidgets.QVBoxLayout()
        preset_buttons.addStretch(1)
        preset_buttons.addWidget(self.cool_set_button)
        preset_buttons.addSpacing(6)
        preset_buttons.addWidget(self.warm_set_button)
        preset_buttons.addSpacing(6)
        preset_buttons.addWidget(self.reset_color_button)
        preset_buttons.addStretch(1)

        self.color_section.content_layout.addWidget(self.color_mode_combo)
        color_row = QtWidgets.QHBoxLayout()
        color_row.addLayout(self.color_form)
        color_row.addSpacing(18)
        color_row.addLayout(preset_buttons)
        color_row.addStretch(1)
        self.color_section.content_layout.addLayout(color_row)
        self.color_section.content_layout.addWidget(
            self.add_color_group_button, alignment=QtCore.Qt.AlignLeft
        )

        self.shape_section = CollapsibleSection("コントローラー形状")
        self.shape_field = QtWidgets.QLineEdit()
        self.shape_field.setReadOnly(True)
        self.shape_field.setText("立方体（標準）")
        self.shape_set_button = QtWidgets.QPushButton("一覧...")
        self.shape_clear_button = QtWidgets.QPushButton("リセット")
        shape_row = QtWidgets.QHBoxLayout()
        shape_row.addWidget(self.shape_field, 1)
        shape_row.addWidget(self.shape_set_button)
        shape_row.addWidget(self.shape_clear_button)
        self.shape_section.content_layout.addLayout(shape_row)

        self.include_end_radio = QtWidgets.QRadioButton("作成")
        self.exclude_end_radio = QtWidgets.QRadioButton("除外")
        self.include_end_radio.setChecked(True)
        self.end_joint_group = QtWidgets.QButtonGroup(self)
        self.end_joint_group.addButton(self.include_end_radio)
        self.end_joint_group.addButton(self.exclude_end_radio)
        self.build_button = QtWidgets.QPushButton("FKを作成")
        self.build_button.setMinimumHeight(36)
        self.build_button.setStyleSheet(
            "QPushButton {"
            " background-color: #2f9f91;"
            " color: #ffffff;"
            " border: 1px solid #47b9aa;"
            "}"
            "QPushButton:hover { background-color: #36ad9e; }"
            "QPushButton:pressed { background-color: #287f75; }"
        )
        self.log_output = QtWidgets.QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(200)
        self.log_output.setMinimumHeight(150)

    def _create_layout(self) -> None:
        form = QtWidgets.QFormLayout()
        root_row = QtWidgets.QHBoxLayout()
        root_row.addWidget(self.root_field, 1)
        root_row.addWidget(self.set_button)
        form.addRow("ルートジョイント", root_row)
        visibility_row = QtWidgets.QHBoxLayout()
        visibility_row.addWidget(self.visibility_field, 1)
        visibility_row.addWidget(self.visibility_set_button)
        visibility_row.addWidget(self.visibility_clear_button)
        form.addRow("表示切替コントローラー（任意）", visibility_row)
        form.addRow("表示切替の属性名", self.visibility_attribute_field)
        form.addRow("コントローラーサイズ", self.size_spin)

        scroll_content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(scroll_content)
        layout.addLayout(form)
        layout.addWidget(self.offset_section)
        layout.addWidget(self.lock_section)
        layout.addWidget(self.color_section)
        layout.addWidget(self.shape_section)
        end_joint_row = QtWidgets.QHBoxLayout()
        end_joint_row.addWidget(QtWidgets.QLabel("末端ジョイント"))
        end_joint_row.addStretch(1)
        end_joint_row.addWidget(self.include_end_radio)
        end_joint_row.addWidget(self.exclude_end_radio)
        layout.addLayout(end_joint_row)
        layout.addWidget(self.build_button)
        layout.addWidget(QtWidgets.QLabel("ログ"))
        layout.addWidget(self.log_output)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(scroll_content)
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll_area)
        self.resize(470, 720)

    def _connect_signals(self) -> None:
        self.set_button.clicked.connect(self.set_root_joint)
        self.visibility_set_button.clicked.connect(
            self.set_visibility_controller
        )
        self.visibility_clear_button.clicked.connect(
            self.clear_visibility_controller
        )
        self.color_mode_combo.currentIndexChanged.connect(
            self._on_color_mode_changed
        )
        self.add_color_group_button.clicked.connect(
            self.add_name_color_group
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
        self.shape_set_button.clicked.connect(self.open_shape_picker)
        self.shape_clear_button.clicked.connect(self.reset_shape_selection)
        self.build_button.clicked.connect(self.build_fk)
        self.sync_color_preset_buttons()

    @QtCore.Slot()
    def set_root_joint(self) -> None:
        try:
            root = selected_joint(self.cmds)
            joints = self.builder.inspect(root)
            color_groups = self.builder.color_groups(root)
        except (FKBuilderError, RuntimeError) as exc:
            self.log("エラー: {0}".format(exc), clear=True)
            return
        self.root_field.setText(root)
        self._configure_color_groups(color_groups)
        self.offset_section.set_branches(color_groups)
        self.lock_section.set_branches(color_groups)
        self.log("{0}個のジョイントを検出しました。".format(len(joints)), clear=True)

    @QtCore.Slot()
    def set_visibility_controller(self) -> None:
        try:
            controller = selected_transform(self.cmds)
        except FKBuilderError as exc:
            self.log("エラー: {0}".format(exc), clear=True)
            return
        self.visibility_field.setText(controller)
        self.log(
            "表示切替コントローラー: {0}".format(controller),
            clear=True,
        )

    @QtCore.Slot()
    def clear_visibility_controller(self) -> None:
        """Remove the optional visibility-controller assignment."""
        self.visibility_field.clear()
        self.log("表示切替コントローラーを解除しました。", clear=True)

    @QtCore.Slot()
    def open_shape_picker(self) -> None:
        """Open the available shape libraries beside Maya."""
        if self._shape_picker is not None:
            self._shape_picker.show()
            self._shape_picker.raise_()
            self._shape_picker.activateWindow()
            return
        dialog = ShapePickerDialog(self._available_shapes, self)
        dialog.setModal(False)
        dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.accepted.connect(
            lambda: self._apply_shape_selection(dialog)
        )
        dialog.destroyed.connect(self._clear_shape_picker_reference)
        self._shape_picker = dialog
        dialog.show()

    def _apply_shape_selection(self, dialog: ShapePickerDialog) -> None:
        """Apply the item accepted in the non-modal shape picker."""
        if not dialog.selected_shape:
            return
        self._selected_shape_key = dialog.selected_shape
        shape = self._available_shapes[self._selected_shape_key]
        label = str(shape.get("label", self._selected_shape_key))
        library_name = str(
            shape.get("library_name", "シェイプライブラリ")
        )
        self.shape_field.setText("{0} / {1}".format(library_name, label))
        self.log(
            "コントローラー形状: {0} / {1}".format(
                library_name, label
            ),
            clear=True,
        )

    @QtCore.Slot()
    def _clear_shape_picker_reference(self) -> None:
        """Release the picker reference after its window closes."""
        self._shape_picker = None

    @QtCore.Slot()
    def reset_shape_selection(self) -> None:
        """Return controller generation to the default cube shape."""
        self._selected_shape_key = ""
        self.shape_field.setText("立方体（標準）")
        self.log("コントローラー形状: 立方体（標準）。", clear=True)

    @QtCore.Slot()
    def build_fk(self) -> None:
        self.log_output.clear()
        try:
            offset_mode, controller_offsets, name_offset_rules = (
                self.offset_section.settings()
            )
            lock_mode, lock_channel_groups, name_lock_rules = (
                self.lock_section.settings()
            )
            result = self.builder.build(
                root_joint=self.root_field.text().strip(),
                controller_size=self.size_spin.value(),
                log=self.log,
                lock_channel_groups=lock_channel_groups,
                lock_mode=lock_mode,
                name_lock_rules=name_lock_rules,
                visibility_controller=(
                    self.visibility_field.text().strip() or None
                ),
                visibility_attribute_name=(
                    self.visibility_attribute_field.text().strip()
                    or "FK-finger"
                ),
                controller_colors=self.selected_controller_colors(),
                color_mode=self.color_mode_combo.currentData(),
                name_color_rules=self.selected_name_color_rules(),
                controller_offsets=controller_offsets,
                offset_mode=offset_mode,
                name_offset_rules=name_offset_rules,
                include_end_joint=self.include_end_radio.isChecked(),
                shape_data=self._available_shapes.get(
                    self._selected_shape_key
                ),
            )
        except Exception as exc:
            self.log("エラー: {0}".format(exc))
            return
        self.log("{0}個のコントローラーを作成しました。".format(len(result.controllers)))
        self.log("作成完了。")

    def log(self, message: str, clear: bool = False) -> None:
        if clear:
            self.log_output.clear()
        self.log_output.appendPlainText(message)
    def selected_lock_channels(self) -> tuple[str, ...]:
        """Return channel names currently enabled in the lock section."""
        _mode, groups, _rules = self.lock_section.settings()
        return next(iter(groups.values()), ())

    @QtCore.Slot()
    def unlock_all_channels(self) -> None:
        """Clear every channel-lock selection at once."""
        self.lock_section.unlock_all()

    def selected_controller_colors(self) -> dict[str, int | None]:
        """Return Maya color indices selected for each color group."""
        return {
            finger: combo.currentData()
            for finger, combo in self.color_combos.items()
        }

    def selected_name_color_rules(self) -> list[tuple[str, int | None]]:
        """Return ordered substring/color rules from the name mode."""
        if self.color_mode_combo.currentData() != "name":
            return []
        return [
            (line_edit.text().strip(), self.color_combos[key].currentData())
            for key, line_edit in self.name_rule_inputs.items()
            if line_edit.text().strip()
        ]

    @QtCore.Slot()
    def _on_color_mode_changed(self) -> None:
        """Rebuild the rows for the newly selected color strategy."""
        self._capture_name_rules()
        self._rebuild_color_rows()

    @QtCore.Slot()
    def add_name_color_group(self) -> None:
        """Append an editable name-matching color group."""
        self._capture_name_rules()
        index = len(self._name_rule_values)
        color = self.DEFAULT_SEQUENCE[index % len(self.DEFAULT_SEQUENCE)]
        self._name_rule_values.append(("", color))
        self._rebuild_color_rows()

    def _remove_name_color_group(self, key: str) -> None:
        """Remove one name-matching row while preserving the others."""
        values = []
        for rule_key, line_edit in self.name_rule_inputs.items():
            if rule_key != key:
                values.append(
                    (line_edit.text(), self.color_combos[rule_key].currentData())
                )
        self._name_rule_values = values
        self._rebuild_color_rows()

    def _capture_name_rules(self) -> None:
        """Preserve edits before dynamic rows are recreated."""
        if not self.name_rule_inputs:
            return
        self._name_rule_values = [
            (line_edit.text(), self.color_combos[key].currentData())
            for key, line_edit in self.name_rule_inputs.items()
        ]

    def apply_color_preset(self, preset_name: str) -> None:
        """Apply a default, warm, or cool palette to all groups."""
        preset = self._preset_colors(preset_name)
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
        if not self.color_combos:
            self._clear_color_preset_selection()
            return
        selected = self.selected_controller_colors()
        matching_button = None
        if selected == self._preset_colors("cool"):
            matching_button = self.cool_set_button
        elif selected == self._preset_colors("warm"):
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

    def _configure_color_groups(
        self,
        groups: list[tuple[str, str]],
    ) -> None:
        """Store the exact hierarchy branches and refresh when applicable."""
        self._branch_color_groups = list(groups)
        self._rebuild_color_rows()

    def _rebuild_color_rows(self) -> None:
        """Create rows appropriate for all, name, or branch color mode."""
        while self.color_form.rowCount():
            self.color_form.removeRow(0)
        self.color_combos.clear()
        self.name_rule_inputs.clear()
        mode = self.color_mode_combo.currentData()
        self.add_color_group_button.setVisible(mode == "name") if hasattr(
            self, "add_color_group_button"
        ) else None

        if mode == "all":
            self._add_standard_color_row("__all__", "すべて", 0)
        elif mode == "name":
            for pattern, color_index in self._name_rule_values:
                self._add_name_color_row(pattern, color_index)
        elif not self._branch_color_groups:
            self.color_form.addRow(
                QtWidgets.QLabel("ルートジョイントを設定してください")
            )
        else:
            for index, (key, label) in enumerate(self._branch_color_groups):
                self._add_standard_color_row(key, label, index)
        if hasattr(self, "color_preset_group"):
            enabled = bool(self.color_combos)
            self.cool_set_button.setEnabled(enabled)
            self.warm_set_button.setEnabled(enabled)
            self.reset_color_button.setEnabled(enabled)
            self.sync_color_preset_buttons()

    def _new_color_combo(self, color_index: int | None) -> QtWidgets.QComboBox:
        """Create a consistently configured Maya index-color combo."""
        combo = QtWidgets.QComboBox()
        for option_label, option_index in self.COLOR_OPTIONS:
            combo.addItem(option_label, option_index)
        selected_index = combo.findData(color_index)
        combo.setCurrentIndex(max(0, selected_index))
        combo.currentIndexChanged.connect(self.sync_color_preset_buttons)
        return combo

    def _add_standard_color_row(
        self, key: str, label: str, sequence_index: int
    ) -> None:
        """Add an all-color or hierarchy-branch row."""
        color = self.DEFAULT_SEQUENCE[sequence_index % len(self.DEFAULT_SEQUENCE)]
        combo = self._new_color_combo(color)
        self.color_combos[key] = combo
        self.color_form.addRow(label, combo)

    def _add_name_color_row(
        self, pattern: str, color_index: int | None
    ) -> None:
        """Add one editable substring rule with its own remove button."""
        self._color_rule_counter += 1
        key = "name_rule_{0}".format(self._color_rule_counter)
        line_edit = QtWidgets.QLineEdit(pattern)
        line_edit.setPlaceholderText("識別文字（例: L_）")
        combo = self._new_color_combo(color_index)
        remove_button = QtWidgets.QToolButton()
        remove_button.setText("×")
        remove_button.setToolTip("このグループを削除")
        remove_button.clicked.connect(
            lambda _checked=False, rule_key=key: self._remove_name_color_group(
                rule_key
            )
        )
        field = QtWidgets.QWidget()
        field_layout = QtWidgets.QHBoxLayout(field)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.addWidget(combo)
        field_layout.addWidget(remove_button)
        self.name_rule_inputs[key] = line_edit
        self.color_combos[key] = combo
        self.color_form.addRow(line_edit, field)

    def _preset_colors(
        self,
        preset_name: str,
    ) -> dict[str, int | None]:
        """Create a palette matching the current dynamic color rows."""
        sequences = {
            "default": self.DEFAULT_SEQUENCE,
            "cool": self.COOL_SEQUENCE,
            "warm": self.WARM_SEQUENCE,
        }
        sequence = sequences[preset_name]
        return {
            key: sequence[index % len(sequence)]
            for index, key in enumerate(self.color_combos)
        }
