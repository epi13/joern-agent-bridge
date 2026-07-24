from __future__ import annotations

import json
from pathlib import Path

from joern_agent_bridge.hooks import session_start, stop
from joern_agent_bridge.snapshot import repository_state


def payload(repo: Path, active: bool = False) -> dict[str, object]:
    return {"cwd": str(repo), "hook_event_name": "Stop", "stop_hook_active": active}


def write_record(repo: Path, *, status: str = "complete", stale: bool = False) -> None:
    state = repository_state(repo, "c")
    record = {
        "schema_version": 1,
        "status": status,
        "language": "c",
        "working_tree_hash": "stale" if stale else state["working_tree_hash"],
        "relevant_diff_hash": state["relevant_diff_hash"],
        "baseline": {"status": "complete"},
        "post": {"status": status},
    }
    destination = repo / ".joern-agent" / "validation.json"
    destination.parent.mkdir()
    destination.write_text(json.dumps(record))


def test_no_source_changes_is_allowed(git_repo: Path) -> None:
    assert stop(payload(git_repo))["continue"] is True


def test_documentation_only_change_is_allowed(git_repo: Path) -> None:
    (git_repo / "README.md").write_text("# Changed\n")
    assert stop(payload(git_repo))["continue"] is True


def test_source_change_without_analysis_is_rejected(git_repo: Path) -> None:
    (git_repo / "main.c").write_text("int main(void) { return 1; }\n")
    result = stop(payload(git_repo))
    assert result["continue"] is False
    assert "scripts/joern-check" in str(result["stopReason"])


def test_stale_analysis_is_rejected(git_repo: Path) -> None:
    (git_repo / "main.c").write_text("int main(void) { return 1; }\n")
    write_record(git_repo, stale=True)
    assert stop(payload(git_repo))["continue"] is False


def test_failed_analysis_is_rejected(git_repo: Path) -> None:
    (git_repo / "main.c").write_text("int main(void) { return 1; }\n")
    write_record(git_repo, status="failed")
    assert stop(payload(git_repo))["continue"] is False


def test_valid_current_analysis_is_allowed(git_repo: Path) -> None:
    (git_repo / "main.c").write_text("int main(void) { return 1; }\n")
    write_record(git_repo)
    assert stop(payload(git_repo))["continue"] is True


def test_repeated_stop_avoids_infinite_loop(git_repo: Path) -> None:
    (git_repo / "main.c").write_text("int main(void) { return 1; }\n")
    result = stop(payload(git_repo, active=True))
    assert result["continue"] is True
    assert "will not recurse" in str(result["systemMessage"])


def test_untracked_source_directory_is_rejected(git_repo: Path) -> None:
    generated = git_repo / "new-source"
    generated.mkdir()
    (generated / "worker.py").write_text("print('work')\n")
    assert stop(payload(git_repo))["continue"] is False


def test_session_start_reports_missing_tools(git_repo: Path) -> None:
    result = session_start({"cwd": str(git_repo)})
    assert result["continue"] is True
    assert "incomplete" in str(result["systemMessage"])
