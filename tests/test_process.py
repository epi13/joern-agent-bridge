from __future__ import annotations

from pathlib import Path

import pytest

from joern_agent_bridge.errors import JoernExecutionError
from joern_agent_bridge.process import run_process, sanitized_environment


def test_process_uses_argument_array_without_shell(tmp_path: Path) -> None:
    result = run_process(
        [Path("/usr/bin/python3"), "-c", "import sys; print(sys.argv[1])", "$(touch nope)"],
        cwd=tmp_path,
        timeout=10,
    )
    assert result.stdout.strip() == "$(touch nope)"
    assert not (tmp_path / "nope").exists()


def test_output_is_bounded(tmp_path: Path) -> None:
    result = run_process(
        [Path("/usr/bin/python3"), "-c", "print('x' * 1000)"],
        cwd=tmp_path,
        timeout=10,
        output_limit=100,
    )
    assert len(result.stdout.encode()) == 100
    assert result.stdout_truncated


def test_timeout_terminates_process_group(tmp_path: Path) -> None:
    with pytest.raises(JoernExecutionError) as error:
        run_process(
            [Path("/usr/bin/python3"), "-c", "import time; time.sleep(30)"],
            cwd=tmp_path,
            timeout=1,
        )
    assert error.value.code == "process_timeout"


def test_environment_is_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_TEST_SECRET", "do-not-forward")
    env = sanitized_environment()
    assert "BRIDGE_TEST_SECRET" not in env
    assert "PATH" in env
    with pytest.raises(ValueError):
        sanitized_environment({"BRIDGE_TEST_SECRET": "x"})


def test_executable_must_be_absolute(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="absolute"):
        run_process(["python3", "-c", "pass"], cwd=tmp_path, timeout=1)
