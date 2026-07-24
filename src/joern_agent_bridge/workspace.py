"""Content-addressed CPG cache and write serialization."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from filelock import FileLock
from platformdirs import user_cache_path

from .discovery import JoernInstallation
from .errors import BridgeError, JoernExecutionError
from .models import CpgManifest
from .process import run_process

_SOURCE_SUFFIXES = {
    "c": {".c", ".h"},
    "c++": {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"},
    "java": {".java", ".jar", ".class"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"},
    "python": {".py"},
    "kotlin": {".kt", ".kts"},
    "php": {".php"},
}
_FRONTEND_ALIASES = {
    "c": "c",
    "c++": "c",
    "java": "javasrc",
    "javascript": "jssrc",
    "python": "pythonsrc",
    "kotlin": "kotlin",
    "php": "php",
}
_EXCLUDED_DIRECTORIES = {
    ".git",
    ".joern-agent",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


def hash_bytes(*values: bytes) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def source_state(source_root: Path, language: str) -> str:
    suffixes = _SOURCE_SUFFIXES.get(language)
    if not suffixes:
        raise BridgeError(
            "unsupported_language",
            f"Unsupported language: {language}",
            details={"supported": sorted(_SOURCE_SUFFIXES)},
        )
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and not _EXCLUDED_DIRECTORIES.intersection(path.relative_to(source_root).parts)
    )
    if not files:
        raise BridgeError(
            "no_source_files",
            f"No {language} source files found",
            details={"source_root": str(source_root)},
        )
    for path in files:
        relative = path.relative_to(source_root).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


class CpgWorkspace:
    def __init__(self, cache_root: Path | None = None) -> None:
        root = cache_root or user_cache_path("joern-agent-bridge")
        self.root = root.expanduser().resolve(strict=False)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _key(
        self,
        source_root: Path,
        state: str,
        installation: JoernInstallation,
        language: str,
        configuration_hash: str,
    ) -> str:
        return hash_bytes(
            str(source_root).encode(),
            state.encode(),
            installation.version.encode(),
            language.encode(),
            configuration_hash.encode(),
        )

    def ensure(
        self,
        source_root: Path,
        installation: JoernInstallation,
        *,
        language: str,
        timeout: float,
        force: bool = False,
        configuration: dict[str, object] | None = None,
    ) -> CpgManifest:
        configuration_json = json.dumps(configuration or {}, sort_keys=True, separators=(",", ":"))
        configuration_hash = hashlib.sha256(configuration_json.encode()).hexdigest()
        state = source_state(source_root, language)
        key = self._key(source_root, state, installation, language, configuration_hash)
        cache_dir = self.root / key
        cpg_path = cache_dir / "cpg.bin"
        manifest_path = cache_dir / "manifest.json"
        lock = FileLock(str(self.root / f"{key}.lock"), timeout=max(timeout, 1))
        with lock:
            if not force and cpg_path.is_file() and manifest_path.is_file():
                try:
                    manifest = CpgManifest.model_validate_json(manifest_path.read_text())
                except (ValueError, OSError):
                    manifest = None
                if (
                    manifest
                    and manifest.source_state == state
                    and manifest.joern_version == installation.version
                    and manifest.language == language
                ):
                    return manifest

            cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = cache_dir / f"cpg.bin.tmp-{os.getpid()}"
            temporary.unlink(missing_ok=True)
            argv: list[str | Path] = [
                installation.parse,
                "--language",
                _FRONTEND_ALIASES[language],
                "--output",
                temporary,
                source_root,
            ]
            result = run_process(argv, cwd=cache_dir, timeout=timeout)
            if result.returncode != 0 or not temporary.is_file():
                temporary.unlink(missing_ok=True)
                raise JoernExecutionError(
                    "joern_parse_failed",
                    "Joern failed to create a CPG",
                    details={
                        "returncode": result.returncode,
                        "stderr": result.stderr,
                        "stdout": result.stdout,
                    },
                )
            temporary.replace(cpg_path)
            manifest = CpgManifest(
                source_root=str(source_root),
                source_state=state,
                joern_version=installation.version,
                language=language,
                configuration_hash=configuration_hash,
                cpg_path=str(cpg_path),
                created_at=datetime.now(UTC).isoformat(),
            )
            manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
            return manifest
