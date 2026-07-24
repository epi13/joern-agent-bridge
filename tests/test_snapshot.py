from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from joern_agent_bridge.models import AnalysisResult, Snapshot
from joern_agent_bridge.snapshot import (
    compare_snapshots,
    create_snapshot,
    load_snapshot,
    write_validation_record,
)


def snapshot(methods: list[str], counts: dict[str, int], phase: str) -> Snapshot:
    return Snapshot(
        status="complete",
        repository_commit="abc",
        working_tree_hash=phase,
        relevant_diff_hash=phase,
        joern_version="4.0.583",
        language="c",
        source_root="/var/empty/example",
        query_definitions=["methods", "cfg"],
        analyzed_methods=[{"name": name} for name in methods],
        method_cfg_summaries=[
            {"method": method, "node_count": count} for method, count in counts.items()
        ],
        call_relationships=[],
        control_dependencies=[],
        warnings=[],
        timeout_seconds=10,
        timestamp=datetime.now(UTC).isoformat(),
        phase=phase,  # type: ignore[arg-type]
    )


def test_snapshot_comparison_reports_semantic_changes() -> None:
    before = snapshot(["a", "b"], {"a": 2, "b": 3}, "baseline")
    after = snapshot(["b", "c"], {"b": 4, "c": 1}, "post")
    result = compare_snapshots(before, after)
    assert result["methods_added"] == ["c"]
    assert result["methods_removed"] == ["a"]
    assert result["cfg_node_count_changes"]["b"] == {"before": 3, "after": 4}


class FakeSnapshotService:
    installation = SimpleNamespace(version="4.0.583")

    def query(self, _project: Path, operation: str, **parameters: Any) -> AnalysisResult:
        if operation == "snapshot":
            return AnalysisResult(
                ok=True,
                data={
                    "methods": [{"name": "main"}, {"name": "helper"}],
                    "cfg_summaries": [
                        {"method": "main", "node_count": 2},
                        {"method": "helper", "node_count": 2},
                    ],
                    "calls": [{"caller": "main", "callee": "helper"}],
                    "controls": [{"method": "main", "code": "argc > 1"}],
                },
                warnings=["bounded fixture"],
            )
        raise AssertionError((operation, parameters))


def test_create_load_and_record_snapshot(git_repo: Path) -> None:
    baseline_path = git_repo / "baseline.json"
    baseline = create_snapshot(
        FakeSnapshotService(),  # type: ignore[arg-type]
        git_repo,
        baseline_path,
        phase="baseline",
        timeout=10,
    )
    assert baseline.status == "complete"
    assert len(baseline.method_cfg_summaries) == 2
    assert load_snapshot(baseline_path) == baseline

    (git_repo / "main.c").write_text("int main(void) { return 1; }\n")
    post = create_snapshot(
        FakeSnapshotService(),  # type: ignore[arg-type]
        git_repo,
        git_repo / "post.json",
        phase="post",
        timeout=10,
    )
    comparison = compare_snapshots(baseline, post)
    record = write_validation_record(git_repo, baseline, post, comparison)
    assert record.is_file()
    assert "generated_by" in record.read_text()
