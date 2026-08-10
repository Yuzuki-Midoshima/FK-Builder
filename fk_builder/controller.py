"""Reusable NURBS controller creation."""

from __future__ import annotations

import math
from typing import Any


class CubeControllerFactory:
    """Create lightweight default or library-based NURBS controllers."""

    _POINTS = (
        (-1, -1, -1),
        (-1, -1, 1),
        (-1, 1, 1),
        (-1, 1, -1),
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, 1, 1),
        (1, 1, 1),
        (1, 1, -1),
        (1, -1, -1),
        (1, -1, 1),
        (1, 1, 1),
        (1, 1, -1),
        (1, -1, -1),
        (1, -1, 1),
        (-1, -1, 1),
    )

    def __init__(self, cmds: Any) -> None:
        self.cmds = cmds

    def create(
        self,
        name: str,
        size: float,
        color_index: int | None = None,
        shape_data: dict[str, Any] | None = None,
        position_offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation_offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> str:
        """Create the default cube or a selected library shape."""
        if size <= 0.0:
            raise ValueError("コントローラーサイズは0より大きくしてください。")
        components = (
            shape_data.get("components") if shape_data else None
        ) or [shape_data or {"degree": 1, "points": self._POINTS}]
        controller = ""
        for index, component in enumerate(components):
            points = [
                self._offset_point(
                    tuple(float(axis) * size for axis in point),
                    position_offset,
                    rotation_offset,
                )
                for point in component.get("points", [])
            ]
            degree = int(component.get("degree", 1))
            if len(points) <= degree:
                raise ValueError("コントローラー形状のポイントが無効です。")
            curve = self.cmds.curve(
                name=name if index == 0 else name + "Part",
                degree=degree,
                point=points,
            )
            if index == 0:
                controller = curve
                continue
            part_shapes = self._curve_shapes(curve)
            for part_shape in part_shapes:
                self.cmds.parent(
                    part_shape,
                    controller,
                    shape=True,
                    relative=True,
                )
            self.cmds.delete(curve)
        # Freeze only the controller. The curve size is baked into its CVs.
        self.cmds.makeIdentity(
            controller,
            apply=True,
            translate=True,
            rotate=True,
            scale=True,
            normal=False,
        )
        shapes = self._curve_shapes(controller)
        for index, shape in enumerate(shapes, start=1):
            suffix = (
                "Shape"
                if len(shapes) == 1
                else "Shape{0:02d}".format(index)
            )
            self.cmds.rename(shape, name + suffix)
        if color_index is not None:
            shapes = self._curve_shapes(controller)
            for shape in shapes:
                self.cmds.setAttr(
                    "{0}.overrideEnabled".format(shape), True
                )
                self.cmds.setAttr(
                    "{0}.overrideColor".format(shape), int(color_index)
                )
        return controller

    @staticmethod
    def _offset_point(
        point: tuple[float, float, float],
        position: tuple[float, float, float],
        rotation: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        """Bake XYZ Euler rotation and translation into a curve CV."""
        x, y, z = point
        rx, ry, rz = (math.radians(value) for value in rotation)
        cos_x, sin_x = math.cos(rx), math.sin(rx)
        y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x
        cos_y, sin_y = math.cos(ry), math.sin(ry)
        x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
        cos_z, sin_z = math.cos(rz), math.sin(rz)
        x, y = x * cos_z - y * sin_z, x * sin_z + y * cos_z
        return (
            x + position[0],
            y + position[1],
            z + position[2],
        )

    def _curve_shapes(self, controller: str) -> list[str]:
        """Return all direct NURBS curve shapes under a controller."""
        return self.cmds.listRelatives(
            controller,
            shapes=True,
            type="nurbsCurve",
            fullPath=True,
        ) or []
