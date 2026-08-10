import unittest

from fk_builder.builder import FKBuilder
from fk_builder.controller import CubeControllerFactory
from fk_builder.shape_library import load_mox_shapes
from fk_builder.utils import FKBuilderError


class ShapeLibraryTests(unittest.TestCase):
    def test_bundled_shapes_have_valid_components(self):
        shapes = load_mox_shapes()
        self.assertTrue(shapes)
        for shape_id, shape in shapes.items():
            self.assertTrue(shape_id)
            components = shape.get("components") or [shape]
            self.assertTrue(components)
            for component in components:
                degree = int(component.get("degree", 1))
                points = component.get("points")
                self.assertIsInstance(points, list)
                self.assertGreater(len(points), degree)

    def test_invalid_shape_data_is_rejected(self):
        with self.assertRaises(FKBuilderError):
            FKBuilder._validate_shape_data(
                {"degree": 3, "points": [[0.0, 0.0, 0.0]]}
            )


class ControllerGeometryTests(unittest.TestCase):
    def test_position_offset_is_baked_into_curve_point(self):
        result = CubeControllerFactory._offset_point(
            (1.0, 2.0, 3.0),
            (4.0, 5.0, 6.0),
            (0.0, 0.0, 0.0),
        )
        self.assertEqual(result, (5.0, 7.0, 9.0))

    def test_z_rotation_is_baked_into_curve_point(self):
        result = CubeControllerFactory._offset_point(
            (1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 90.0),
        )
        self.assertAlmostEqual(result[0], 0.0, places=7)
        self.assertAlmostEqual(result[1], 1.0, places=7)
        self.assertAlmostEqual(result[2], 0.0, places=7)


class BuilderConfigurationTests(unittest.TestCase):
    def test_visibility_attribute_is_maya_safe(self):
        self.assertEqual(
            FKBuilder._visibility_attribute_names("FK-finger controls"),
            ("FK_finger_controls", "FK-finger controls"),
        )

    def test_visibility_attribute_cannot_be_empty(self):
        with self.assertRaises(FKBuilderError):
            FKBuilder._visibility_attribute_names("---")

    def test_recursive_split_creates_branch_groups(self):
        joints = [
            "|hand_jnt",
            "|hand_jnt|index_01_jnt",
            "|hand_jnt|index_01_jnt|index_02_jnt",
            "|hand_jnt|middle_01_jnt",
            "|hand_jnt|middle_01_jnt|middle_02_jnt",
        ]
        self.assertEqual(
            FKBuilder._branch_roots(joints),
            [
                "|hand_jnt|index_01_jnt",
                "|hand_jnt|middle_01_jnt",
            ],
        )


if __name__ == "__main__":
    unittest.main()
