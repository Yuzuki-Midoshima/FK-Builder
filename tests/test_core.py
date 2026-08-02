import unittest

from finger_fk_builder.builder import FingerFKBuilder
from finger_fk_builder.utils import (
    FingerFKError,
    controller_name,
    joint_hierarchy,
    selected_joint,
    selected_transform,
    short_name,
    zero_name,
)


class NamingTests(unittest.TestCase):
    def test_short_name_removes_dag_path(self):
        self.assertEqual(short_name("|hand|index1_jnt"), "index1_jnt")

    def test_output_names_preserve_namespace(self):
        joint = "|character:hand|character:index1_jnt"
        self.assertEqual(controller_name(joint), "character:index1_anim")
        self.assertEqual(zero_name(joint), "character:index1_zero")

    def test_controller_name_requires_joint_suffix(self):
        with self.assertRaises(FingerFKError):
            controller_name("index1")


class SelectionCmds:
    def __init__(self, joints=None, transforms=None):
        self.joints = joints or []
        self.transforms = transforms or []

    def ls(self, selection=False, long=False, type=None):
        if type == "joint":
            return self.joints
        if type == "transform":
            return self.transforms
        return []


class SelectionTests(unittest.TestCase):
    def test_selected_joint_returns_long_path(self):
        cmds = SelectionCmds(joints=["|hand|index1_jnt"])
        self.assertEqual(selected_joint(cmds), "|hand|index1_jnt")

    def test_selected_joint_requires_selection(self):
        with self.assertRaises(FingerFKError):
            selected_joint(SelectionCmds())

    def test_selected_transform_requires_exactly_one(self):
        with self.assertRaises(FingerFKError):
            selected_transform(SelectionCmds(transforms=["a", "b"]))


class HierarchyCmds:
    def objExists(self, node):
        return node == "root_jnt"

    def nodeType(self, node):
        return "joint"

    def ls(self, node, long=False):
        return ["|root_jnt"]

    def listRelatives(self, node, **kwargs):
        return ["|root_jnt|child_jnt|end_jnt", "|root_jnt|child_jnt"]


class HierarchyTests(unittest.TestCase):
    def test_joint_hierarchy_is_parent_before_child(self):
        self.assertEqual(
            joint_hierarchy(HierarchyCmds(), "root_jnt"),
            ["|root_jnt", "|root_jnt|child_jnt", "|root_jnt|child_jnt|end_jnt"],
        )


class ColorResolutionTests(unittest.TestCase):
    def test_color_is_resolved_from_delimited_finger_name(self):
        colors = {"index": 6, "ring": 14}
        self.assertEqual(
            FingerFKBuilder._color_for_joint("|hand|L_index_01_jnt", colors),
            6,
        )

    def test_partial_token_does_not_match(self):
        self.assertIsNone(
            FingerFKBuilder._color_for_joint(
                "|hand|L_indexHelper_jnt",
                {"index": 6},
            )
        )


if __name__ == "__main__":
    unittest.main()
