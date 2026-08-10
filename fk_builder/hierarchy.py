"""FK controller hierarchy operations."""

from __future__ import annotations

from typing import Any


def create_fk_hierarchy(
    cmds: Any,
    joints: list[str],
    controllers: dict[str, str],
    zero_groups: dict[str, str],
) -> None:
    """Parent each zero below its nearest ancestor joint controller."""
    joint_set = set(joints)
    for joint in joints:
        parent_path = joint.rsplit("|", 1)[0]
        while parent_path and parent_path not in joint_set:
            parent_path = parent_path.rsplit("|", 1)[0]
        if parent_path in joint_set:
            cmds.parent(zero_groups[joint], controllers[parent_path])
