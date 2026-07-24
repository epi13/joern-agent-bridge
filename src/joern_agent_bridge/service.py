"""Application service shared by CLI and MCP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .discovery import JoernInstallation, discover, supported_languages
from .errors import JoernExecutionError
from .models import AnalysisResult, Limits
from .paths import approved_roots, resolve_confined
from .query import QueryRunner
from .workspace import CpgWorkspace


class JoernService:
    def __init__(
        self,
        *,
        roots: tuple[Path, ...] | None = None,
        cache_root: Path | None = None,
        installation: JoernInstallation | None = None,
    ) -> None:
        self.roots = roots or approved_roots()
        self.installation = installation or discover()
        self.workspace = CpgWorkspace(cache_root)
        self.queries = QueryRunner(self.installation)

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "joern_version": self.installation.version,
            "executables": {
                "joern": str(self.installation.joern),
                "joern_parse": str(self.installation.parse),
                "joern_export": str(self.installation.export),
            },
            "supported_languages": supported_languages(self.installation),
            "approved_roots": [str(item) for item in self.roots],
            "transport": "stdio",
        }

    def parse(
        self,
        project: str | Path,
        *,
        language: str = "c",
        timeout: float = 600,
        force: bool = False,
    ) -> dict[str, Any]:
        source_root = resolve_confined(project, self.roots, expect="dir")
        manifest = self.workspace.ensure(
            source_root,
            self.installation,
            language=language,
            timeout=timeout,
            force=force,
        )
        return manifest.model_dump(mode="json")

    def query(
        self,
        project: str | Path,
        operation: str,
        *,
        language: str = "c",
        limits: Limits | None = None,
        force: bool = False,
        **parameters: Any,
    ) -> AnalysisResult:
        selected_limits = limits or Limits()
        source_root = resolve_confined(project, self.roots, expect="dir")
        manifest = self.workspace.ensure(
            source_root,
            self.installation,
            language=language,
            timeout=max(selected_limits.timeout, 60),
            force=force,
        )
        return self.queries.run(
            Path(manifest.cpg_path),
            operation,
            limits=selected_limits,
            **parameters,
        )

    def export(
        self,
        project: str | Path,
        output: str | Path,
        *,
        representation: str = "cfg",
        language: str = "c",
        timeout: float = 300,
    ) -> dict[str, Any]:
        from .process import run_process

        source_root = resolve_confined(project, self.roots, expect="dir")
        output_path = resolve_confined(output, self.roots, must_exist=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            raise FileExistsError(f"Export directory must not already exist: {output_path}")
        manifest = self.workspace.ensure(
            source_root,
            self.installation,
            language=language,
            timeout=timeout,
        )
        allowed = {"ast", "cfg", "cdg", "ddg", "pdg", "cpg", "all"}
        if representation not in allowed:
            raise ValueError(f"representation must be one of: {sorted(allowed)}")
        result = run_process(
            [
                self.installation.export,
                "--repr",
                representation,
                "--out",
                output_path,
                Path(manifest.cpg_path),
            ],
            cwd=output_path.parent,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise JoernExecutionError(
                "joern_export_failed",
                "Joern graph export failed",
                details={
                    "returncode": result.returncode,
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                },
            )
        artifacts = sorted(str(path) for path in output_path.rglob("*") if path.is_file())
        summary = {
            "ok": True,
            "representation": representation,
            "artifact_count": len(artifacts),
            "output": str(output_path),
            "artifacts": artifacts[:20],
            "truncated": len(artifacts) > 20,
        }
        (output_path / "export-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        return summary
