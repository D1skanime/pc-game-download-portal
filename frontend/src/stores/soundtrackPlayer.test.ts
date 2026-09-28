import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import useSoundtrackPlayer, {
  type PlayerMeta,
  type PlayerTrack,
} from "@/stores/soundtrackPlayer";

const tracks: PlayerTrack[] = [
  {
    romId: 7,
    mediaId: 41,
    fileName: "third.mp3",
    url: "/api/roms/7/media/41/content",
  },
  {
    romId: 7,
    mediaId: 8,
    fileName: "first.mp3",
    url: "/api/roms/7/media/8/content",
  },
  {
    romId: 7,
    mediaId: 23,
    fileName: "second.mp3",
    url: "/api/roms/7/media/23/content",
  },
];

describe("soundtrackPlayer", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("navigates the supplied owned-media order without alphabetizing IDs", () => {
    const player = useSoundtrackPlayer();
    const metas: Record<number, PlayerMeta> = {};

    player.loadPlaylistForRom(7, tracks, metas);
    player.play(tracks[1], metas[tracks[1].mediaId] ?? {});

    player.next();
    expect(player.track?.mediaId).toBe(23);

    player.previous();
    expect(player.track?.mediaId).toBe(8);
  });

  it("retains the active owned track and queue after decode failure", () => {
    const player = useSoundtrackPlayer();

    player.loadPlaylistForRom(7, tracks, {});
    player.play(tracks[0], {});
    player.setError();

    expect(player.track?.mediaId).toBe(41);
    expect(player.playlist.map((item) => item.mediaId)).toEqual([41, 8, 23]);
    expect(player.hasError).toBe(true);
  });
});
