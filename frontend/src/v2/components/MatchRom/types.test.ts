import { describe, expect, it } from "vitest";
import {
  firstAvailableCover,
  getMatchSources,
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
