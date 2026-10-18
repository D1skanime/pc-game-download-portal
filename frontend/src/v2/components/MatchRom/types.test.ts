import { describe, expect, it } from "vitest";
import {
  firstAvailableCover,
  getMatchSources,
  getPcCandidateCover,
  type MatchSearchRom,
} from "./types";

describe("PC metadata match provider media", () => {
  it("keeps Steam covers attributed to Steam", () => {
    const candidate = {
      name: "The Witcher 3: Wild Hunt - Blood and Wine",
      steam_url_cover: "https://cdn.example/steam-cover.jpg",
    } as MatchSearchRom;

    expect(firstAvailableCover(candidate)).toBe(
      "https://cdn.example/steam-cover.jpg",
    );
    expect(getMatchSources(candidate)).toEqual([
      {
        name: "Steam",
        logo_path: "/assets/scrappers/steam.svg",
        url_cover: "https://cdn.example/steam-cover.jpg",
      },
    ]);
  });
});

describe("PC candidate cover mapping", () => {
  it.each([
    ["igdb", "igdb_url_cover"],
    ["steam", "steam_url_cover"],
    ["moby", "moby_url_cover"],
    ["sgdb", "sgdb_url_cover"],
    ["launchbox", "launchbox_url_cover"],
    ["screenscraper", "ss_url_cover"],
    ["flashpoint", "flashpoint_url_cover"],
    ["libretro", "libretro_url_cover"],
  ] as const)("maps %s covers to %s", (provider, field) => {
    const coverUrl = "https://cdn.example/" + provider + "-cover.jpg";
    const cover = getPcCandidateCover({
      provider,
      media: [
        { kind: "screenshot", url: "https://cdn.example/shot.jpg" },
        { kind: "artwork", url: "https://cdn.example/art.jpg" },
        { kind: "cover", url: coverUrl },
      ],
    });

    expect(cover).toEqual({ field, url: coverUrl });

    const matchedRom = {
      name: provider,
      [field]: cover?.url,
    } as MatchSearchRom;
    expect(firstAvailableCover(matchedRom)).toBe(coverUrl);
    expect(getMatchSources(matchedRom)[0]?.url_cover).toBe(coverUrl);
  });

  it("ignores candidates without a cover media entry", () => {
    expect(
      getPcCandidateCover({
        provider: "steam",
        media: [
          { kind: "screenshot", url: "https://cdn.example/shot.jpg" },
          { kind: "artwork", url: "https://cdn.example/art.jpg" },
          { kind: "logo", url: "https://cdn.example/logo.jpg" },
          { kind: "fan_art", url: "https://cdn.example/fan-art.jpg" },
          { kind: "video", url: "https://cdn.example/video.mp4" },
        ],
      }),
    ).toBeNull();
  });

  it("ignores unknown providers even when they contain a cover", () => {
    expect(
      getPcCandidateCover({
        provider: "unknown",
        media: [{ kind: "cover", url: "https://cdn.example/cover.jpg" }],
      }),
    ).toBeNull();
  });
});
