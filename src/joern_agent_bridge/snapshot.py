"""Graph snapshot creation, comparison, and trusted validation records."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Limits, Snapshot
from .service import JoernService
from .workspace import source_state

_RELEVANT_SUFFIXES = {
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".cxx",
    ".hpp",
    ".java",
    ".kt",
    ".kts",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".py",
    ".php",
}


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["/usr/bin/git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def repository_state(repo: Path, language: str) -> dict[str, str]:
    repo = repo.resolve(strict=True)
    commit = _git(repo, "rev-parse", "HEAD").strip() or "uncommitted"
    tracked_changes = set(_git(repo, "diff", "--name-only", "HEAD").splitlines())
    untracked = set(_git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    relevant = sorted(
        path
        for path in tracked_changes | untracked
        if Path(path).suffix.lower() in _RELEVANT_SUFFIXES
    )
    diff = _git(repo, "diff", "--binary", "HEAD", "--", *relevant)
    diff_digest = hashlib.sha256(diff.encode())
    for relative in relevant:
        path = repo / relative
        if path.is_file() and relative in untracked:
            diff_digest.update(relative.encode())
            diff_digest.update(path.read_bytes())
    state = source_state(repo, language)
    return {
        "commit": commit,
        "working_tree_hash": state,
        "relevant_diff_hash": diff_digest.hexdigest(),
    }


def create_snapshot(
    service: JoernService,
    project: Path,
    output: Path,
    *,
    phase: str,
    language: str = "c",
    timeout: float = 300,
) -> Snapshot:
    if phase not in {"baseline", "post"}:
        raise ValueError("phase must be baseline or post")
    limits = Limits(timeout=timeout, max_results=200, max_nodes=1000)
    summary = service.query(project, "snapshot", language=language, limits=limits)
    if not isinstance(summary.data, dict):
        raise TypeError("Joern snapshot operation returned a non-object result")
    methods = list(summary.data.get("methods", []))
    cfg_summaries = list(summary.data.get("cfg_summaries", []))
    calls = list(summary.data.get("calls", []))
    controls = list(summary.data.get("controls", []))
    warnings = list(summary.warnings)

    state = repository_state(project, language)
    snapshot = Snapshot(
        status="complete",
        repository_commit=state["commit"],
        working_tree_hash=state["working_tree_hash"],
        relevant_diff_hash=state["relevant_diff_hash"],
        joern_version=service.installation.version,
        language=language,
        source_root=str(project.resolve()),
        query_definitions=["snapshot(methods,cfg_summaries,callees,control_dependencies)"],
        analyzed_methods=methods,
        method_cfg_summaries=cfg_summaries,
        call_relationships=calls,
        control_dependencies=controls,
        warnings=sorted(set(warnings)),
        timeout_seconds=timeout,
        timestamp=datetime.now(UTC).isoformat(),
        phase=phase,  # type: ignore[arg-type]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(snapshot.model_dump_json(indent=2) + "\n")
    return snapshot


def compare_snapshots(before: Snapshot, after: Snapshot) -> dict[str, Any]:
    def names(snapshot: Snapshot) -> set[str]:
        return {
            str(item.get("fullName") or item.get("name"))
            for item in snapshot.analyzed_methods
            if isinstance(item, dict) and (item.get("fullName") or item.get("name"))
        }

    before_names = names(before)
    after_names = names(after)
    before_cfg = {
        str(item["method"]): int(item["node_count"]) for item in before.method_cfg_summaries
    }
    after_cfg = {
        str(item["method"]): int(item["node_count"]) for item in after.method_cfg_summaries
    }
    changed_cfg = {
        method: {"before": before_cfg.get(method), "after": after_cfg.get(method)}
        for method in sorted(before_cfg.keys() | after_cfg.keys())
        if before_cfg.get(method) != after_cfg.get(method)
    }
    return {
        "schema_version": 1,
        "before": before.timestamp,
        "after": after.timestamp,
        "methods_added": sorted(after_names - before_names),
        "methods_removed": sorted(before_names - after_names),
        "cfg_node_count_changes": changed_cfg,
        "source_state_changed": before.working_tree_hash != after.working_tree_hash,
        "warnings": sorted(set(before.warnings + after.warnings)),
    }


def load_snapshot(path: Path) -> Snapshot:
    return Snapshot.model_validate_json(path.read_text())


def write_validation_record(
    project: Path,
    baseline: Snapshot,
    post: Snapshot,
    comparison: dict[str, Any],
) -> Path:
    state = repository_state(project, post.language)
    record = {
        "schema_version": 1,
        "status": "complete",
        "repository_commit": state["commit"],
        "working_tree_hash": state["working_tree_hash"],
        "relevant_diff_hash": state["relevant_diff_hash"],
        "joern_version": post.joern_version,
        "language": post.language,
        "source_root": str(project.resolve()),
        "baseline": baseline.model_dump(mode="json"),
        "post": post.model_dump(mode="json"),
        "comparison": comparison,
        "generated_by": "joern-agent validate",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    destination = project / ".joern-agent" / "validation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return destination
