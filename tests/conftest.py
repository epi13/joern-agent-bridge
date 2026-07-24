from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["/usr/bin/git", "init", "-b", "main", str(tmp_path)], check=True)
    subprocess.run(
        ["/usr/bin/git", "-C", str(tmp_path), "config", "user.name", "Test User"], check=True
    )
    subprocess.run(
        ["/usr/bin/git", "-C", str(tmp_path), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    (tmp_path / "main.c").write_text("int main(void) { return 0; }\n")
    (tmp_path / "README.md").write_text("# Test\n")
    subprocess.run(["/usr/bin/git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["/usr/bin/git", "-C", str(tmp_path), "commit", "-m", "initial"], check=True)
    return tmp_path
