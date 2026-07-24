"""Structured Joern script execution."""

from __future__ import annotations

import json
import time
from importlib.resources import files
from pathlib import Path
from typing import Any

from .discovery import JoernInstallation
from .errors import JoernExecutionError
from .models import AnalysisResult, JoernError, Limits, QueryMetadata
from .process import run_process

_MARKER = "JOERN_AGENT_RESULT:"
_ALLOWED = {
    "methods",
    "search_methods",
    "cfg",
    "neighbors",
    "callers",
    "callees",
    "control_dependencies",
    "dominators",
    "post_dominators",
    "loops",
    "unreachable",
    "call_paths",
    "dataflow",
    "summary",
    "snapshot",
}


class QueryRunner:
    def __init__(
        self,
        installation: JoernInstallation,
        script: Path | None = None,
    ) -> None:
        self.installation = installation
        self.script = script or Path(str(files("joern_agent_bridge").joinpath("joern/query.sc")))

    def run(
        self,
        cpg_path: Path,
        operation: str,
        *,
        limits: Limits | None = None,
        method: str = "",
        pattern: str = "",
        node_id: int = 0,
        direction: str = "both",
        source: str = "",
        sink: str = "",
    ) -> AnalysisResult:
        selected_limits = limits or Limits()
        if operation not in _ALLOWED:
            raise ValueError(f"Unsupported operation: {operation}")
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be in, out, or both")
        started = time.monotonic()
        argv: list[str | Path] = [
            self.installation.joern,
            "--script",
            self.script,
            "--param",
            f"cpgFile={cpg_path}",
            "--param",
            f"operation={operation}",
            "--param",
            f"method={method}",
            "--param",
            f"pattern={pattern}",
            "--param",
            f"nodeId={node_id}",
            "--param",
            f"direction={direction}",
            "--param",
            f"source={source}",
            "--param",
            f"sink={sink}",
            "--param",
            f"maxResults={selected_limits.max_results}",
            "--param",
            f"maxNodes={selected_limits.max_nodes}",
            "--param",
            f"maxDepth={selected_limits.max_depth}",
            "--param",
            f"maxPaths={selected_limits.max_paths}",
        ]
        result = run_process(
            argv,
            cwd=cpg_path.parent,
            timeout=selected_limits.timeout,
        )
        metadata = QueryMetadata(
            operation=operation,
            joern_version=self.installation.version,
            cpg_path=str(cpg_path),
            duration_ms=round((time.monotonic() - started) * 1000),
            limits=selected_limits,
        )
        if result.returncode != 0:
            raise JoernExecutionError(
                "joern_query_failed",
                f"Joern query failed: {operation}",
                details={
                    "returncode": result.returncode,
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                },
            )
        lines = [line for line in result.stdout.splitlines() if line.startswith(_MARKER)]
        if len(lines) != 1:
            raise JoernExecutionError(
                "malformed_joern_output",
                "Joern did not emit exactly one structured result",
                details={"marker_count": len(lines), "stderr": result.stderr},
            )
        try:
            payload: Any = json.loads(lines[0][len(_MARKER) :])
        except json.JSONDecodeError as exc:
            raise JoernExecutionError(
                "malformed_joern_json",
                "Joern emitted invalid JSON",
                details={"error": str(exc)},
            ) from exc
        warnings: list[str] = []
        if result.stdout_truncated or result.stderr_truncated:
            warnings.append("Joern process output was truncated")
        return AnalysisResult(ok=True, data=payload, warnings=warnings, metadata=metadata)


def error_result(exc: Exception) -> AnalysisResult:
    if isinstance(exc, JoernExecutionError):
        error = JoernError(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
        )
    else:
        error = JoernError(code="internal_error", message=str(exc))
    return AnalysisResult(ok=False, error=error)
