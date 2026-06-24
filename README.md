# palmier-pro-plugin

A [protoAgent](https://github.com/protoLabsAI) plugin that drops the **Palmier Pro**
macOS video editor into your fleet as a tool surface. It registers the editor's local
MCP server so an agent can read and edit the timeline, import media, search, and manage
captions — and ships a skill that teaches the workflow.

## What it contributes

- **An MCP server** (`register_mcp_server`) for the editor's loopback endpoint
  `http://127.0.0.1:19789/mcp`. The editor's 35 tools (`get_timeline`, `get_media`,
  `add_clips`, `import_media`, `search_media`, `add_captions`, …) become available to
  the agent. Connection is via the **`mcp-remote` stdio proxy** — the same one Palmier
  ships in its `.mcpb`. The editor's HTTP server builds a fresh MCP server per TCP
  connection, which a stateless `streamable_http` client trips over (tool calls 400);
  `mcp-remote` holds one persistent connection, so it works reliably.
- **A skill** (`driving-palmier-pro`) — the fleet-level workflow, including the policy
  of **generating media on your own infra and importing it** rather than using
  Palmier's paid hosted generation.

## Prerequisites

- **Palmier Pro running on the same machine, with a project open.** The MCP server is
  loopback-only (`127.0.0.1`), so the agent driving it must be co-located (or you must
  tunnel to that Mac's port 19789). Enable the server in Palmier Pro under
  **Settings ▸ Agent ▸ MCP Server**.
- **`node` / `npx` on the host's PATH.** The plugin launches `npx -y mcp-remote …`;
  the first run fetches `mcp-remote`. If `npx` isn't on the host PATH, set
  `proxy_command` to an absolute path.

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
| `connect` | `true` | Register the server. Toggle off to disconnect without disabling the plugin. |
| `proxy_command` | `npx` | Launcher for `mcp-remote`. Set to an absolute path if `npx` isn't on the host PATH. |

## Generation policy

In-app generation (`generate_video`/`image`/`audio`, `upscale_media`) runs on
Palmier's **paid hosted backend** and requires a Palmier account + subscription
(`get_timeline` returns `canGenerate: false` otherwise). The skill's default is to
**bypass it**: generate with your own models and `import_media` the result. Transcription
and visual search run on-device and are unaffected.

## Develop

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite is host-free — it loads the plugin with no protoAgent host and exercises
`register()` and the MCP factory against a fake registry.

## License & relationship to Palmier Pro

This plugin is **separate software** that talks to Palmier Pro at arm's length over the
MCP network protocol — it does not link or include any Palmier Pro source, so it is not
a derivative work of the (GPLv3) editor. Palmier Pro itself is © Palmier, Inc., licensed
under GPLv3.
