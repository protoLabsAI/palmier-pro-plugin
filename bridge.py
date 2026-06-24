"""EditorBridge — one warm, persistent MCP session to the Palmier Pro editor.

The editor's HTTP MCP server builds a fresh server per TCP connection, so the
stateless per-call clients (protoAgent's, or the Python streamable_http client)
400 on tool calls. We instead hold ONE long-lived session through a single
mcp-remote process (the proxy Palmier ships in its .mcpb): connect + initialize
once, then serve every tool call over that warm connection in ~milliseconds
instead of respawning a subprocess per call.

A dedicated worker task owns the session; tool calls hand work to it over an
asyncio.Queue and await a future, so all session I/O stays on one task (no
cross-task cancel-scope hazards). The worker reconnects if the editor restarts.

Host-only / heavy imports (mcp) stay lazy so this module imports with no host.
"""

from __future__ import annotations

import asyncio
import logging

log = logging.getLogger("protoagent.plugins.palmier_pro")

DEFAULT_MCP_URL = "http://127.0.0.1:19789/mcp"
SERVER_NAME = "palmier-pro"
RECONNECT_DELAY = 3.0
CALL_TIMEOUT = 180.0


class BridgeError(RuntimeError):
    """Raised when a call can't reach the editor (offline, disabled, not started)."""


def _result_to_text(res) -> str:
    parts: list[str] = []
    for c in getattr(res, "content", None) or []:
        kind = getattr(c, "type", None)
        if kind == "text":
            parts.append(c.text)
        elif kind == "image":
            parts.append("[image omitted]")
        else:
            parts.append(str(c))
    text = "\n".join(p for p in parts if p)
    if getattr(res, "isError", False):
        return "ERROR: " + (text or "tool returned an error")
    return text


class EditorBridge:
    def __init__(self, cfg: dict | None = None):
        cfg = cfg or {}
        self.url = (cfg.get("mcp_url") or DEFAULT_MCP_URL).strip() or DEFAULT_MCP_URL
        self.command = (cfg.get("proxy_command") or "npx").strip() or "npx"
        self.enabled = bool(cfg.get("connect", True))
        self.connected = False
        self.tools_catalog: list[dict] = []
        self.instructions = ""
        self._queue: asyncio.Queue | None = None
        self._task: asyncio.Task | None = None
        self._stop = False

    # ── lifecycle (driven by register_surface) ───────────────────────────────
    async def start(self) -> None:
        if not self.enabled:
            log.info("[palmier_pro] connect=false — bridge idle")
            return
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self._run(), name="palmier-pro-bridge")
        log.info("[palmier_pro] bridge started (url=%s)", self.url)

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self.connected = False

    # ── worker: keep one warm session alive, reconnect on drop ───────────────
    async def _run(self) -> None:
        while not self._stop:
            try:
                await self._serve_once()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                log.warning("[palmier_pro] session ended: %s", e)
            self.connected = False
            if self._stop:
                break
            await asyncio.sleep(RECONNECT_DELAY)

    async def _serve_once(self) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        try:
            from mcp.shared.exceptions import McpError
        except Exception:  # noqa: BLE001
            McpError = ()  # type: ignore[assignment]

        params = StdioServerParameters(
            command=self.command,
            args=["-y", "mcp-remote", self.url, "--allow-http", "--transport", "http-only"],
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                self.instructions = getattr(init, "instructions", "") or ""
                listed = await session.list_tools()
                self.tools_catalog = [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "inputSchema": getattr(t, "inputSchema", None) or {},
                    }
                    for t in listed.tools
                ]
                self.connected = True
                log.info("[palmier_pro] connected — %d tools", len(self.tools_catalog))
                while not self._stop:
                    item = await self._queue.get()
                    if item is None:
                        return
                    name, args, fut = item
                    if fut.cancelled():
                        continue
                    try:
                        res = await session.call_tool(name, args or {})
                        if not fut.done():
                            fut.set_result(res)
                    except McpError as e:  # protocol/tool error — session still alive
                        if not fut.done():
                            fut.set_exception(e)
                    except Exception as e:  # transport died — surface it and reconnect
                        if not fut.done():
                            fut.set_exception(e)
                        raise

    # ── call path (driven by the agent's tools) ──────────────────────────────
    async def call(self, name: str, arguments: dict | None = None) -> str:
        if not self.enabled:
            raise BridgeError("Palmier Pro connection is disabled (set connect=true).")
        if self._queue is None:
            raise BridgeError("Palmier Pro bridge not started.")
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        await self._queue.put((name, arguments or {}, fut))
        try:
            res = await asyncio.wait_for(fut, CALL_TIMEOUT)
        except TimeoutError as e:
            raise BridgeError(
                "Timed out reaching Palmier Pro — is the editor running with a project open?"
            ) from e
        return _result_to_text(res)
