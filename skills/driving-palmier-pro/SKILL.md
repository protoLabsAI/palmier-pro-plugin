---
name: driving-palmier-pro
description: >-
  Use when the agent should edit a video project in Palmier Pro (the AI-native macOS
  video editor) — building or cutting a timeline, importing media, captions, search, or
  placing generated clips. Triggers: "edit the timeline", "cut this video", "add
  captions", "import this footage", "build a sequence in Palmier". Assumes the
  palmier_pro plugin is enabled, so the palmier / palmier_tools / palmier_status tools
  are available. NOT for: generating media on Palmier's paid backend (see the generation
  policy — we generate on our own infra and import).
---

# Driving Palmier Pro

Palmier Pro is a macOS video editor with a local MCP server. The `palmier_pro` plugin
holds one warm session to it and gives you three tools:

- **`palmier(tool_name, arguments)`** — invoke an editor tool.
- **`palmier_tools(tool_name=None)`** — list the editor's tools; pass a name for that
  tool's full input schema.
- **`palmier_status()`** — is the editor connected, and how many tools.

The editor exposes ~35 tools. **Call `palmier_tools()` once at the start** to see the
catalog, and `palmier_tools("add_clips")` for a specific tool's schema before calling
it. Then drive everything through `palmier(...)`.

## Prerequisites (fail fast)

- **The editor must be running on this machine with a project open.** If
  `palmier_status()` reports `connected: false` (or a call returns "not connected" /
  "timed out"), Palmier Pro isn't running or no project is open — say so and stop; don't
  fabricate timeline state.
- You're driving a **GUI app**: edits appear live in the user's editor window.

## Core model (the editor's conventions)

- **All timing is in FRAMES**, never seconds: `frame = round(seconds × fps)`. Get `fps`
  from `palmier("get_timeline", {})`.
- Tracks are ordered and typed (**video** or **audio**). Video clips, images, and text
  overlays live on video tracks; audio on audio tracks.
- A clip occupies `[startFrame, startFrame + durationFrames)` and references a media
  asset by **mediaRef**. `trimStartFrame`/`trimEndFrame` are **source-media** offsets.
- **IDs are short prefixes** (`clipId`, `mediaRef`, `folderId`, …). Pass them back
  **exactly** — never pad or guess a longer form.

## Workflow loop

1. **`palmier_tools()`** to learn the catalog, then **`palmier("get_timeline", {})`**
   once for fps, tracks, and existing clips. Don't re-read between your own edits —
   mutation tools return the IDs/frames they changed.
2. **`palmier("get_media", {})`** before referencing any asset — every `mediaRef` comes
   from there.
3. **Understand before you cut.** `palmier("inspect_media", {...})` to actually
   see/transcribe an asset (transcription is **on-device, free**).
   `palmier("search_media", {...})` to locate a moment across the library — hits are
   source-second ranges ready to become `add_clips` trims.
4. **Edit with one tool per gesture**: `add_clips` / `insert_clips`, `move_clips`,
   `set_clip_properties`, `set_keyframes`, `split_clip`, `ripple_delete_ranges`,
   `remove_clips`, `add_texts`, `add_captions`. Placements must match track type.
5. **Edits are undoable and effectively free.** Make them and explain what changed; use
   `palmier("undo", {})` to back out.
6. **Verify** a complex sequence with `palmier("inspect_timeline", {...})`.

## Generation policy — generate on our infra, then import

In-app generation (`generate_video`, `generate_image`, `generate_audio`,
`upscale_media`) runs on **Palmier's paid hosted backend**: `get_timeline` returns
`canGenerate`, and when it's `false` every generation/upscale call fails until the user
signs into a Palmier account and subscribes. **We avoid that.**

**Default policy:** do NOT use the in-app generation tools. Instead —

1. Generate the asset with **our own pipeline / models**.
2. Write it to a local file (or a reachable `https` URL).
3. **`palmier("import_media", {"source": {...}})`** it into the project, then place it
   with `palmier("add_clips", {...})`.

This keeps all generation on our infrastructure — no Palmier account, no credits. Only
fall back to the in-app generators if the user explicitly asks AND `canGenerate` is
`true`.

## Gotchas

- `canGenerate: false` isn't an error to retry — it means the paid backend isn't
  available. Switch to the import policy above.
- `speed` 1.0 is normal; `<1.0` lengthens the clip on the timeline, `>1.0` shortens it.
  `trim*` are source offsets.
- Setting `volume`/`opacity` via `set_clip_properties` clears existing keyframes on that
  property; use `set_keyframes` (clip-relative frames) to animate.
- Don't paraphrase a filename as if you saw the content — `inspect_media` first.
