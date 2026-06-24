# palmier-pro-plugin

A [protoAgent](https://github.com/protoLabsAI/protoAgent) plugin that drops the
**Palmier Pro** macOS video editor into your fleet as a tool surface — over a single
**warm, persistent MCP session**, so the agent can read and edit the timeline, import
media, search, and manage captions with millisecond tool calls.

## What it contributes

- **A background surface** (`register_surface`) — the `EditorBridge`. It holds **one
  long-lived MCP session** to the editor through the `mcp-remote` proxy (the same one
  Palmier ships in its `.mcpb`), connecting + initializing once and keeping it warm. It
  self-reconnects if the editor restarts. This sidesteps the editor's per-connection
  HTTP server (a stateless per-call client 400s on tool calls) **and** the ~1–2s
  subprocess respawn protoAgent would otherwise pay on every call.
- **Three tools** that route through that warm session:
  - `palmier(tool_name, arguments)` — invoke any editor tool (`get_timeline`,
    `add_clips`, `import_media`, …).
  - `palmier_tools(tool_name=None)` — the **live** tool catalog (names + descriptions);
    pass a name for that tool's full JSON input schema.
  - `palmier_status()` — connection state + tool count.
  - Generic dispatch (rather than 35 baked-in tools) keeps the catalog **never-stale**
    — schemas come from the running editor — and the tools still exist (returning a
    clear "not connected") when the editor is offline.
- **A skill** (`driving-palmier-pro`) — the fleet workflow, including the policy of
  **generating media on your own infra and importing it** instead of using Palmier's
  paid hosted generation.

## Prerequisites

- **Palmier Pro running on the same machine, with a project open.** The MCP server is
  loopback-only (`127.0.0.1`); the agent must be co-located (or tunnel to port 19789).
  Enable it under **Settings ▸ Agent ▸ MCP Server**.
- **`node` / `npx` on the host's PATH** — the bridge launches `npx -y mcp-remote …`
  (first run fetches it). Set `proxy_command` to an absolute path if `npx` isn't on the
  host PATH.

## Install

```bash
python -m server plugin install https://github.com/protoLabsAI/palmier-pro-plugin --ref <tag>
```

Then enable it (`enable_plugin("palmier_pro")` or the console Plugins panel). Ships
**disabled** — enabling is the trust decision.

## Config

| Key | Default | Meaning |
|---|---|---|
| `mcp_url` | `http://127.0.0.1:19789/mcp` | The editor's loopback endpoint. Change only if you tunnel to another host. |
| `connect` | `true` | Hold the session. Toggle off to disconnect without disabling the plugin. |
| `proxy_command` | `npx` | Launcher for `mcp-remote`. Set to an absolute path if `npx` isn't on the host PATH. |

## Generation policy

In-app generation (`generate_video`/`image`/`audio`, `upscale_media`) runs on Palmier's
**paid hosted backend** and reports `canGenerate: false` until you sign in + subscribe.
The skill's default is to **bypass it**: generate with your own models and
`palmier("import_media", …)` the result. Transcription and visual search run on-device
and are unaffected.

## Develop

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite is host-free — it loads the plugin with no protoAgent host and exercises
`register()`, the bridge, and the tools against fakes. Live session I/O is validated
separately against a running editor.

## License & relationship to Palmier Pro

This plugin is **separate software** that talks to Palmier Pro at arm's length over the
MCP protocol — it links no Palmier Pro source, so it is not a derivative work of the
(GPLv3) editor. Palmier Pro itself is © Palmier, Inc., licensed under GPLv3.
