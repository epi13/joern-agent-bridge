"""Standards-compliant local STDIO MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .models import Limits
from .paths import resolve_confined
from .service import JoernService
from .snapshot import compare_snapshots, create_snapshot, load_snapshot

mcp = FastMCP(
    "joern",
    instructions=(
        "Bounded, source-evidenced Joern CPG analysis. All project and output paths "
        "must remain beneath the server's launch directory. Prefer focused method-level "
        "queries and explicit limits; large graph exports are written to artifact files."
    ),
)


def _limits(
    timeout: float,
    max_results: int,
    max_nodes: int,
    max_depth: int,
    max_paths: int,
) -> Limits:
    return Limits(
        timeout=timeout,
        max_results=max_results,
        max_nodes=max_nodes,
        max_depth=max_depth,
        max_paths=max_paths,
    )


def _service() -> JoernService:
    return JoernService()


def _query(
    project: str,
    operation: str,
    *,
    language: str = "c",
    timeout: float = 120,
    max_results: int = 100,
    max_nodes: int = 500,
    max_depth: int = 8,
    max_paths: int = 20,
    **parameters: Any,
) -> dict[str, Any]:
    result = _service().query(
        project,
        operation,
        language=language,
        limits=_limits(timeout, max_results, max_nodes, max_depth, max_paths),
        **parameters,
    )
    return result.model_dump(mode="json")


@mcp.tool()
def joern_health() -> dict[str, Any]:
    """Use before analysis to verify real Joern executables, version, languages, approved roots, and STDIO mode. Cost: low; no CPG is built. Failures usually mean Joern or this package is absent from PATH."""
    return _service().health()


@mcp.tool()
def joern_supported_languages() -> dict[str, Any]:
    """Discover language frontends in the installed Joern distribution. Cost: low. Results are installation-specific and may differ from upstream documentation."""
    service = _service()
    return {
        "joern_version": service.installation.version,
        "languages": service.health()["supported_languages"],
    }


@mcp.tool()
def joern_parse_project(
    project: str,
    language: str = "c",
    force: bool = False,
    timeout: float = 600,
) -> dict[str, Any]:
    """Create or refresh a content-addressed CPG. `project` must be an existing directory beneath an approved root; symlink escapes are rejected. Cost: high and serialized per CPG. Returns cache/source/version metadata; failures include unsupported language, timeout, and frontend errors."""
    return _service().parse(project, language=language, force=force, timeout=timeout)


@mcp.tool()
def joern_list_methods(
    project: str,
    language: str = "c",
    max_results: int = 100,
    timeout: float = 120,
) -> dict[str, Any]:
    """List bounded real CPG method nodes with source-location properties. Use to identify method names before focused queries. `project` is confined to approved roots. Cost: medium after parsing; common failures are stale/invalid source and parse timeout."""
    return _query(project, "methods", language=language, max_results=max_results, timeout=timeout)


@mcp.tool()
def joern_search_methods(
    project: str,
    exact_name: str = "",
    regex: str = "",
    language: str = "c",
    max_results: int = 100,
    timeout: float = 120,
) -> dict[str, Any]:
    """Search methods by exact name or Joern regex. Prefer exact names; regex is evaluated by Joern and invalid expressions fail. Returns bounded method nodes with file/line evidence. Cost: medium."""
    return _query(
        project,
        "search_methods",
        language=language,
        method=exact_name,
        pattern=regex,
        max_results=max_results,
        timeout=timeout,
    )


@mcp.tool()
def joern_get_method_cfg(
    project: str,
    method: str,
    language: str = "c",
    max_nodes: int = 500,
    timeout: float = 120,
) -> dict[str, Any]:
    """Retrieve bounded CFG nodes for an exact method name, including Joern node IDs and source properties. Use for branches, loops, exits, and cleanup review. Cost: medium; overloaded names may produce multiple CFGs."""
    return _query(
        project, "cfg", method=method, language=language, max_nodes=max_nodes, timeout=timeout
    )


@mcp.tool()
def joern_get_cfg_neighbors(
    project: str,
    node_id: int,
    direction: str = "both",
    language: str = "c",
    max_nodes: int = 100,
    timeout: float = 120,
) -> dict[str, Any]:
    """Return CFG predecessors (`in`), successors (`out`), or both for a Joern node ID from a prior result. Cost: medium. Invalid/stale node IDs return no nodes; direction must be in/out/both."""
    return _query(
        project,
        "neighbors",
        node_id=node_id,
        direction=direction,
        language=language,
        max_nodes=max_nodes,
        timeout=timeout,
    )


def _method_relation(
    project: str,
    operation: str,
    method: str,
    language: str,
    max_results: int,
    timeout: float,
) -> dict[str, Any]:
    return _query(
        project,
        operation,
        method=method,
        language=language,
        max_results=max_results,
        timeout=timeout,
    )


@mcp.tool()
def joern_get_callers(
    project: str,
    method: str,
    language: str = "c",
    max_results: int = 100,
    timeout: float = 120,
) -> dict[str, Any]:
    """Retrieve bounded caller method nodes for an exact callee name with source evidence. Use for impact analysis. Cost: medium; unresolved dynamic calls may be absent."""
    return _method_relation(project, "callers", method, language, max_results, timeout)


@mcp.tool()
def joern_get_callees(
    project: str,
    method: str,
    language: str = "c",
    max_results: int = 100,
    timeout: float = 120,
) -> dict[str, Any]:
    """Retrieve bounded callee method nodes for an exact caller name with source evidence. Use for impact and side-effect analysis. Cost: medium; unresolved dynamic calls may be absent."""
    return _method_relation(project, "callees", method, language, max_results, timeout)


@mcp.tool()
def joern_get_control_dependencies(
    project: str,
    method: str,
    language: str = "c",
    max_nodes: int = 500,
    timeout: float = 120,
) -> dict[str, Any]:
    """Retrieve bounded controlling conditions for CFG nodes in an exact method. Use for branch/error/auth/input-validation analysis. Returns Joern source-located nodes. Cost: medium."""
    return _query(
        project,
        "control_dependencies",
        method=method,
        language=language,
        max_nodes=max_nodes,
        timeout=timeout,
    )


@mcp.tool()
def joern_get_dominators(
    project: str,
    method: str,
    language: str = "c",
    max_nodes: int = 500,
    timeout: float = 120,
) -> dict[str, Any]:
    """Retrieve bounded dominator evidence for an exact method. Use to prove that checks/actions occur on every path before a node. Cost: medium; incomplete frontend CFGs must be disclosed."""
    return _query(
        project,
        "dominators",
        method=method,
        language=language,
        max_nodes=max_nodes,
        timeout=timeout,
    )


@mcp.tool()
def joern_get_post_dominators(
    project: str,
    method: str,
    language: str = "c",
    max_nodes: int = 500,
    timeout: float = 120,
) -> dict[str, Any]:
    """Retrieve bounded post-dominator evidence for an exact method. Use for cleanup and must-eventually-execute reasoning. Cost: medium; exceptional/incomplete CFG edges may affect results."""
    return _query(
        project,
        "post_dominators",
        method=method,
        language=language,
        max_nodes=max_nodes,
        timeout=timeout,
    )


@mcp.tool()
def joern_find_loops(
    project: str,
    method: str,
    language: str = "c",
    max_results: int = 100,
    timeout: float = 120,
) -> dict[str, Any]:
    """Identify bounded source-located loop control structures in an exact method. Use for loop-sensitive edits and potential cyclic CFG regions. Cost: medium; irreducible cycles not represented as source loop constructs may require exported CFG analysis."""
    return _query(
        project,
        "loops",
        method=method,
        language=language,
        max_results=max_results,
        timeout=timeout,
    )


@mcp.tool()
def joern_find_unreachable_nodes(
    project: str,
    method: str,
    language: str = "c",
    max_nodes: int = 500,
    timeout: float = 120,
) -> dict[str, Any]:
    """Return method CFG nodes not reachable from Joern's first CFG node within the explicit node/depth safety bound. Cost: medium. Treat results as potential unreachable evidence when exceptional or frontend edges are incomplete."""
    return _query(
        project,
        "unreachable",
        method=method,
        language=language,
        max_nodes=max_nodes,
        max_depth=max_nodes,
        timeout=timeout,
    )


