from __future__ import annotations

import json
import tomllib
from pathlib import Path


def test_project_codex_configuration_is_valid() -> None:
    root = Path(__file__).parents[1]
    config = tomllib.loads((root / ".codex/config.toml").read_text())
    server = config["mcp_servers"]["joern"]
    assert server["command"] == "joern-agent-mcp"
    assert server["required"] is True
    assert server["enabled"] is True
    assert config["features"]["hooks"] is True


def test_hook_schema_shape() -> None:
    root = Path(__file__).parents[1]
    hooks = json.loads((root / ".codex/hooks.json").read_text())
    assert set(hooks["hooks"]) == {"SessionStart", "Stop"}
    for event in hooks["hooks"].values():
        for group in event:
            assert isinstance(group["hooks"], list)
            assert all(handler["type"] == "command" for handler in group["hooks"])
            assert all(isinstance(handler["timeout"], int) for handler in group["hooks"])


def test_generated_databases_are_ignored() -> None:
    ignored = (Path(__file__).parents[1] / ".gitignore").read_text()
    for pattern in ("*.cpg", "cpg.bin", ".joern-agent/"):
        assert pattern in ignored
