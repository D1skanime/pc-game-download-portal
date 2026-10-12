# Phase 28 Research

## Scope

Phase 28 covers three confirmed gaps: YouTube IDs are currently rendered as a
link instead of an embedded preview; the ROM edit dialog does not expose the
already persisted steam_id; and PC save uploads currently use the generic user
asset save path even though PC saves should live with the game's
ROM-owned media/resources.

## Existing implementation evidence

### YouTube

- OverviewTab.vue already resolves manual_metadata.youtube_video_id and
  rom.youtube_video_id.
- IDs are validated as exactly 11 characters and a youtube-nocookie embed URL
  is built.
- The template currently renders an external anchor, not an iframe.
- The overview already has a separate section for scraped local clips.

### Steam App ID

- steam_id exists in generated ROM schemas and backend RomUpdateForm.
- frontend/src/services/api/rom.ts already serializes rom.steam_id in the PUT
  form.
- backend/endpoints/roms/__init__.py already calls the Steam metadata handler
  when a new ID is submitted and clears Steam metadata when it is removed.
- MetadataIdSection.vue lists provider IDs but omits steam_id; this is the UI
  gap, not a missing backend architecture.

### Saves and states

- SaveDataTab.vue supports multi-file upload, refresh, visibility, delete, and
  download for saves and states.
- saveApi posts to /api/saves, and the backend accepts any sanitized filename
  subject to the global 512 MiB asset limit. No ZIP/raw extension whitelist or
  extraction is applied, so both formats are opaque files.
- Downloads use /api/saves/{id}/content and preserve the stored filename.
- Current paths are users/<user>/saves/<platform>/<rom-id>/<emulator> and the
  equivalent states path.
- Existing ROM-owned resources already use rom.fs_resources_path, with
  per-ROM directories such as owned-media, pc-media, and pc-owned-media.
- Save records must remain Save/State rows. The image/audio owned-media tables
  are not a suitable replacement for save semantics.

## Recommended design

Use a canonical resource path below the existing ROM resource directory, with
separate leaves for save files and emulator states. The helper must derive from
the stable ROM resource identity, never from a mutable title:

    <resources-root>/<rom.fs_resources_path>/pc-saves/
      saves/<emulator>/<filename>
      states/<emulator>/<filename>

Uploads write there, database rows keep their existing metadata and point to
the canonical file_path, and downloads resolve canonical paths first. A legacy
resolver must still recognize existing asset paths, and migration must update
rows only after bytes are safely copied/moved and verified by size/hash. ZIP
files are never unpacked automatically.

## Risks and verification

- A path change can orphan existing files if row and byte move are not
  coordinated. Test interrupted/missing-file fallback and idempotent migration.
- Save/state routes must retain ownership, public visibility, device sync, and
  optimistic conflict behavior.
- YouTube embedding can be blocked by browser/network policy; keep a visible
  fallback link and invalid-ID message.
- Steam ID changes must trigger existing enrichment only when the ID changes and
  clear provider data when removed.
- Verify focused frontend tests, backend save endpoint/handler tests,
  typecheck/build, and live Linux Dev/browser UAT for raw and ZIP round trips.
