from __future__ import annotations

from pathlib import Path

import pytest

from joern_agent_bridge.errors import PathViolation
from joern_agent_bridge.paths import resolve_confined, safe_artifact_path


def test_resolve_confined_accepts_child(tmp_path: Path) -> None:
    child = tmp_path / "source"
    child.mkdir()
    assert resolve_confined(child, (tmp_path,), expect="dir") == child


def test_resolve_confined_rejects_outside(tmp_path: Path) -> None:
    outside = tmp_path.parent
    with pytest.raises(PathViolation, match="outside"):
        resolve_confined(outside, (tmp_path,), expect="dir")


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PathViolation) as error:
        resolve_confined(root / "escape", (root,), expect="dir")
    assert error.value.code == "path_outside_approved_roots"


def test_path_type_is_checked(tmp_path: Path) -> None:
    item = tmp_path / "item"
    item.write_text("content")
    with pytest.raises(PathViolation) as error:
        resolve_confined(item, (tmp_path,), expect="dir")
    assert error.value.code == "not_a_directory"


def test_artifact_escape_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PathViolation):
        safe_artifact_path(tmp_path, "../escape")
