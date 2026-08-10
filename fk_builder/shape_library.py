"""Load bundled and user-provided controller-shape libraries."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


USER_DATA_ENV = "FK_BUILDER_USER_DATA_DIR"
LIBRARY_DIRECTORY_NAME = "shape_libraries"
BUNDLED_LIBRARY_PATH = (
    Path(__file__).resolve().parent / "data" / "bundled_shapes.json"
)


class ShapeLibraryError(ValueError):
    """Raised when a shape-library file is unreadable or invalid."""


def default_user_data_dir() -> Path:
    """Return the external FK-Builder user-data directory."""
    configured = os.environ.get(USER_DATA_ENV)
    if configured:
        return Path(configured).expanduser()

    try:
        from maya import cmds  # type: ignore

        scripts_dir = Path(cmds.internalVar(userScriptDir=True))
        return scripts_dir / "FK-Builder-UserData"
    except (ImportError, AttributeError, RuntimeError):
        pass

    maya_app_dir = os.environ.get("MAYA_APP_DIR")
    if maya_app_dir:
        return Path(maya_app_dir).expanduser() / "scripts" / "FK-Builder-UserData"
    return Path.home() / "Documents" / "maya" / "scripts" / "FK-Builder-UserData"


def external_library_dir(user_data_dir: Path | None = None) -> Path:
    """Return the directory containing local, untracked JSON libraries."""
    return (user_data_dir or default_user_data_dir()) / LIBRARY_DIRECTORY_NAME


def discover_external_libraries(
    user_data_dir: Path | None = None,
) -> tuple[Path, ...]:
    """Return external JSON library files in stable filename order."""
    directory = external_library_dir(user_data_dir)
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob("*.json"), key=lambda path: path.name.lower()))


def load_shape_library(path: Path) -> dict[str, dict[str, Any]]:
    """Load and validate one shape library."""
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ShapeLibraryError(
            "シェイプライブラリを読み込めません: {0}: {1}".format(path, exc)
        ) from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("shapes"), dict):
        raise ShapeLibraryError(
            "シェイプライブラリにはshapesオブジェクトが必要です: {0}".format(path)
        )

    library = payload.get("library")
    if not isinstance(library, dict):
        library = {}
    library_name = str(
        library.get("name") or payload.get("name") or path.stem
    )

    result: dict[str, dict[str, Any]] = {}
    for shape_id, raw_shape in payload["shapes"].items():
        if not isinstance(shape_id, str) or not shape_id.strip():
            raise ShapeLibraryError("シェイプIDが不正です: {0}".format(path))
        if not isinstance(raw_shape, dict):
            raise ShapeLibraryError(
                "シェイプデータがオブジェクトではありません: {0}: {1}".format(
                    path, shape_id
                )
            )
        shape = dict(raw_shape)
        components = shape.get("components") or [shape]
        if not isinstance(components, list) or not components:
            raise ShapeLibraryError(
                "シェイプのcomponentsが不正です: {0}: {1}".format(path, shape_id)
            )
        for component in components:
            if not isinstance(component, dict):
                raise ShapeLibraryError(
                    "シェイプcomponentがオブジェクトではありません: {0}: {1}".format(
                        path, shape_id
                    )
                )
            try:
                degree = int(component.get("degree", 1))
            except (TypeError, ValueError) as exc:
                raise ShapeLibraryError(
                    "シェイプのdegreeが整数ではありません: {0}: {1}".format(
                        path, shape_id
                    )
                ) from exc
            if degree < 1:
                raise ShapeLibraryError(
                    "シェイプのdegreeは1以上が必要です: {0}: {1}".format(
                        path, shape_id
                    )
                )
            points = component.get("points")
            if not isinstance(points, list) or len(points) <= degree:
                raise ShapeLibraryError(
                    "シェイプのpointsが不足しています: {0}: {1}".format(
                        path, shape_id
                    )
                )
            if any(
                not isinstance(point, (list, tuple))
                or len(point) != 3
                or any(not isinstance(axis, (int, float)) for axis in point)
                for point in points
            ):
                raise ShapeLibraryError(
                    "シェイプのpointには3つの数値が必要です: {0}: {1}".format(
                        path, shape_id
                    )
                )
        shape["library_name"] = library_name
        shape["library_path"] = str(path)
        result[shape_id] = shape
    return result


def load_shape_libraries(
    user_data_dir: Path | None = None,
    include_external: bool = True,
) -> dict[str, dict[str, Any]]:
    """Load bundled shapes and optional external UserData libraries."""
    paths = [BUNDLED_LIBRARY_PATH]
    if include_external:
        paths.extend(discover_external_libraries(user_data_dir))

    shapes: dict[str, dict[str, Any]] = {}
    for path in paths:
        for shape_id, shape in load_shape_library(path).items():
            if shape_id in shapes:
                raise ShapeLibraryError(
                    "シェイプIDが重複しています: {0} ({1})".format(
                        shape_id, path
                    )
                )
            shapes[shape_id] = shape
    return shapes
