"""Codex lifecycle hook implementation."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .snapshot import _RELEVANT_SUFFIXES, repository_state


def _emit(payload: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return 0


def session_start(payload: dict[str, Any]) -> dict[str, Any]:
    cwd = Path(str(payload.get("cwd") or ".")).resolve()
    missing = [
        executable
        for executable in ("joern", "joern-parse", "joern-agent-mcp")
        if not shutil.which(executable)
    ]
    project_config = cwd / ".codex" / "config.toml"
    if missing or not project_config.is_file():
        details = []
        if missing:
            details.append(f"missing executables: {', '.join(missing)}")
        if not project_config.is_file():
            details.append("missing .codex/config.toml")
        return {
            "continue": True,
            "systemMessage": "Joern integration is incomplete: " + "; ".join(details),
        }
    return {
        "continue": True,
        "systemMessage": "Joern graph validation is available; use it for graph-sensitive edits.",
    }


def _changed_files(repo: Path) -> list[Path]:
    result = subprocess.run(  # noqa: S603
        [
            "/usr/bin/git",
            "-C",
            str(repo),
            "ls-files",
            "--modified",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("git status failed")
    output = result.stdout.decode("utf-8", errors="replace")
    paths = []
    for path in output.split("\0"):
        if path:
            paths.append(repo / path)
    return paths


def stop(payload: dict[str, Any]) -> dict[str, Any]:
    cwd = Path(str(payload.get("cwd") or ".")).resolve()
    repo_result = subprocess.run(  # noqa: S603
        ["/usr/bin/git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if repo_result.returncode != 0:
        return {"continue": True}
    repo = Path(repo_result.stdout.strip()).resolve()
    changed = _changed_files(repo)
    graph_sensitive = [path for path in changed if path.suffix.lower() in _RELEVANT_SUFFIXES]
    if not graph_sensitive:
        return {"continue": True}

    active = bool(payload.get("stop_hook_active", False))
    record_path = repo / ".joern-agent" / "validation.json"
    problem: str | None = None
    if not record_path.is_file():
        problem = "no trusted Joern validation record exists"
    else:
        try:
            record = json.loads(record_path.read_text())
            language = str(record.get("language", "c"))
            current = repository_state(repo, language)
            if record.get("status") != "complete":
                problem = "the Joern validation record reports failure"
            elif record.get("working_tree_hash") != current["working_tree_hash"]:
                problem = "the Joern validation record is stale for the current source tree"
            elif record.get("relevant_diff_hash") != current["relevant_diff_hash"]:
                problem = "the Joern validation record is stale for the current diff"
            elif not isinstance(record.get("baseline"), dict):
                problem = "the Joern validation record has no baseline snapshot"
            elif not isinstance(record.get("post"), dict):
                problem = "the Joern validation record has no post-edit snapshot"
            elif record["post"].get("status") != "complete":
                problem = "the post-edit Joern snapshot failed"
        except (OSError, ValueError, TypeError, KeyError):
            problem = "the Joern validation record is malformed"

    if problem is None:
        return {"continue": True}
    instruction = (
        f"Graph-sensitive source changes cannot be completed because {problem}. "
        "Run `scripts/joern-check` from the repository root, resolve any failure, "
        "and retry. The record must match both the current source-state and diff hashes."
    )
    if active:
        return {
            "continue": True,
            "systemMessage": instruction
            + " Stop-hook continuation is already active, so it will not recurse again.",
        }
    return {"continue": False, "stopReason": instruction, "systemMessage": instruction}


def hook_main(event: str) -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise TypeError("hook input must be a JSON object")
        if event == "session-start":
            return _emit(session_start(payload))
        if event == "stop":
            return _emit(stop(payload))
        raise ValueError(f"unknown hook event: {event}")
    except Exception as exc:  # fail closed with valid JSON
        return _emit(
            {
                "continue": False,
                "stopReason": f"Joern hook implementation failure: {exc}",
                "systemMessage": "Joern hook failed closed; inspect the hook and rerun validation.",
            }
        )
