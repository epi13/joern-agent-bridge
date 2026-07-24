"""Shared typed result models."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Limits(StrictModel):
    timeout: float = Field(default=120.0, ge=1, le=1800)
    max_results: int = Field(default=100, ge=1, le=1000)
    max_nodes: int = Field(default=500, ge=1, le=5000)
    max_depth: int = Field(default=8, ge=1, le=50)
    max_paths: int = Field(default=20, ge=1, le=200)


class JoernError(StrictModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class QueryMetadata(StrictModel):
    operation: str
    joern_version: str
    cpg_path: str | None = None
    duration_ms: int
    limits: Limits
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AnalysisResult(StrictModel):
    ok: bool
    data: Any = None
    warnings: list[str] = Field(default_factory=list)
    error: JoernError | None = None
    metadata: QueryMetadata | None = None
    artifact_path: str | None = None


class ProcessResult(StrictModel):
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class CpgManifest(StrictModel):
    schema_version: int = 1
    source_root: str
    source_state: str
    joern_version: str
    language: str
    configuration_hash: str
    cpg_path: str
    created_at: str


class Snapshot(StrictModel):
    schema_version: int = 1
    status: Literal["complete", "failed"]
    repository_commit: str
    working_tree_hash: str
    relevant_diff_hash: str
    joern_version: str
    language: str
    source_root: str
    query_definitions: list[str]
    analyzed_methods: list[dict[str, Any]]
    method_cfg_summaries: list[dict[str, Any]]
    call_relationships: list[dict[str, Any]]
    control_dependencies: list[dict[str, Any]]
    warnings: list[str]
    timeout_seconds: float
    timestamp: str
    phase: Literal["baseline", "post"]


class PathPolicy(StrictModel):
    approved_roots: tuple[Path, ...]
