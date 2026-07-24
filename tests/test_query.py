from __future__ import annotations

from pathlib import Path

import pytest

from joern_agent_bridge.discovery import JoernInstallation
from joern_agent_bridge.errors import JoernExecutionError
from joern_agent_bridge.models import ProcessResult
from joern_agent_bridge.query import QueryRunner


def runner(tmp_path: Path) -> QueryRunner:
    fake = tmp_path / "joern"
    script = tmp_path / "query.sc"
    fake.write_text("")
    script.write_text("")
    install = JoernInstallation(fake, fake, fake, None, "4.0.583")
    return QueryRunner(install, script)


def test_structured_json_is_parsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_run(argv: list[object], **_: object) -> ProcessResult:
        seen.extend(str(item) for item in argv)
        return ProcessResult(
            argv=seen,
            returncode=0,
            stdout='noise\nJOERN_AGENT_RESULT:[{"name":"main"}]\n',
            stderr="",
            duration_ms=1,
        )

    monkeypatch.setattr("joern_agent_bridge.query.run_process", fake_run)
    result = runner(tmp_path).run(tmp_path / "cpg.bin", "methods")
    assert result.data == [{"name": "main"}]
    assert "--script" in seen
    assert all(";" not in item for item in seen)


@pytest.mark.parametrize(
    "stdout,code",
    [
        ("no marker\n", "malformed_joern_output"),
        ("JOERN_AGENT_RESULT:not-json\n", "malformed_joern_json"),
        ("JOERN_AGENT_RESULT:[]\nJOERN_AGENT_RESULT:[]\n", "malformed_joern_output"),
    ],
)
def test_malformed_output_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdout: str, code: str
) -> None:
    monkeypatch.setattr(
        "joern_agent_bridge.query.run_process",
        lambda *_args, **_kwargs: ProcessResult(
            argv=[], returncode=0, stdout=stdout, stderr="", duration_ms=1
        ),
    )
    with pytest.raises(JoernExecutionError) as error:
        runner(tmp_path).run(tmp_path / "cpg.bin", "methods")
    assert error.value.code == code


def test_nonzero_joern_exit_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "joern_agent_bridge.query.run_process",
        lambda *_args, **_kwargs: ProcessResult(
            argv=[], returncode=2, stdout="", stderr="failed", duration_ms=1
        ),
    )
    with pytest.raises(JoernExecutionError) as error:
        runner(tmp_path).run(tmp_path / "cpg.bin", "methods")
    assert error.value.code == "joern_query_failed"
