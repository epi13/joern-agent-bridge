"""Filesystem confinement for source and artifact paths."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from .errors import PathViolation


def approved_roots(extra: Iterable[Path] = ()) -> tuple[Path, ...]:
    configured = os.environ.get("JOERN_AGENT_APPROVED_ROOTS", "")
    roots = [Path.cwd(), *extra]
    roots.extend(Path(item) for item in configured.split(os.pathsep) if item)
    resolved: list[Path] = []
    for root in roots:
        candidate = root.expanduser().resolve(strict=True)
        if candidate not in resolved:
            resolved.append(candidate)
    return tuple(resolved)


def resolve_confined(
    value: str | Path,
    roots: Iterable[Path],
    *,
    must_exist: bool = True,
    expect: str = "any",
) -> Path:
    raw = Path(value).expanduser()
    try:
        resolved = raw.resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise PathViolation(
            "invalid_path",
            f"Cannot resolve path: {raw}",
            details={"path": str(raw)},
        ) from exc

    allowed = tuple(root.expanduser().resolve(strict=True) for root in roots)
    if not any(resolved == root or resolved.is_relative_to(root) for root in allowed):
        raise PathViolation(
            "path_outside_approved_roots",
            "Path is outside the approved roots",
            details={"path": str(resolved), "approved_roots": [str(root) for root in allowed]},
        )
    if must_exist and expect == "file" and not resolved.is_file():
        raise PathViolation("not_a_file", "Expected a file", details={"path": str(resolved)})
    if must_exist and expect == "dir" and not resolved.is_dir():
        raise PathViolation(
            "not_a_directory", "Expected a directory", details={"path": str(resolved)}
        )
    return resolved


def safe_artifact_path(root: Path, relative: str | Path) -> Path:
    root = root.expanduser().resolve(strict=True)
    candidate = (root / relative).resolve(strict=False)
    if candidate == root or not candidate.is_relative_to(root):
        raise PathViolation(
            "artifact_path_escape",
            "Artifact path escapes its root",
            details={"path": str(candidate), "root": str(root)},
        )
    return candidate
