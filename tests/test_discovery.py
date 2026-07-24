from __future__ import annotations

import shutil

import pytest

from joern_agent_bridge.discovery import discover
from joern_agent_bridge.errors import JoernUnavailable


def test_missing_joern_fails_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    discover.cache_clear()
    real_which = shutil.which

    def fake_which(name: str) -> str | None:
        if name.startswith("joern"):
            return None
        return real_which(name)

    monkeypatch.setattr("joern_agent_bridge.discovery.shutil.which", fake_which)
    with pytest.raises(JoernUnavailable) as error:
        discover()
    assert error.value.code == "joern_not_found"


def test_installation_is_user_accessible() -> None:
    discover.cache_clear()
    installation = discover()
    assert installation.joern.is_absolute()
    assert installation.parse.is_file()
    assert installation.export.is_file()
    assert installation.version.count(".") == 2
