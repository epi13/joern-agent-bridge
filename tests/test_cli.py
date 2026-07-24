from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from joern_agent_bridge.cli import app


class FakeService:
    def health(self) -> dict[str, Any]:
        return {"ok": True, "joern_version": "4.0.583"}


def test_doctor_json(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr("joern_agent_bridge.cli._service", lambda _project: FakeService())
    result = CliRunner().invoke(app, ["doctor", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert '"ok": true' in result.stdout


def test_cli_help_lists_expected_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("doctor", "parse", "cfg", "dataflow", "snapshot", "mcp"):
        assert command in result.stdout
