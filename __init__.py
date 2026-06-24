"""palmier_pro — drive the Palmier Pro macOS video editor from your fleet over a
warm, persistent MCP session.

register() contributes a background surface (the EditorBridge — one long-lived
mcp-remote session, kept warm and self-reconnecting), the agent-facing tools that
route through it, and a skill. Host-only / heavy imports stay lazy so the test
suite loads this with no protoAgent host.
"""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.palmier_pro")


def register(registry) -> None:
    cfg = registry.config or {}

    from .bridge import EditorBridge
    from .tools import build_tools

    bridge = EditorBridge(cfg)

    try:
        registry.register_surface(bridge.start, stop=bridge.stop, name="palmier-pro-bridge")
    except Exception:  # noqa: BLE001 — one failed contribution shouldn't sink the rest
        log.exception("[palmier_pro] registering surface failed")

    try:
        for t in build_tools(bridge):
            registry.register_tool(t)
    except Exception:  # noqa: BLE001
        log.exception("[palmier_pro] registering tools failed")

    try:
        registry.register_skill_dir("skills")
    except Exception:  # noqa: BLE001
        log.exception("[palmier_pro] registering skill dir failed")

    log.info("[palmier_pro] registered (url=%s)", cfg.get("mcp_url") or "default")
