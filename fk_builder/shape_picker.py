"""Searchable visual picker for controller-shape libraries."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets


class ShapePickerDialog(QtWidgets.QDialog):
    """Display shape previews generated directly from curve-point data."""

    def __init__(
        self,
        shapes: dict[str, dict[str, Any]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("コントローラー形状一覧")
        self.setMinimumSize(560, 420)
        self.selected_shape = ""
        self._shapes = shapes

        layout = QtWidgets.QVBoxLayout(self)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("形状名を検索...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QtWidgets.QListWidget()
        self.list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.list.setMovement(QtWidgets.QListView.Movement.Static)
        self.list.setIconSize(QtCore.QSize(72, 72))
        self.list.setGridSize(QtCore.QSize(112, 102))
        self.list.itemDoubleClicked.connect(self._accept_item)
        layout.addWidget(self.list, 1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_current)
        buttons.rejected.connect(self.reject)
        buttons.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).setText("決定")
        buttons.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        ).setText("キャンセル")
        layout.addWidget(buttons)
        self._populate()

    def _populate(self) -> None:
        for key, shape in sorted(
            self._shapes.items(),
            key=lambda item: str(item[1].get("label", item[0])),
        ):
            item = QtWidgets.QListWidgetItem(
                self._icon(shape), str(shape.get("label", key))
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
            item.setToolTip(
                "{0} / {1}".format(
                    shape.get("library_name", "シェイプライブラリ"),
                    shape.get("source", key),
                )
            )
            self.list.addItem(item)

    @staticmethod
    def _icon(shape: dict[str, Any]) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(72, 72)
        pixmap.fill(QtGui.QColor("#303030"))
        components = shape.get("components") or [shape]
        points = [
            point
            for component in components
            for point in component.get("points", [])
        ]
        projected = [
            (
                float(point[0]) + float(point[1]) * 0.35,
                float(point[2]) - float(point[1]) * 0.35,
            )
            for point in points
        ]
        if not projected:
            return QtGui.QIcon(pixmap)
        xs, ys = zip(*projected)
        extent = max(max(xs) - min(xs), max(ys) - min(ys), 1.0e-6)
        scale = 56.0 / extent
        center_x = (max(xs) + min(xs)) * 0.5
        center_y = (max(ys) + min(ys)) * 0.5
        polygon = QtGui.QPolygonF(
            [
                QtCore.QPointF(
                    36.0 + (x - center_x) * scale,
                    36.0 - (y - center_y) * scale,
                )
                for x, y in projected
            ]
        )
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor("#f0c84b"), 1.5))
        painter.drawPolyline(polygon)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _filter(self, text: str) -> None:
        query = text.strip().lower()
        for row in range(self.list.count()):
            item = self.list.item(row)
            item.setHidden(query not in item.text().lower())

    def _accept_item(self, item: QtWidgets.QListWidgetItem) -> None:
        self.selected_shape = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()

    def _accept_current(self) -> None:
        item = self.list.currentItem()
        if item:
            self._accept_item(item)
