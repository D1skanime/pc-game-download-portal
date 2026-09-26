import { describe, expect, it } from "vitest";
import { PROVIDERS } from "./providers";

describe("Steam provider registry", () => {
  it("maps persisted Steam App IDs to Steam Storefront links independently of SteamGridDB", () => {
    const steam = PROVIDERS.find((provider) => provider.key === "steam_id");
    const sgdb = PROVIDERS.find((provider) => provider.key === "sgdb_id");

    expect(steam).toMatchObject({
      key: "steam_id",
      name: "Steam",
      logo: null,
    });
    expect(steam?.url?.(1091500, {} as never)).toBe(
      "https://store.steampowered.com/app/1091500",
    );
    expect(sgdb).toMatchObject({
      key: "sgdb_id",
      name: "SteamGridDB",
      logo: "/assets/scrappers/sgdb.png",
    });
    expect(sgdb?.url?.(1091500, {} as never)).toBe(
      "https://www.steamgriddb.com/game/1091500",
    );
  });
});
