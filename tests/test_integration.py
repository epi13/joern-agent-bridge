from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from joern_agent_bridge.models import Limits
from joern_agent_bridge.service import JoernService

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture(scope="module")
def real_service() -> JoernService:
    if not shutil.which("joern"):
        pytest.fail("Joern is required for real integration tests")
    root = Path(__file__).parents[1].resolve()
    return JoernService(roots=(root,))


@pytest.fixture(scope="module")
def fixture_path() -> Path:
    return Path(__file__).parents[1].joinpath("examples/c-demo").resolve()


def test_real_joern_graph_operations(real_service: JoernService, fixture_path: Path) -> None:
    manifest = real_service.parse(fixture_path, language="c", timeout=600, force=True)
    assert Path(manifest["cpg_path"]).is_file()
    limits = Limits(timeout=300, max_results=100, max_nodes=500, max_paths=10, max_depth=20)
    methods = real_service.query(fixture_path, "methods", limits=limits).data
    names = {item["name"] for item in methods}
    assert {"main", "process_request", "unsafe_sink", "validate_input"} <= names
    cfg = real_service.query(fixture_path, "cfg", limits=limits, method="process_request").data
    assert len(cfg) >= 10
    assignment = next(
        node
        for node in cfg
        if node.get("_label") == "CALL" and node.get("code") == "status = validate_input(input)"
    )
    neighbors = real_service.query(
        fixture_path,
        "neighbors",
        limits=limits,
        node_id=assignment["_id"],
        direction="both",
    ).data
    assert neighbors
    callers = real_service.query(
        fixture_path, "callers", limits=limits, method="process_request"
    ).data
    assert any(item["name"] == "main" for item in callers)
    callees = real_service.query(
        fixture_path, "callees", limits=limits, method="process_request"
    ).data
    assert {"validate_input", "checksum", "unsafe_sink"} <= {item["name"] for item in callees}
    controls = real_service.query(
        fixture_path, "control_dependencies", limits=limits, method="process_request"
    ).data
    assert controls
    assert real_service.query(
        fixture_path, "dominators", limits=limits, method="process_request"
    ).data
    assert real_service.query(
        fixture_path, "post_dominators", limits=limits, method="process_request"
    ).data
    assert real_service.query(fixture_path, "loops", limits=limits, method="checksum").data
    disconnected = real_service.query(
        fixture_path, "unreachable", limits=limits, method="process_request"
    ).data
    assert isinstance(disconnected, list)
    dataflow = real_service.query(
        fixture_path,
        "dataflow",
        limits=limits,
        source="process_request",
        sink="unsafe_sink",
    ).data
    assert dataflow
    call_paths = real_service.query(
        fixture_path,
        "call_paths",
        limits=limits,
        source="main",
        sink="unsafe_sink",
    ).data
    assert call_paths


def test_real_dot_export_and_graphviz(
    real_service: JoernService, fixture_path: Path, tmp_path: Path
) -> None:
    output = tmp_path / "cfg-export"
    export_service = JoernService(roots=(Path(__file__).parents[1].resolve(), tmp_path))
    result = export_service.export(fixture_path, output, representation="cfg", timeout=300)
    assert result["artifact_count"] > 0
    dot_file = next(output.glob("*.dot"))
    svg = tmp_path / "rendered.svg"
    subprocess.run(["/usr/bin/dot", "-Tsvg", str(dot_file), "-o", str(svg)], check=True)
    assert svg.read_text().startswith("<?xml")