@mcp.tool()
def joern_find_call_paths(
    project: str,
    source_method: str,
    sink_method: str,
    language: str = "c",
    max_depth: int = 8,
    max_paths: int = 20,
    timeout: float = 180,
) -> dict[str, Any]:
    """Find bounded call-graph paths from exact source to sink method names. Always keep depth/path bounds small. Cost: high; missing paths do not prove absence when calls are unresolved."""
    return _query(
        project,
        "call_paths",
        source=source_method,
        sink=sink_method,
        language=language,
        max_depth=max_depth,
        max_paths=max_paths,
        timeout=timeout,
    )


@mcp.tool()
def joern_find_dataflow_paths(
    project: str,
    source_method_regex: str,
    sink_call_regex: str,
    language: str = "c",
    max_depth: int = 20,
    max_paths: int = 20,
    timeout: float = 300,
) -> dict[str, Any]:
    """Run a bounded real Joern source-to-sink data-flow query from method parameters to sink call arguments. Cost: very high. Regexes must be focused; frontend/type/semantic gaps can cause false positives or negatives."""
    return _query(
        project,
        "dataflow",
        source=source_method_regex,
        sink=sink_call_regex,
        language=language,
        max_depth=max_depth,
        max_paths=max_paths,
        timeout=timeout,
    )


@mcp.tool()
def joern_export_graph(
    project: str,
    output_directory: str,
    representation: str = "cfg",
    language: str = "c",
    timeout: float = 300,
) -> dict[str, Any]:
    """Export a Joern graph representation (`ast`, `cfg`, `cdg`, `ddg`, `pdg`, `cpg`, or `all`) to an approved artifact directory. Cost: high and potentially large; returns only a concise manifest and paths, never the whole graph."""
    return _service().export(
        project,
        output_directory,
        representation=representation,
        language=language,
        timeout=timeout,
    )


@mcp.tool()
def joern_create_snapshot(
    project: str,
    output_file: str,
    phase: str = "post",
    language: str = "c",
    timeout: float = 300,
) -> dict[str, Any]:
    """Create a bounded graph-analysis snapshot containing source/diff hashes, methods, CFG summaries, calls, controls, Joern version, warnings, and status. Paths are confined. Cost: high; phase must be baseline or post."""
    service = _service()
    project_path = Path(project).resolve()
    output_path = resolve_confined(output_file, service.roots, must_exist=False)
    snapshot = create_snapshot(
        service,
        project_path,
        output_path,
        phase=phase,
        language=language,
        timeout=timeout,
    )
    return snapshot.model_dump(mode="json")


@mcp.tool()
def joern_compare_snapshots(before_file: str, after_file: str) -> dict[str, Any]:
    """Compare two trusted snapshot JSON files for method and CFG-summary changes. Cost: low; malformed or schema-incompatible snapshots fail explicitly."""
    service = _service()
    before = resolve_confined(before_file, service.roots, expect="file")
    after = resolve_confined(after_file, service.roots, expect="file")
    return compare_snapshots(load_snapshot(before), load_snapshot(after))


def main() -> None:
    """Run only the local STDIO transport; no network listener is opened."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
