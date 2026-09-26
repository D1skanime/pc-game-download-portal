import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import storeHeartbeat from "@/stores/heartbeat";

describe("metadata provider options", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("offers enabled Steam separately from SteamGridDB", () => {
    const heartbeat = storeHeartbeat();
    heartbeat.value.METADATA_SOURCES.STEAM_API_ENABLED = true;
    heartbeat.value.METADATA_SOURCES.STEAMGRIDDB_API_ENABLED = false;

    expect(heartbeat.getEnabledMetadataOptions()).toContainEqual(
      expect.objectContaining({ name: "Steam", value: "steam" }),
    );
    expect(heartbeat.getEnabledMetadataOptions()).not.toContainEqual(
      expect.objectContaining({ value: "sgdb" }),
    );
  });
});
