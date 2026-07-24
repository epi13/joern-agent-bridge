"""Human-facing command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer

from .errors import BridgeError
from .models import Limits
from .paths import resolve_confined
from .service import JoernService
from .snapshot import (
    compare_snapshots,
    create_snapshot,
    load_snapshot,
    write_validation_record,
)

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def _print(value: Any, as_json: bool) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if as_json:
        typer.echo(json.dumps(value, indent=2, sort_keys=True))
    elif isinstance(value, dict):
        for key, item in value.items():
            typer.echo(f"{key}: {item}")
    elif isinstance(value, list):
        for item in value:
            typer.echo(json.dumps(item, sort_keys=True))
    else:
        typer.echo(str(value))


def _service(project: Path) -> JoernService:
    project_root = project.resolve(strict=True)
    current_root = Path.cwd().resolve(strict=True)
    roots = (current_root,) if project_root == current_root else (current_root, project_root)
    return JoernService(roots=roots)


def _query(
    operation: str,
    project: Path,
    *,
    language: str,
    timeout: float,
    max_results: int,
    max_nodes: int,
    max_depth: int,
    max_paths: int,
    as_json: bool,
    **parameters: Any,
) -> None:
    limits = Limits(
        timeout=timeout,
        max_results=max_results,
        max_nodes=max_nodes,
        max_depth=max_depth,
        max_paths=max_paths,
    )
    result = _service(project).query(
        project, operation, language=language, limits=limits, **parameters
    )
    _print(result, as_json)
    if not result.ok:
        raise typer.Exit(2)


@app.command()
def doctor(
    project: Path = typer.Argument(Path(".")),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _print(_service(project).health(), json_output)


@app.command()
def parse(
    project: Path = typer.Argument(Path(".")),
    language: str = "c",
    timeout: float = 600,
    force: bool = False,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _print(
        _service(project).parse(project, language=language, timeout=timeout, force=force),
        json_output,
    )


def _common_query(
    operation: str,
    project: Path,
    language: str,
    method: str,
    pattern: str,
    node_id: int,
    direction: str,
    source: str,
    sink: str,
    timeout: float,
    max_results: int,
    max_nodes: int,
    max_depth: int,
    max_paths: int,
    json_output: bool,
) -> None:
    _query(
        operation,
        project,
        language=language,
        timeout=timeout,
        max_results=max_results,
        max_nodes=max_nodes,
        max_depth=max_depth,
        max_paths=max_paths,
        as_json=json_output,
        method=method,
        pattern=pattern,
        node_id=node_id,
        direction=direction,
        source=source,
        sink=sink,
    )


def _register_query(name: str, operation: str) -> None:
    def command(
        project: Path = typer.Argument(Path(".")),
        method: str = "",
        pattern: str = "",
        node_id: int = 0,
        direction: str = "both",
        source: str = "",
        sink: str = "",
        language: str = "c",
        timeout: float = 120,
        max_results: int = 100,
        max_nodes: int = 500,
        max_depth: int = 8,
        max_paths: int = 20,
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        _common_query(
            operation,
            project,
            language,
            method,
            pattern,
            node_id,
            direction,
            source,
            sink,
            timeout,
            max_results,
            max_nodes,
            max_depth,
            max_paths,
            json_output,
        )

    command.__name__ = name.replace("-", "_")
    app.command(name)(command)


for _name, _operation in {
    "methods": "methods",
    "search-methods": "search_methods",
    "cfg": "cfg",
    "neighbors": "neighbors",
    "callers": "callers",
    "callees": "callees",
    "controls": "control_dependencies",
    "dominators": "dominators",
    "post-dominators": "post_dominators",
    "loops": "loops",
    "unreachable": "unreachable",
    "call-paths": "call_paths",
    "dataflow": "dataflow",
}.items():
    _register_query(_name, _operation)


@app.command("export")
def export_command(
    project: Path = typer.Argument(Path(".")),
    output: Path = Path(".joern-agent/exports"),
    representation: str = "cfg",
    language: str = "c",
    timeout: float = 300,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _print(
        _service(project).export(
            project, output, representation=representation, language=language, timeout=timeout
        ),
        json_output,
    )


@app.command()
def snapshot(
    project: Path = typer.Argument(Path(".")),
    output: Path = Path(".joern-agent/snapshot.json"),
    phase: str = "post",
    language: str = "c",
    timeout: float = 300,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    service = _service(project)
    output_path = resolve_confined(output, service.roots, must_exist=False)
    _print(
        create_snapshot(
            service,
            project.resolve(),
            output_path,
            phase=phase,
            language=language,
            timeout=timeout,
        ),
        json_output,
    )


@app.command()
def compare(
    before: Path = typer.Argument(...),
    after: Path = typer.Argument(...),
    output: Path | None = None,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    roots = (Path.cwd().resolve(strict=True),)
    before = resolve_confined(before, roots, expect="file")
    after = resolve_confined(after, roots, expect="file")
    result = compare_snapshots(load_snapshot(before), load_snapshot(after))
    if output:
        output = resolve_confined(output, roots, must_exist=False)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _print(result, json_output)


@app.command()
def validate(
    project: Path = typer.Argument(Path(".")),
    baseline: Path = Path(".joern-agent/baseline.json"),
    post: Path = Path(".joern-agent/post.json"),
    language: str = "c",
    timeout: float = 300,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    service = _service(project)
    project = project.resolve()
    baseline = resolve_confined(baseline, service.roots, must_exist=False)
    post = resolve_confined(post, service.roots, must_exist=False)
    if not baseline.is_file():
        create_snapshot(
            service,
            project,
            baseline.resolve(),
            phase="baseline",
            language=language,
            timeout=timeout,
        )
    after = create_snapshot(
        service, project, post.resolve(), phase="post", language=language, timeout=timeout
    )
    before = load_snapshot(baseline.resolve())
    comparison = compare_snapshots(before, after)
    record = write_validation_record(project, before, after, comparison)
    _print({"ok": True, "record": str(record), "comparison": comparison}, json_output)


@app.command()
def mcp() -> None:
    from .mcp_server import main as mcp_main

    mcp_main()


def main() -> None:
    try:
        app()
    except BridgeError as exc:
        payload = {
            "ok": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "retryable": exc.retryable,
            },
        }
        if "--json" in sys.argv:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        else:
            typer.echo(f"{exc.code}: {exc.message}", err=True)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
