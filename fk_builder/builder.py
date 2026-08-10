"""UI-independent orchestration for building finger FK controls."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from collections.abc import Iterable
import re
from typing import Any, Callable

from .controller import CubeControllerFactory
from .hierarchy import create_fk_hierarchy
from .utils import (
    FKBuilderError,
    controller_name,
    joint_hierarchy,
    maya_cmds,
)

LogCallback = Callable[[str], None]


@dataclass(frozen=True)
class BuildResult:
    """Names created during a successful build."""

    joints: tuple[str, ...]
    controllers: tuple[str, ...]
    zero_groups: tuple[str, ...]
    constraints: tuple[str, ...]


class FKBuilder:
    """Build FK controls for every joint below a selected root."""

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
            raise FKBuilderError(
                "末端ジョイントを除外すると対象が0個になります。"
            )
        self._validate_names(joints)
        return joints

    def build(
        self,
        root_joint: str,
        controller_size: float = 1.0,
        log: LogCallback | None = None,
        lock_channels: Iterable[str] | None = None,
        lock_channel_groups: dict[str, tuple[str, ...]] | None = None,
        lock_mode: str = "all",
        name_lock_rules: list[tuple[str, tuple[str, ...]]] | None = None,
        visibility_controller: str | None = None,
        visibility_attribute_name: str = "FK-finger",
        controller_colors: dict[str, int | None] | None = None,
        color_mode: str = "branch",
        name_color_rules: list[tuple[str, int | None]] | None = None,
        controller_offsets: dict[
            str, tuple[tuple[float, float, float], tuple[float, float, float]]
        ] | None = None,
        offset_mode: str = "all",
        name_offset_rules: list[
            tuple[
                str,
                tuple[float, float, float],
                tuple[float, float, float],
            ]
        ] | None = None,
        include_end_joint: bool = True,
        shape_data: dict[str, Any] | None = None,
    ) -> BuildResult:
        """Build the complete FK setup as one Maya undo operation."""
        emit = log or (lambda _message: None)
        if controller_size <= 0.0:
            raise FKBuilderError(
                "コントローラーサイズは0より大きくしてください。"
            )

        emit("ジョイントを検索しています...")
        joints = self.inspect(root_joint, include_end_joint)
        original_joint_matrices = {
            joint: tuple(
                self.cmds.xform(
                    joint,
                    query=True,
                    worldSpace=True,
                    matrix=True,
                )
            )
            for joint in joints
        }
        output_names = self._output_names(joints)
        visibility_attribute = self._visibility_attribute_names(
            visibility_attribute_name
        )
        settings_controller = self._validate_visibility_controller(
            visibility_controller,
            visibility_attribute[0],
        )
        shape_data = self._validate_shape_data(shape_data)
        if color_mode not in {"all", "name", "branch"}:
            raise FKBuilderError("Unsupported controller color mode: {0}".format(color_mode))
        if offset_mode not in {"all", "name", "branch"}:
            raise FKBuilderError("Unsupported controller offset mode: {0}".format(offset_mode))
        if lock_mode not in {"all", "name", "branch"}:
            raise FKBuilderError("Unsupported channel lock mode: {0}".format(lock_mode))
        color_keys = self._color_keys(joints) if color_mode == "branch" else {}
        offset_keys = self._color_keys(joints) if offset_mode == "branch" else {}
        lock_keys = self._color_keys(joints) if lock_mode == "branch" else {}
        emit("{0}個のジョイントが見つかりました。".format(len(joints)))

        controllers: dict[str, str] = {}
        zero_groups: dict[str, str] = {}
        constraints: list[str] = []
        chunk_open = False
        try:
            self.cmds.undoInfo(
                openChunk=True,
                chunkName="FK-Builder",
            )
            chunk_open = True

            emit("コントローラーを作成しています...")
            for joint in joints:
                ctrl_name, group_name = output_names[joint]
                position_offset, rotation_offset = self._offset_for_joint(
                    joint,
                    controller_offsets,
                    offset_keys,
                    offset_mode,
                    name_offset_rules,
                )
                controller = self.controller_factory.create(
                    ctrl_name,
                    controller_size,
                    self._color_for_joint(
                        joint,
                        controller_colors,
                        color_keys,
                        color_mode,
                        name_color_rules,
                    ),
                    shape_data,
                    position_offset,
                    rotation_offset,
                )
                zero = self.cmds.group(empty=True, name=group_name)
                self.cmds.parent(controller, zero)
                self.cmds.matchTransform(
                    zero, joint, position=True, rotation=True, scale=True
                )
                self._lock_channels(
                    controller,
                    self._locks_for_joint(
                        joint,
                        lock_channel_groups,
                        lock_keys,
                        lock_mode,
                        name_lock_rules,
                        lock_channels,
                    ),
                )
                controllers[joint] = controller
                zero_groups[joint] = zero

            emit("{0}個のコントローラーを作成しました。".format(len(controllers)))
            emit("FK階層を作成しています...")
            create_fk_hierarchy(
                self.cmds, joints, controllers, zero_groups
            )
            self._parent_root_controller(
                joints[0], zero_groups[joints[0]]
            )
            if settings_controller:
                emit("表示切替を作成しています...")
                self._create_visibility_switch(
                    settings_controller,
                    zero_groups[joints[0]],
                    visibility_attribute[0],
                    visibility_attribute[1],
                )

            emit("コンストレイントを作成しています...")
            for joint in joints:
                ctrl_name = output_names[joint][0]
                parent_constraint = self.cmds.parentConstraint(
                    controllers[joint],
                    joint,
                    maintainOffset=True,
                    name=ctrl_name + "_parentConstraint",
                )[0]
                scale_constraint = self.cmds.scaleConstraint(
                    controllers[joint],
                    joint,
                    # Joint segmentScaleCompensate can otherwise change the
                    # bind pose immediately on non-uniformly scaled chains.
                    maintainOffset=True,
                    name=ctrl_name + "_scaleConstraint",
                )[0]
                constraints.extend(
                    (parent_constraint, scale_constraint)
                )
            self._validate_joint_matrices(
                joints,
                original_joint_matrices,
            )
        except Exception:
            if chunk_open:
                self.cmds.undoInfo(closeChunk=True)
                chunk_open = False
                self.cmds.undo()
            raise
        finally:
            if chunk_open:
                self.cmds.undoInfo(closeChunk=True)

        emit("処理が完了しました。")
        return BuildResult(
            joints=tuple(joints),
            controllers=tuple(controllers[joint] for joint in joints),
            zero_groups=tuple(zero_groups[joint] for joint in joints),
            constraints=tuple(constraints),
        )

    def _validate_joint_matrices(
        self,
        joints: list[str],
        original_matrices: dict[str, tuple[float, ...]],
        tolerance: float = 1.0e-5,
    ) -> None:
        """Abort and let the undo guard restore any changed bind pose."""
        for joint in joints:
            current = tuple(
                self.cmds.xform(
                    joint,
                    query=True,
                    worldSpace=True,
                    matrix=True,
                )
            )
            difference = max(
                abs(before - after)
                for before, after in zip(original_matrices[joint], current)
            )
            if difference > tolerance:
                raise FKBuilderError(
                    "FK作成でジョイント姿勢が変化したため、自動的に元へ戻しました: {0}".format(
                        joint.rsplit("|", 1)[-1]
                    )
                )

    def _parent_root_controller(
        self,
        root_joint: str,
        root_zero: str,
    ) -> None:
        """Place the controller hierarchy under the root joint's parent."""
        parents = self.cmds.listRelatives(
            root_joint,
            parent=True,
            fullPath=True,
        ) or []
        if parents:
            # Maya parenting preserves the existing world transform by
            # default, so the controller remains aligned to the root joint.
            self.cmds.parent(root_zero, parents[0])

    def _validate_names(self, joints: list[str]) -> None:
        """Reject existing controller names with precise context."""
        names = self._output_names(joints)
        for joint, (ctrl_name, _zero_name) in names.items():
            if self.cmds.objExists(ctrl_name):
                raise FKBuilderError(
                    "同名コントローラーが存在します: {0}（対象Joint: {1}）".format(
                        ctrl_name, joint
                    )
                )

    def _output_names(
        self,
        joints: list[str],
    ) -> dict[str, tuple[str, str]]:
        """Create unique controller and non-conflicting zero names."""
        base_names = [controller_name(joint) for joint in joints]
        totals = Counter(base_names)
        occurrences: dict[str, int] = {}
        result: dict[str, tuple[str, str]] = {}
        for joint, base_name in zip(joints, base_names):
            occurrences[base_name] = occurrences.get(base_name, 0) + 1
            if totals[base_name] > 1:
                ctrl_name = "{0}_{1:02d}_anim".format(
                    base_name[:-5], occurrences[base_name]
                )
            else:
                ctrl_name = base_name
            zero_name = ctrl_name[:-5] + "_zero"
            reserved = {pair[1] for pair in result.values()}
            if self.cmds.objExists(zero_name) or zero_name in reserved:
                zero_base = ctrl_name[:-5] + "_fk_zero"
                zero_name = zero_base
                suffix = 1
                while self.cmds.objExists(zero_name) or zero_name in reserved:
                    zero_name = "{0}_{1:02d}".format(zero_base, suffix)
                    suffix += 1
            result[joint] = (ctrl_name, zero_name)
        return result

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
                raise FKBuilderError(
                    "対応していないロックチャンネルです: {0}".format(attribute)
                )
            self.cmds.setAttr(
                "{0}.{1}".format(controller, attribute),
                lock=True,
                keyable=False,
                channelBox=False,
            )

    @staticmethod
    def _locks_for_joint(
        joint: str,
        groups: dict[str, tuple[str, ...]] | None,
        lock_keys: dict[str, str],
        mode: str,
        name_rules: list[tuple[str, tuple[str, ...]]] | None,
        fallback: Iterable[str] | None,
    ) -> tuple[str, ...]:
        """Resolve channel locks using all/name/branch grouping."""
        default = tuple(fallback) if fallback is not None else (
            "translateX", "translateY", "translateZ",
            "scaleX", "scaleY", "scaleZ", "visibility",
        )
        if mode == "all":
            return (groups or {}).get("__all__", default)
        if mode == "name":
            leaf_name = joint.rsplit("|", 1)[-1].lower()
            for pattern, attributes in name_rules or []:
                pattern = pattern.strip().lower()
                if pattern and pattern in leaf_name:
                    return attributes
            return default
        key = lock_keys.get(joint, "")
        return (groups or {}).get(key, default) if key else default

    def _validate_visibility_controller(
        self,
        controller: str | None,
        attribute_name: str,
    ) -> str | None:
        """Validate the optional transform which receives FK-finger."""
        if not controller:
            return None
        if not self.cmds.objExists(controller):
            raise FKBuilderError("表示切替コントローラーが存在しません。")
        if self.cmds.nodeType(controller) != "transform":
            raise FKBuilderError(
                "表示切替コントローラーはTransformを選択してください。"
            )
        controller = (self.cmds.ls(controller, long=True) or [controller])[0]
        plug = "{0}.{1}".format(controller, attribute_name)
        if self.cmds.objExists(plug):
            raise FKBuilderError(
                "表示切替属性がすでに存在します: {0}".format(plug)
            )
        return controller

    def _create_visibility_switch(
        self,
        settings_controller: str,
        root_zero: str,
        attribute_name: str,
        nice_name: str,
    ) -> None:
        """Add an OFF/ON channel and drive the complete FK hierarchy."""
        self.cmds.addAttr(
            settings_controller,
            longName=attribute_name,
            niceName=nice_name,
            attributeType="enum",
            enumName="OFF:ON",
            defaultValue=1,
            keyable=True,
        )
        self.cmds.connectAttr(
            "{0}.{1}".format(settings_controller, attribute_name),
            "{0}.visibility".format(root_zero),
            force=True,
        )

    @staticmethod
    def _visibility_attribute_names(name: str) -> tuple[str, str]:
        """Return a Maya-safe long name and the requested channel label."""
        nice_name = name.strip()
        if not nice_name:
            raise FKBuilderError("表示切替の属性名を入力してください。")
        attribute_name = re.sub(r"[^A-Za-z0-9_]", "_", nice_name)
        attribute_name = re.sub(r"_+", "_", attribute_name).strip("_")
        if not attribute_name:
            raise FKBuilderError(
                "属性名には半角英数字を1文字以上含めてください。"
            )
        if attribute_name[0].isdigit():
            attribute_name = "FK_" + attribute_name
        return attribute_name, nice_name

    def color_groups(self, root_joint: str) -> list[tuple[str, str]]:
        """Return color keys and UI labels for the selected hierarchy."""
        joints = joint_hierarchy(self.cmds, root_joint)
        branches = self._branch_roots(joints)
        return [
            (joint, joint.rsplit("|", 1)[-1])
            for joint in branches
        ]

    @staticmethod
    def _validate_shape_data(
        shape_data: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Validate optional controller-shape library data."""
        if not shape_data:
            return None
        components = shape_data.get("components") or [shape_data]
        for component in components:
            points = component.get("points")
            degree = int(component.get("degree", 1))
            if not isinstance(points, list) or len(points) <= degree:
                raise FKBuilderError("選択した形状データが無効です。")
        return shape_data

    @staticmethod
    def _color_for_joint(
        joint: str,
        controller_colors: dict[str, int | None] | None,
        color_keys: dict[str, str] | None = None,
        color_mode: str = "branch",
        name_color_rules: list[tuple[str, int | None]] | None = None,
    ) -> int | None:
        """Resolve a color using the selected grouping strategy."""
        if color_mode == "all":
            return (controller_colors or {}).get("__all__")
        if color_mode == "name":
            leaf_name = joint.rsplit("|", 1)[-1].lower()
            for pattern, color_index in name_color_rules or []:
                if pattern.strip().lower() in leaf_name and pattern.strip():
                    return color_index
            return None
        if not controller_colors:
            return None
        if color_keys is None:
            leaf_name = joint.rsplit("|", 1)[-1].rsplit(":", 1)[-1].lower()
            tokens = set(filter(None, re.split(r"[^a-z]+", leaf_name)))
            for part in ("thumb", "index", "middle", "ring", "pinky"):
                if part in tokens:
                    return controller_colors.get(part)
            return None
        key = color_keys.get(joint, "")
        return controller_colors.get(key) if key else None

    @staticmethod
    def _color_keys(
        joints: list[str],
    ) -> dict[str, str]:
        """Map every joint to its nearest recursive branch-root key."""
        branch_roots = set(FKBuilder._branch_roots(joints))
        has_split = joints[0] not in branch_roots
        joint_set = set(joints)
        result: dict[str, str] = {}
        for joint in joints:
            if joint in branch_roots:
                result[joint] = joint
                continue
            parent = FKBuilder._nearest_joint_parent(
                joint, joint_set
            )
            result[joint] = result.get(parent, "") if has_split else joints[0]
        return result

    @staticmethod
    def _offset_for_joint(
        joint: str,
        offsets: dict[
            str, tuple[tuple[float, float, float], tuple[float, float, float]]
        ] | None,
        offset_keys: dict[str, str],
        mode: str,
        name_rules: list[
            tuple[
                str,
                tuple[float, float, float],
                tuple[float, float, float],
            ]
        ] | None,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Resolve baked curve position and rotation offsets."""
        default = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        if mode == "all":
            return (offsets or {}).get("__all__", default)
        if mode == "name":
            leaf_name = joint.rsplit("|", 1)[-1].lower()
            for pattern, position, rotation in name_rules or []:
                pattern = pattern.strip().lower()
                if pattern and pattern in leaf_name:
                    return position, rotation
            return default
        key = offset_keys.get(joint, "")
        return (offsets or {}).get(key, default) if key else default

    @staticmethod
    def _branch_roots(joints: list[str]) -> list[str]:
        """Return root and every child beginning a recursively split branch."""
        joint_set = set(joints)
        children_by_parent: dict[str, list[str]] = {
            joint: [] for joint in joints
        }
        for joint in joints[1:]:
            parent = FKBuilder._nearest_joint_parent(
                joint, joint_set
            )
            if parent:
                children_by_parent[parent].append(joint)

        branch_roots: list[str] = []
        for joint in joints:
            children = children_by_parent[joint]
            if len(children) > 1:
                branch_roots.extend(
                    sorted(
                        children,
                        key=lambda child: child.rsplit("|", 1)[-1].lower(),
                    )
                )
        return branch_roots or [joints[0]]

    @staticmethod
    def _nearest_joint_parent(
        joint: str,
        joint_set: set[str],
    ) -> str:
        """Find the nearest ancestor joint through intervening groups."""
        parent_path = joint.rsplit("|", 1)[0]
        while parent_path and parent_path not in joint_set:
            parent_path = parent_path.rsplit("|", 1)[0]
        return parent_path if parent_path in joint_set else ""
