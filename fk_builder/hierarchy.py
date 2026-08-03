"""FK controller hierarchy operations."""

from __future__ import annotations

from typing import Any


def create_fk_hierarchy(
    cmds: Any,
    joints: list[str],
    controllers: dict[str, str],
    zero_groups: dict[str, str],
) -> None:
    """Parent each child zero beneath its joint parent's controller."""
    joint_set = set(joints)
    for joint in joints:
        parents = cmds.listRelatives(
            joint, parent=True, type="joint", fullPath=True
        ) or []
        if parents and parents[0] in joint_set:
            cmds.parent(zero_groups[joint], controllers[parents[0]])
