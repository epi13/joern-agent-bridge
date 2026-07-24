from __future__ import annotations

import threading
from pathlib import Path

import pytest

from joern_agent_bridge.discovery import JoernInstallation
from joern_agent_bridge.models import ProcessResult
from joern_agent_bridge.workspace import CpgWorkspace, source_state


def installation(tmp_path: Path) -> JoernInstallation:
    fake = tmp_path / "fake"
    fake.write_text("")
    return JoernInstallation(fake, fake, fake, None, "4.0.583")


def test_source_state_changes_with_source(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    file = source / "main.c"
    file.write_text("int main(void) { return 0; }\n")
    before = source_state(source, "c")
    file.write_text("int main(void) { return 1; }\n")
    assert source_state(source, "c") != before


def test_unsupported_language_fails(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="Unsupported"):
        source_state(tmp_path, "brainfuck")


def test_source_state_ignores_virtual_environments(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('source')\n")
    before = source_state(tmp_path, "python")
    ignored = tmp_path / ".venv" / "lib"
    ignored.mkdir(parents=True)
    (ignored / "dependency.py").write_text("print('dependency')\n")
    assert source_state(tmp_path, "python") == before


def test_cache_reuse_and_invalidation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "src"
    source.mkdir()
    file = source / "main.c"
    file.write_text("int main(void) { return 0; }\n")
    calls = 0

    def fake_run(argv: list[object], **_: object) -> ProcessResult:
        nonlocal calls
        calls += 1
        output = Path(argv[argv.index("--output") + 1])
        output.write_bytes(b"real-looking-cpg")
        return ProcessResult(
            argv=[str(item) for item in argv], returncode=0, stdout="", stderr="", duration_ms=1
        )

    monkeypatch.setattr("joern_agent_bridge.workspace.run_process", fake_run)
    workspace = CpgWorkspace(tmp_path / "cache")
    install = installation(tmp_path)
    first = workspace.ensure(source, install, language="c", timeout=10)
    second = workspace.ensure(source, install, language="c", timeout=10)
    assert first.cpg_path == second.cpg_path
    assert calls == 1
    file.write_text("int main(void) { return 1; }\n")
    third = workspace.ensure(source, install, language="c", timeout=10)
    assert third.cpg_path != first.cpg_path
    assert calls == 2


def test_concurrent_writers_are_serialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "main.c").write_text("int main(void) { return 0; }\n")
    calls = 0
    guard = threading.Lock()

    def fake_run(argv: list[object], **_: object) -> ProcessResult:
        nonlocal calls
        with guard:
            calls += 1
        output = Path(argv[argv.index("--output") + 1])
        output.write_bytes(b"cpg")
        return ProcessResult(
            argv=[str(item) for item in argv], returncode=0, stdout="", stderr="", duration_ms=1
        )

    monkeypatch.setattr("joern_agent_bridge.workspace.run_process", fake_run)
    workspace = CpgWorkspace(tmp_path / "cache")
    install = installation(tmp_path)
    errors: list[Exception] = []

    def worker() -> None:
        try:
            workspace.ensure(source, install, language="c", timeout=10)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert calls == 1
