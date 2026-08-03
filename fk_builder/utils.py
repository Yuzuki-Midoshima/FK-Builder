"""Small Maya and naming helpers shared by the builder modules."""

from __future__ import annotations

from typing import Any


class FKBuilderError(RuntimeError):
    """An expected validation or build error suitable for display in the UI."""


def maya_cmds() -> Any:
    """Import maya.cmds only when Maya functionality is requested."""
    try:
        from maya import cmds
    except ImportError as exc:
        raise RuntimeError(
            "FK-Builder must be run inside Maya."
        ) from exc
    return cmds


def short_name(node: str) -> str:
    """Return a DAG node's leaf name while retaining its namespace."""
    return node.rsplit("|", 1)[-1]


def controller_name(joint: str) -> str:
    """Convert a joint name to its controller name."""
    name = short_name(joint)
    if not name.endswith("_jnt"):
        raise FKBuilderError(
            "Joint name must end with '_jnt': {0}".format(name)
        )
    return name[:-4] + "_anim"


def zero_name(joint: str) -> str:
    """Convert a joint name to its zero-group name."""
    return controller_name(joint)[:-5] + "_zero"


def selected_joint(cmds: Any) -> str:
    """Return the first selected joint as a stable long DAG path."""
    selected = cmds.ls(
        selection=True,
        long=True,
        type="joint",
    ) or []
    if not selected:
        raise FKBuilderError("Select a root joint.")
    return selected[0]


def selected_transform(cmds: Any) -> str:
    """Return one selected transform for use as a settings controller."""
    selected = cmds.ls(selection=True, long=True, type="transform") or []
    if len(selected) != 1:
        raise FKBuilderError("Select exactly one settings controller.")
    return selected[0]


def joint_hierarchy(cmds: Any, root_joint: str) -> list[str]:
    """Return root and all joint descendants in parent-before-child order."""
    if not root_joint or not cmds.objExists(root_joint):
        raise FKBuilderError("Root Joint does not exist.")
    if cmds.nodeType(root_joint) != "joint":
        raise FKBuilderError("Root Joint must be a joint.")

    root = (cmds.ls(root_joint, long=True) or [root_joint])[0]
    descendants = cmds.listRelatives(
        root, allDescendents=True, type="joint", fullPath=True
    ) or []
    joints = [root] + list(reversed(descendants))
    return joints
