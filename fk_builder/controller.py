"""Reusable NURBS controller creation."""

from __future__ import annotations

from typing import Any


class CubeControllerFactory:
    """Create lightweight cube-shaped NURBS curve controllers."""

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
    ) -> str:
        """Create a degree-one cube at the requested baked-in size."""
        if size <= 0.0:
            raise ValueError("Controller size must be greater than zero.")
        points = [
            tuple(float(axis) * size for axis in point)
            for point in self._POINTS
        ]
        controller = self.cmds.curve(
            name=name,
            degree=1,
            point=points,
            knot=list(range(len(points))),
        )
        # Freeze only the controller. The curve size is baked into its CVs.
        self.cmds.makeIdentity(
            controller,
            apply=True,
            translate=True,
            rotate=True,
            scale=True,
            normal=False,
        )
        if color_index is not None:
            shapes = self.cmds.listRelatives(
                controller, shapes=True, fullPath=True
            ) or []
            for shape in shapes:
                self.cmds.setAttr(
                    "{0}.overrideEnabled".format(shape), True
                )
                self.cmds.setAttr(
                    "{0}.overrideColor".format(shape), int(color_index)
                )
        return controller
