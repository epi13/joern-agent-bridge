"""Joern executable, version, and frontend discovery."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .errors import JoernUnavailable
from .process import run_process

_VERSION = re.compile(r"(?:Version:\s*|v?)(\d+\.\d+\.\d+)")


@dataclass(frozen=True)
class JoernInstallation:
    joern: Path
    parse: Path
    export: Path
    scan: Path | None
    version: str


def _executable(name: str) -> Path:
    located = shutil.which(name)
    if not located:
        raise JoernUnavailable(
            "joern_not_found",
            f"Required executable is not on PATH: {name}",
            details={"executable": name},
        )
    return Path(located).resolve(strict=True)


@lru_cache(maxsize=1)
def discover() -> JoernInstallation:
    joern = _executable("joern")
    parser = _executable("joern-parse")
    exporter = _executable("joern-export")
    scan_value = shutil.which("joern-scan")
    scan = Path(scan_value).resolve(strict=True) if scan_value else None
    result = run_process([joern, "--version"], cwd=Path.cwd(), timeout=30)
    combined = f"{result.stdout}\n{result.stderr}"
    match = _VERSION.search(combined)
    if not match:
        raise JoernUnavailable(
            "joern_version_unknown",
            "Joern is installed but its version could not be determined",
            details={"returncode": result.returncode},
        )
    return JoernInstallation(joern, parser, exporter, scan, match.group(1))


def supported_languages(installation: JoernInstallation) -> list[str]:
    if installation.scan:
        result = run_process(
            [installation.scan, "--list-languages"],
            cwd=Path.cwd(),
            timeout=60,
        )
        if result.returncode == 0:
            values = [
                line.strip().lstrip("- ").lower()
                for line in result.stdout.splitlines()
                if line.strip().startswith("- ")
            ]
            if values:
                return sorted(set(values))
    frontends = {
        "c": "c2cpg.sh",
        "c++": "c2cpg.sh",
        "java": "javasrc2cpg",
        "javascript": "jssrc2cpg.sh",
        "jvm-bytecode": "jimple2cpg",
        "kotlin": "kotlin2cpg",
        "php": "php2cpg",
        "python": "pysrc2cpg",
        "x86/x64": "ghidra2cpg",
    }
    return sorted(
        language for language, executable in frontends.items() if shutil.which(executable)
    )
