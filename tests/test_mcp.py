from __future__ import annotations

import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.integration


def test_mcp_initialize_list_and_real_tool_call() -> None:
    root = Path(__file__).parents[1].resolve()

    async def scenario() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "joern_agent_bridge.mcp_server"],
            cwd=root,
        )
        async with (
            stdio_client(parameters) as (read, write),
            ClientSession(read, write) as session,
        ):
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "joern"
            listing = await session.list_tools()
            names = {tool.name for tool in listing.tools}
            assert {
                "joern_health",
                "joern_parse_project",
                "joern_get_method_cfg",
                "joern_find_dataflow_paths",
            } <= names
            health = await session.call_tool("joern_health")
            assert not health.isError
            methods = await session.call_tool(
                "joern_list_methods",
                {"project": "examples/c-demo", "language": "c", "max_results": 20},
            )
            assert not methods.isError
            assert "process_request" in str(methods.content)

    anyio.run(scenario)
