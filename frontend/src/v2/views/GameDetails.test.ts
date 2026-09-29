import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  scheduleBackgroundRotation,
  selectedBackgroundAudioTracks,
} from "./GameDetails.vue";

describe("GameDetails", () => {
  it("passes the current parent ROM id to OverviewTab", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain(':parent-rom-id="currentRom.id"');
  });

  it("derives overview screenshots from selected owned-media placements", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain("selectedOverviewScreenshots");
    expect(source).toContain('placement.surface === "overview"');
    expect(source).toContain('media?.role === "screenshot"');
    expect(source).toContain(':screenshots="selectedOverviewScreenshots"');
  });

  it("labels the PC download tab for players instead of the internal model", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain('label: t("rom.game-downloads")');
  });

  it("keeps the patcher tab out of PC game details", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain(
      '...(isPcRom.value ? [] : [{ id: "patcher", label: t("common.patcher") }])',
    );
    expect(source).toMatch(
      /<PatcherTab\s+v-if="tab === 'patcher' && !isPcRom"\s+:rom="currentRom"\s+\/>/,
    );
  });

  it("rotates backgrounds in confirmed server order and cleans up its interval", () => {
    vi.useFakeTimers();
    const setBackground = vi.fn();
    const stop = scheduleBackgroundRotation(
      ["first", "second", "third"],
      "cover",
      true,
      setBackground,
    );

    expect(setBackground).toHaveBeenLastCalledWith("first");
    vi.advanceTimersByTime(10_000);
    expect(setBackground).toHaveBeenLastCalledWith("second");
    vi.advanceTimersByTime(10_000);
    expect(setBackground).toHaveBeenLastCalledWith("third");
    stop();
    vi.advanceTimersByTime(10_000);
    expect(setBackground).toHaveBeenCalledTimes(3);
  });

  it("restarts the rotation when the selected background list changes", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain("watch(");
    expect(source).toContain(
      "[selectedBackgrounds, resolvedCover, isActiveDetailsRoute, reducedMotion]",
    );
    expect(source).toContain("{ immediate: true }");
  });

  it("passes selected local and active owned tracks to background audio as one collection", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain("selectedBackgroundAudio");
    expect(source).toContain('file.category === "soundtrack"');
    expect(source).toContain("owned_background_audio_media_ids");
    expect(source).toContain('media.role === "soundtrack"');
    expect(source).toContain('media.state === "active"');
    expect(source).toContain("/media/${media.id}/content");
    expect(source).toContain("backgroundAudio.playRandom(tracks)");
    expect(source).toContain("onCleanup(() => backgroundAudio.stop())");
  });

  it("combines local and active owned background candidates without source weighting", () => {
    const tracks = selectedBackgroundAudioTracks({
      id: 44,
      files: [
        { id: 1, category: "soundtrack", file_name: "local.mp3" },
        { id: 2, category: "game", file_name: "game.exe" },
      ],
      local_background_audio_file_ids: [1],
      owned_background_audio_media_ids: [10, 11],
      owned_media: [
        { id: 10, role: "soundtrack", state: "active" },
        { id: 11, role: "soundtrack", state: "tombstoned" },
      ],
    });

    expect(tracks).toEqual([
      {
        id: 1,
        url: "/api/roms/1/files/content/local.mp3",
      },
      {
        id: 10,
        url: "/api/roms/44/media/10/content",
      },
    ]);
  });

  it("keeps the first background static when motion is reduced or a list is singular", () => {
    vi.useFakeTimers();
    const setBackground = vi.fn();
    const reducedStop = scheduleBackgroundRotation(
      ["first", "second"],
      "cover",
      false,
      setBackground,
    );
    vi.advanceTimersByTime(30_000);
    expect(setBackground).toHaveBeenCalledTimes(1);
    reducedStop();

    const singleStop = scheduleBackgroundRotation(
      ["first"],
      "cover",
      true,
      setBackground,
    );
    vi.advanceTimersByTime(30_000);
    expect(setBackground).toHaveBeenCalledTimes(2);
    singleStop();
  });
});

afterEach(() => vi.useRealTimers());
