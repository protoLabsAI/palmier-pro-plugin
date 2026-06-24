"""Host-free tests: registration, the warm-session bridge, the agent tools, and
manifest/pyproject coherence. No live editor and no `mcp` import required —
session I/O is exercised separately against a running editor."""

from __future__ import annotations

import asyncio
import json
import tomllib
import types
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


def _manifest() -> dict:
    return yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())


# ── registration ─────────────────────────────────────────────────────────────
def test_register_contributes_surface_tools_skill(plugin, make_registry):
    reg = make_registry({"connect": True})
    plugin.register(reg)
    assert [s["name"] for s in reg.surfaces] == ["palmier-pro-bridge"]
    assert sorted(t.name for t in reg.tools) == ["palmier", "palmier_status", "palmier_tools"]
    assert reg.skill_dirs == ["skills"]


# ── bridge ───────────────────────────────────────────────────────────────────
def test_bridge_defaults():
    from palmier_pro.bridge import DEFAULT_MCP_URL, EditorBridge

    b = EditorBridge({})
    assert b.url == DEFAULT_MCP_URL
    assert b.command == "npx"
    assert b.enabled is True


def test_bridge_disabled_call_errors():
    from palmier_pro.bridge import BridgeError, EditorBridge

    b = EditorBridge({"connect": False})
    with pytest.raises(BridgeError):
        asyncio.run(b.call("get_timeline", {}))


def test_bridge_not_started_call_errors():
    from palmier_pro.bridge import BridgeError, EditorBridge

    b = EditorBridge({"connect": True})  # enabled, but start() never called
    with pytest.raises(BridgeError):
        asyncio.run(b.call("get_timeline", {}))


def test_result_to_text():
    from palmier_pro.bridge import _result_to_text

    def block(**kw):
        return types.SimpleNamespace(**kw)

    ok = types.SimpleNamespace(
        content=[block(type="text", text="hello"), block(type="image")], isError=False
    )
    assert _result_to_text(ok) == "hello\n[image omitted]"

    err = types.SimpleNamespace(content=[block(type="text", text="bad input")], isError=True)
    assert _result_to_text(err) == "ERROR: bad input"


# ── tools ────────────────────────────────────────────────────────────────────
class _FakeBridge:
    url = "http://127.0.0.1:19789/mcp"
    connected = True
    instructions = ""

    def __init__(self, catalog=None, connected=True):
        self.tools_catalog = catalog if catalog is not None else []
        self.connected = connected

    async def call(self, name, arguments):
        return f"called {name} {arguments}"


def _tools(bridge):
    from palmier_pro.tools import build_tools

    return {t.name: t for t in build_tools(bridge)}


def test_palmier_routes_through_bridge():
    tools = _tools(_FakeBridge())
    out = asyncio.run(
        tools["palmier"].ainvoke({"tool_name": "get_timeline", "arguments": {"a": 1}})
    )
    assert out == "called get_timeline {'a': 1}"


def test_palmier_tools_catalog_and_single_schema():
    cat = [{"name": "add_clips", "description": "adds clips", "inputSchema": {"type": "object"}}]
    tools = _tools(_FakeBridge(catalog=cat))
    listing = json.loads(asyncio.run(tools["palmier_tools"].ainvoke({})))
    assert listing["connected"] is True
    assert listing["tools"] == [{"name": "add_clips", "description": "adds clips"}]
    one = json.loads(asyncio.run(tools["palmier_tools"].ainvoke({"tool_name": "add_clips"})))
    assert one["inputSchema"] == {"type": "object"}


def test_palmier_tools_when_offline():
    tools = _tools(_FakeBridge(catalog=[], connected=False))
    listing = json.loads(asyncio.run(tools["palmier_tools"].ainvoke({})))
    assert listing["connected"] is False
    assert listing["tools"] == []
    assert "note" in listing


def test_palmier_status():
    tools = _tools(_FakeBridge(catalog=[{"name": "x", "description": "", "inputSchema": {}}]))
    st = json.loads(asyncio.run(tools["palmier_status"].ainvoke({})))
    assert st["connected"] is True
    assert st["tool_count"] == 1
    assert st["url"].endswith("/mcp")


# ── manifest / packaging ─────────────────────────────────────────────────────
def test_manifest_required_fields():
    m = _manifest()
    for key in ("id", "name", "version", "description"):
        assert m.get(key), f"manifest missing {key}"
    assert m["enabled"] is False
    assert m["id"] == "palmier_pro"
    assert m["capabilities"]["network"] == ["127.0.0.1:19789"]


def test_manifest_version_matches_pyproject():
    m = _manifest()
    pp = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert m["version"] == pp["project"]["version"]
