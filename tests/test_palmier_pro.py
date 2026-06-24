"""Host-free tests for the palmier_pro plugin: registration, the MCP factory, and
manifest/pyproject coherence."""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _manifest() -> dict:
    return yaml.safe_load((ROOT / "protoagent.plugin.yaml").read_text())


def test_register_contributes_mcp_and_skill(plugin, make_registry):
    reg = make_registry({"mcp_url": "http://127.0.0.1:19789/mcp", "connect": True})
    plugin.register(reg)
    assert len(reg.mcp_servers) == 1
    assert reg.skill_dirs == ["skills"]
    assert reg.tools == []  # the editor's tools come over MCP, not from this plugin


def test_factory_returns_streamable_http_entry(plugin, make_registry):
    reg = make_registry({"mcp_url": "http://127.0.0.1:19789/mcp", "connect": True})
    plugin.register(reg)
    # The host calls the factory with the live LangGraphConfig; we don't use it.
    entry = reg.mcp_servers[0](None)
    assert entry == {
        "name": "palmier-pro",
        "transport": "streamable_http",
        "url": "http://127.0.0.1:19789/mcp",
    }


def test_factory_off_when_not_connected(plugin, make_registry):
    reg = make_registry({"connect": False})
    plugin.register(reg)
    assert reg.mcp_servers[0](None) is None


def test_factory_honors_custom_url(plugin, make_registry):
    reg = make_registry({"mcp_url": "http://127.0.0.1:5000/mcp", "connect": True})
    plugin.register(reg)
    assert reg.mcp_servers[0](None)["url"] == "http://127.0.0.1:5000/mcp"


def test_factory_defaults_url_when_missing(plugin, make_registry):
    reg = make_registry({"connect": True})  # no mcp_url
    plugin.register(reg)
    assert reg.mcp_servers[0](None)["url"] == "http://127.0.0.1:19789/mcp"


def test_register_survives_empty_config(plugin, make_registry):
    reg = make_registry(None)
    plugin.register(reg)
    # default connect=True, default url
    assert reg.mcp_servers[0](None)["url"] == "http://127.0.0.1:19789/mcp"


def test_manifest_required_fields():
    m = _manifest()
    for key in ("id", "name", "version", "description"):
        assert m.get(key), f"manifest missing {key}"
    assert m["enabled"] is False  # ships disabled
    assert m["id"] == "palmier_pro"
    assert m["capabilities"]["network"] == ["127.0.0.1:19789"]  # loopback only


def test_manifest_version_matches_pyproject():
    m = _manifest()
    pp = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert m["version"] == pp["project"]["version"]
