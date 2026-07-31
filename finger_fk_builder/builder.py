"""UI-independent orchestration for building finger FK controls."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
import re
from typing import Any, Callable

from .controller import CubeControllerFactory
from .hierarchy import create_fk_hierarchy
from .utils import (
    FingerFKError,
    controller_name,
    joint_hierarchy,
    maya_cmds,
    zero_name,
)

LogCallback = Callable[[str], None]


@dataclass(frozen=True)
class BuildResult:
    """Names created during a successful build."""

    joints: tuple[str, ...]
    controllers: tuple[str, ...]
    zero_groups: tuple[str, ...]
    constraints: tuple[str, ...]


class FingerFKBuilder:
    """Build cube FK controls for every joint below a selected root."""

    def __init__(
        self,
        cmds: Any | None = None,
        controller_factory: CubeControllerFactory | None = None,
    ) -> None:
        self.cmds = cmds or maya_cmds()
        self.controller_factory = (
            controller_factory or CubeControllerFactory(self.cmds)
        )

    def inspect(
        self,
        root_joint: str,
        include_end_joint: bool = True,
    ) -> list[str]:
        """Validate and return the joints that would be built."""
        joints = joint_hierarchy(self.cmds, root_joint)
        if not include_end_joint:
            joints = [
                joint
                for joint in joints
                if self.cmds.listRelatives(
                    joint,
                    children=True,
                    type="joint",
                    fullPath=True,
                )
            ]
        if not joints:
            raise FingerFKError(
                "No joints remain when End Joint is excluded."
            )
        self._validate_names(joints)
        return joints

    def build(
        self,
        root_joint: str,
        controller_size: float = 1.0,
        log: LogCallback | None = None,
        lock_channels: Iterable[str] | None = None,
        visibility_controller: str | None = None,
        finger_colors: dict[str, int | None] | None = None,
        include_end_joint: bool = True,
    ) -> BuildResult:
        """Build the complete FK setup as one Maya undo operation."""
        emit = log or (lambda _message: None)
        if controller_size <= 0.0:
            raise FingerFKError("Controller Size must be greater than zero.")

        emit("Searching joints...")
        joints = self.inspect(root_joint, include_end_joint)
        settings_controller = self._validate_visibility_controller(
            visibility_controller
        )
        emit("{0} joints found.".format(len(joints)))

        controllers: dict[str, str] = {}
        zero_groups: dict[str, str] = {}
        constraints: list[str] = []
        chunk_open = False
        try:
            self.cmds.undoInfo(
                openChunk=True,
                chunkName="Finger-FK-Builder",
            )
            chunk_open = True

            emit("Creating controllers...")
            for joint in joints:
                controller = self.controller_factory.create(
                    controller_name(joint),
                    controller_size,
                    self._color_for_joint(joint, finger_colors),
                )
                zero = self.cmds.group(empty=True, name=zero_name(joint))
                self.cmds.parent(controller, zero)
                self.cmds.matchTransform(
                    zero, joint, position=True, rotation=True
                )
                self._lock_channels(
                    controller,
                    lock_channels
                    if lock_channels is not None
                    else (
                        "translateX",
                        "translateY",
                        "translateZ",
                        "scaleX",
                        "scaleY",
                        "scaleZ",
                        "visibility",
                    ),
                )
                controllers[joint] = controller
                zero_groups[joint] = zero

            emit("{0} controllers created.".format(len(controllers)))
            emit("Creating hierarchy...")
            create_fk_hierarchy(
                self.cmds, joints, controllers, zero_groups
            )
            if settings_controller:
                emit("Creating visibility switch...")
                self._create_visibility_switch(
                    settings_controller,
                    zero_groups[joints[0]],
                )

            emit("Creating constraints...")
            for joint in joints:
                constraint = self.cmds.orientConstraint(
                    controllers[joint],
                    joint,
                    maintainOffset=False,
                    name=controller_name(joint) + "_orientConstraint",
                )[0]
                constraints.append(constraint)
        except Exception:
            if chunk_open:
                self.cmds.undoInfo(closeChunk=True)
                chunk_open = False
                self.cmds.undo()
            raise
        finally:
            if chunk_open:
                self.cmds.undoInfo(closeChunk=True)

        emit("Finished.")
        return BuildResult(
            joints=tuple(joints),
            controllers=tuple(controllers[joint] for joint in joints),
            zero_groups=tuple(zero_groups[joint] for joint in joints),
            constraints=tuple(constraints),
        )

    def _validate_names(self, joints: list[str]) -> None:
        """Reject invalid joint suffixes and all output-name collisions."""
        output_names: list[str] = []
        for joint in joints:
            output_names.extend((controller_name(joint), zero_name(joint)))
        duplicates = {
            name for name in output_names if output_names.count(name) > 1
        }
        if duplicates:
            raise FingerFKError(
                "Duplicate output name: {0}".format(sorted(duplicates)[0])
            )
        existing = [name for name in output_names if self.cmds.objExists(name)]
        if existing:
            raise FingerFKError(
                "Controller or zero group already exists: {0}".format(
                    existing[0]
                )
            )

    def _lock_channels(
        self,
        controller: str,
        attributes: Iterable[str],
    ) -> None:
        """Lock the controller channels selected by the caller."""
        allowed = {
            "translateX",
            "translateY",
            "translateZ",
            "rotateX",
            "rotateY",
            "rotateZ",
            "scaleX",
            "scaleY",
            "scaleZ",
            "visibility",
        }
        for attribute in attributes:
            if attribute not in allowed:
                raise FingerFKError(
                    "Unsupported lock channel: {0}".format(attribute)
                )
            self.cmds.setAttr(
                "{0}.{1}".format(controller, attribute),
                lock=True,
                keyable=False,
                channelBox=False,
            )

    def _validate_visibility_controller(
        self,
        controller: str | None,
    ) -> str | None:
        """Validate the optional transform which receives FK-finger."""
        if not controller:
            return None
        if not self.cmds.objExists(controller):
            raise FingerFKError("Visibility Controller does not exist.")
        if self.cmds.nodeType(controller) != "transform":
            raise FingerFKError(
                "Visibility Controller must be a transform."
            )
        controller = (self.cmds.ls(controller, long=True) or [controller])[0]
        plug = "{0}.FK_finger".format(controller)
        if self.cmds.objExists(plug):
            raise FingerFKError(
                "FK-finger already exists on Visibility Controller."
            )
        return controller

    def _create_visibility_switch(
        self,
        settings_controller: str,
        root_zero: str,
    ) -> None:
        """Add an OFF/ON channel and drive the complete FK hierarchy."""
        self.cmds.addAttr(
            settings_controller,
            longName="FK_finger",
            niceName="FK-finger",
            attributeType="enum",
            enumName="OFF:ON",
            defaultValue=1,
            keyable=True,
        )
        self.cmds.connectAttr(
            "{0}.FK_finger".format(settings_controller),
            "{0}.visibility".format(root_zero),
            force=True,
        )

    @staticmethod
    def _color_for_joint(
        joint: str,
        finger_colors: dict[str, int | None] | None,
    ) -> int | None:
        """Resolve a finger color from underscore-delimited joint names."""
        if not finger_colors:
            return None
        leaf_name = joint.rsplit("|", 1)[-1].rsplit(":", 1)[-1].lower()
        tokens = set(filter(None, re.split(r"[^a-z]+", leaf_name)))
        for finger in ("thumb", "index", "middle", "ring", "pinky"):
            if finger in tokens:
                return finger_colors.get(finger)
        return None
