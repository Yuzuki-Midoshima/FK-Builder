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
            "FK-BuilderはMaya内で実行してください。"
        ) from exc
    return cmds


def short_name(node: str) -> str:
    """Return a DAG node's leaf name while retaining its namespace."""
    return node.rsplit("|", 1)[-1]


def controller_name(joint: str) -> str:
    """Convert a supported joint suffix to the controller suffix."""
    name = short_name(joint)
    lower_name = name.lower()
    for suffix in ("_joint", "_bind", "_bone", "_jnt", "_skn", "_bn"):
        if lower_name.endswith(suffix):
            return name[:-len(suffix)] + "_anim"
    raise FKBuilderError(
        "Joint name must use a supported joint suffix: {0}".format(name)
    )


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
        raise FKBuilderError("ルートジョイントを選択してください。")
    return selected[0]


def selected_transform(cmds: Any) -> str:
    """Return one selected transform for use as a settings controller."""
    selected = cmds.ls(selection=True, long=True, type="transform") or []
    if len(selected) != 1:
        raise FKBuilderError(
            "表示切替コントローラーを1つ選択してください。"
        )
    return selected[0]


def joint_hierarchy(cmds: Any, root_joint: str) -> list[str]:
    """Return root and all joint descendants in parent-before-child order."""
    if not root_joint or not cmds.objExists(root_joint):
        raise FKBuilderError("ルートジョイントが存在しません。")
    if cmds.nodeType(root_joint) != "joint":
        raise FKBuilderError("ルートジョイントにはJointを指定してください。")

    root = (cmds.ls(root_joint, long=True) or [root_joint])[0]
    descendants = cmds.listRelatives(
        root, allDescendents=True, type="joint", fullPath=True
    ) or []
    joints = [root] + list(reversed(descendants))
    return joints
