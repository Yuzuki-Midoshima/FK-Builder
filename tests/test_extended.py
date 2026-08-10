import json
from pathlib import Path
import tempfile
import unittest

from fk_builder.builder import FKBuilder
from fk_builder.controller import CubeControllerFactory
from fk_builder.shape_library import (
    ShapeLibraryError,
    discover_external_libraries,
    load_shape_libraries,
)
from fk_builder.utils import FKBuilderError


class ShapeLibraryTests(unittest.TestCase):
    def test_bundled_original_shapes_have_valid_components(self):
        shapes = load_shape_libraries(include_external=False)
        self.assertEqual(
            set(shapes),
            {"basic_circle", "basic_square", "basic_diamond", "basic_cross"},
        )
        for shape in shapes.values():
            self.assertEqual(shape["library_name"], "FK Builder Basic Shapes")
            components = shape.get("components") or [shape]
            for component in components:
                degree = int(component.get("degree", 1))
                self.assertGreater(len(component["points"]), degree)

    def test_external_library_is_loaded_from_user_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary)
            library_dir = user_data / "shape_libraries"
            library_dir.mkdir()
            (library_dir / "custom.json").write_text(
                json.dumps(
                    {
                        "library": {"name": "My Shapes"},
                        "shapes": {
                            "custom_triangle": {
                                "label": "Triangle",
                                "degree": 1,
                                "points": [[0, 0, 1], [1, 0, -1], [-1, 0, -1], [0, 0, 1]],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            shapes = load_shape_libraries(user_data_dir=user_data)
            self.assertIn("custom_triangle", shapes)
            self.assertEqual(shapes["custom_triangle"]["library_name"], "My Shapes")

    def test_missing_external_directory_uses_bundled_shapes(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary) / "missing"
            self.assertEqual(discover_external_libraries(user_data), ())
            self.assertEqual(len(load_shape_libraries(user_data)), 4)

    def test_duplicate_shape_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary)
            library_dir = user_data / "shape_libraries"
            library_dir.mkdir()
            (library_dir / "duplicate.json").write_text(
                json.dumps(
                    {
                        "shapes": {
                            "basic_circle": {
                                "degree": 1,
                                "points": [[0, 0, 0], [1, 0, 0]],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ShapeLibraryError):
                load_shape_libraries(user_data)

    def test_invalid_external_degree_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_data = Path(temporary)
            library_dir = user_data / "shape_libraries"
            library_dir.mkdir()
            (library_dir / "invalid.json").write_text(
                json.dumps(
                    {
                        "shapes": {
                            "invalid": {
                                "degree": "not-an-integer",
                                "points": [[0, 0, 0], [1, 0, 0]],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ShapeLibraryError):
                load_shape_libraries(user_data)

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
