"""The agent-facing tools. They route through the warm EditorBridge session, so
the model drives the editor without a per-call subprocess respawn.

Generic dispatch (palmier / palmier_tools / palmier_status) keeps the catalog
live and never-stale: tool schemas are fetched from the running editor rather
than baked into this repo, and the tools exist even when the editor is offline
(they return a clear "not connected" instead of vanishing).
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool

from .bridge import BridgeError, EditorBridge


def build_tools(bridge: EditorBridge) -> list:
    async def palmier(tool_name: str, arguments: dict | None = None) -> str:
        """Invoke a Palmier Pro editor tool over the live MCP session and return its
        result. `tool_name` is an editor tool (e.g. "get_timeline", "add_clips",
        "import_media"); `arguments` is that tool's input object. Call `palmier_tools`
        first to see the available tools and their schemas."""
        try:
            return await bridge.call(tool_name, arguments or {})
        except BridgeError as e:
            return f"ERROR: {e}"

    async def palmier_tools(tool_name: str | None = None) -> str:
        """List the Palmier Pro editor's tools. With no argument, returns the catalog
        (each tool's name + description) plus connection state. Pass `tool_name` to get
        that one tool's full JSON input schema before calling it via `palmier`."""
        cat = bridge.tools_catalog
        if tool_name:
            for t in cat:
                if t["name"] == tool_name:
                    return json.dumps(t)
            return json.dumps(
                {"error": f"unknown tool {tool_name!r}", "connected": bridge.connected}
            )
        if not cat:
            return json.dumps(
                {
                    "connected": bridge.connected,
                    "tools": [],
                    "note": "Editor not connected — launch Palmier Pro, open a project, and ensure "
                    "the MCP server is on (Settings ▸ Agent ▸ MCP Server).",
                }
            )
        return json.dumps(
            {
                "connected": True,
                "tools": [{"name": t["name"], "description": t["description"]} for t in cat],
            }
        )

    async def palmier_status() -> str:
        """Report the Palmier Pro connection: whether the editor is reachable, how many
        tools it exposes, and the endpoint in use."""
        return json.dumps(
            {
                "connected": bridge.connected,
                "tool_count": len(bridge.tools_catalog),
                "url": bridge.url,
            }
        )

    return [
        StructuredTool.from_function(
            coroutine=palmier, name="palmier", description=palmier.__doc__
        ),
        StructuredTool.from_function(
            coroutine=palmier_tools, name="palmier_tools", description=palmier_tools.__doc__
        ),
        StructuredTool.from_function(
            coroutine=palmier_status, name="palmier_status", description=palmier_status.__doc__
        ),
    ]
