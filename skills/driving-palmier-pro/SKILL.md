---
name: driving-palmier-pro
description: >-
  Use when the agent should edit a video project in Palmier Pro (the AI-native macOS
  video editor) — building or cutting a timeline, importing media, captions, search,
  or placing generated clips. Triggers: "edit the timeline", "cut this video", "add
  captions", "import this footage", "build a sequence in Palmier". Assumes the
  palmier_pro plugin is enabled so the editor's MCP tools (get_timeline, add_clips,
  import_media, …) are available. NOT for: generating media on Palmier's paid backend
  (see the generation policy below — we generate on our own infra and import).
---

# Driving Palmier Pro

Palmier Pro is a macOS video editor that exposes a local **MCP server**. When the
`palmier_pro` plugin is enabled, its tools (`get_timeline`, `get_media`, `add_clips`,
`import_media`, `search_media`, …) are available to you directly. The server also
ships its own detailed instructions and per-tool schemas over MCP — read a tool's
description before first use; this skill is the **fleet-level workflow**, not the
schema.

## Prerequisites (fail fast)

- **The editor must be running on this same machine, with a project open.** The MCP
  server is loopback-only (`127.0.0.1`). If tools return connection-refused or the
  toolset is empty, Palmier Pro isn't running or no project is open — say so and stop;
  don't fabricate timeline state.
- You are driving a **GUI app**: edits appear live in the user's editor window.

## Core model (the editor's conventions)

- **All timing is in FRAMES**, never seconds: `frame = round(seconds × fps)`. Get
  `fps` from `get_timeline`.
- Tracks are ordered and typed (**video** or **audio**). Video clips, images, and
  text overlays all live on video tracks; audio on audio tracks.
- A clip occupies `[startFrame, startFrame + durationFrames)` and references a media
  asset by **mediaRef**. `trimStartFrame`/`trimEndFrame` are **source-media** offsets,
  not timeline offsets.
- **IDs are short prefixes** (`clipId`, `mediaRef`, `folderId`, `captionGroupId`).
  Pass them back **exactly** as given — never pad, complete, or guess a longer form.

## Workflow loop

1. **`get_timeline` once** per session for fps, tracks, and existing clips. Don't
   re-read between your own edits — mutation tools return the IDs/frames they changed.
   Re-read only after an out-of-band change or a failure that suggests a stale model.
2. **`get_media`** before referencing any asset — every `mediaRef` comes from there.
3. **Understand before you cut.** `inspect_media` to actually see/transcribe an asset
   (transcription runs **on-device, free**). `search_media` to locate a moment across
   the library ("the sunset shot", "where she mentions the budget") instead of
   inspecting files one by one — hits come back as source-second ranges ready to turn
   into `add_clips` trims. For transcript-driven cuts, read the word-level
   `get_transcript` as prose before deduping (the segment view is lossy).
4. **Edit with one tool per gesture**, applied to a selection: `add_clips` /
   `insert_clips`, `move_clips`, `set_clip_properties`, `set_keyframes`, `split_clip`,
   `ripple_delete_ranges`, `remove_clips` / `remove_tracks`, `add_texts`,
   `add_captions`. Placements must match track type.
5. **Edits are undoable and effectively free.** Don't ask permission for individual
   edits — make them and explain what changed. Use `undo` to back out.
6. **Verify** a complex sequence with `inspect_timeline` rather than re-reading raw
   state.

## Generation policy — generate on our infra, then import

In-app generation (`generate_video`, `generate_image`, `generate_audio`,
`upscale_media`) runs on **Palmier's paid hosted backend**: `get_timeline` returns
`canGenerate`, and when it's `false` every generation/upscale call fails until the
user signs into a Palmier account and subscribes. **That is a dependency we avoid.**

**Default policy:** do NOT use the in-app generation tools. Instead —

1. Generate the image/video/audio with **our own pipeline / models** (outside the
   editor).
2. Write the result to a local file (or a reachable `https` URL).
3. **`import_media`** it into the project (a local path or a URL; recursive for a
   directory), then place it on the timeline with `add_clips`.

This keeps all generation on our own infrastructure — no Palmier account, no credits,
no data through their backend — while still using the editor for assembly. Only fall
back to the in-app generators if the user explicitly asks for them AND `canGenerate`
is `true`.

## Media management

`import_media`, `inspect_media`, `rename_media`, `delete_media`, and folders
(`list_folders`, `create_folder`, `move_to_folder`, `rename_folder`, `delete_folder`)
mirror the library. `list_models` reports what the in-app generators support (only
relevant if you ever fall back to them).

## Gotchas

- `canGenerate: false` is not an error to retry — it means the paid backend isn't
  available. Switch to the import policy above.
- `speed` 1.0 is normal; `<1.0` lengthens the clip on the timeline, `>1.0` shortens
  it. `trim*` are source offsets.
- Setting `volume`/`opacity` via `set_clip_properties` clears existing keyframes on
  that property; use `set_keyframes` (clip-relative frames) to animate.
- Don't paraphrase a filename as if you saw the content — `inspect_media` first.
