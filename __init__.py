"""palmier_pro — drive the Palmier Pro macOS video editor from your fleet.

register() is the ONLY place plugin code runs. It contributes the editor's local MCP
server (loopback streamable-HTTP) plus a skill. This module has NO protoAgent host
imports, so the test suite loads it with no host present.
"""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.palmier_pro")

DEFAULT_MCP_URL = "http://127.0.0.1:19789/mcp"
SERVER_NAME = "palmier-pro"


def _mcp_factory(plugin_cfg: dict):
    """Build the register_mcp_server factory bound to this plugin's config.

    The host calls the returned factory at every graph build with the live
    LangGraphConfig; we return an ``mcp.servers[]`` entry pointing at the editor's
    loopback endpoint, or ``None`` when the operator turned the connection off.
    """

    def factory(_config):
        if not plugin_cfg.get("connect", True):
            return None
        url = (plugin_cfg.get("mcp_url") or DEFAULT_MCP_URL).strip()
        if not url:
            return None
        return {"name": SERVER_NAME, "transport": "streamable_http", "url": url}

    return factory


def register(registry) -> None:
    cfg = registry.config or {}

    try:
        registry.register_mcp_server(_mcp_factory(cfg))
    except Exception:  # noqa: BLE001 — one failed contribution shouldn't sink the rest
        log.exception("[palmier_pro] registering MCP server failed")

    try:
        registry.register_skill_dir("skills")
    except Exception:  # noqa: BLE001
        log.exception("[palmier_pro] registering skill dir failed")

    log.info("[palmier_pro] registered (mcp=%s)", cfg.get("mcp_url") or DEFAULT_MCP_URL)
