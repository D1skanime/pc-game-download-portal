import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import deSetup from "@/locales/de_DE/setup.json";
import enSetup from "@/locales/en_US/setup.json";
import SetupStepMetadata from "./SetupStepMetadata.vue";

const heartbeat = vi.hoisted(() => ({
  value: {
    METADATA_SOURCES: {
      IGDB_API_ENABLED: false,
      SS_API_ENABLED: false,
      MOBY_API_ENABLED: false,
      RA_API_ENABLED: false,
      STEAMGRIDDB_API_ENABLED: false,
      STEAM_API_ENABLED: false,
      LAUNCHBOX_API_ENABLED: false,
      FLASHPOINT_API_ENABLED: false,
      HLTB_API_ENABLED: false,
      HASHEOUS_API_ENABLED: false,
      PLAYMATCH_API_ENABLED: false,
    },
  },
  fetchMetadataHeartbeat: vi.fn(),
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock("@/v2/data/adapters/legacy/stores/heartbeat", () => ({
  default: () => heartbeat,
}));

function mountSetup() {
  return mount(SetupStepMetadata, {
    global: {
      stubs: {
        RIcon: true,
        RImg: true,
        RTag: {
          props: ["prependIcon", "size", "tone"],
          template: '<span class="r-tag"><slot /></span>',
        },
      },
    },
  });
}

function setSteamState(enabled: boolean) {
  heartbeat.value.METADATA_SOURCES.STEAM_API_ENABLED = enabled;
}

beforeEach(() => {
  heartbeat.value.METADATA_SOURCES.STEAM_API_ENABLED = false;
  heartbeat.value.METADATA_SOURCES.STEAMGRIDDB_API_ENABLED = false;
  heartbeat.fetchMetadataHeartbeat.mockReset();
});

describe("SetupStepMetadata Steam", () => {
  it("renders Steam separately from SteamGridDB", async () => {
    setSteamState(true);
    heartbeat.value.METADATA_SOURCES.STEAMGRIDDB_API_ENABLED = true;
    heartbeat.fetchMetadataHeartbeat.mockResolvedValue(true);

    const wrapper = mountSetup();
    await flushPromises();

    const names = wrapper
      .findAll(".r-setup-metadata__item-name")
      .map((item) => item.text());
    expect(names).toContain("Steam");
    expect(names).toContain("SteamGridDB");
  });

  it("probes enabled Steam through the existing heartbeat provider key", async () => {
    setSteamState(true);
    heartbeat.fetchMetadataHeartbeat.mockResolvedValue(true);

    mountSetup();
    await flushPromises();

    expect(heartbeat.fetchMetadataHeartbeat).toHaveBeenCalledWith("steam");
  });

  it("does not probe disabled Steam and marks it disabled", async () => {
    setSteamState(false);
    heartbeat.fetchMetadataHeartbeat.mockResolvedValue(true);

    const wrapper = mountSetup();
    await flushPromises();

    const steam = wrapper
      .findAll(".r-setup-metadata__item")
      .find(
        (item) => item.find(".r-setup-metadata__item-name").text() === "Steam",
      );
    expect(heartbeat.fetchMetadataHeartbeat).not.toHaveBeenCalledWith("steam");
    expect(steam?.attributes("data-state")).toBe("missing");
    expect(steam?.text()).toContain("setup.metadata-status-disabled");
  });

  it("keeps flag-only Steam statuses separate from API-key statuses", async () => {
    setSteamState(true);
    heartbeat.fetchMetadataHeartbeat.mockResolvedValue(false);

    const unreachable = mountSetup();
    await flushPromises();
    expect(unreachable.text()).toContain("setup.metadata-status-unreachable");
    expect(unreachable.text()).not.toContain(
      "setup.metadata-status-key-invalid",
    );

    heartbeat.fetchMetadataHeartbeat.mockReset();
    heartbeat.fetchMetadataHeartbeat.mockResolvedValue(true);
    const available = mountSetup();
    await flushPromises();
    expect(available.text()).toContain("setup.metadata-status-available");
  });

  it("shows checking while the Steam heartbeat is pending", () => {
    setSteamState(true);
    heartbeat.fetchMetadataHeartbeat.mockReturnValue(new Promise(() => {}));

    const wrapper = mountSetup();
    expect(wrapper.text()).toContain("setup.metadata-status-checking");
  });

  it("provides the Steam setup copy in the authoritative locales", () => {
    expect(enSetup["provider-steam-desc"]).toBe(
      "Steam metadata for PC games and DLCs, using the Steam Store.",
    );
    expect(enSetup["provider-steam-setup"]).toBe(
      "No API key is required. Enable globally with STEAM_API_ENABLED=true.",
    );
    expect(deSetup["provider-steam-desc"]).toBe(
      "Steam-Metadaten für PC-Spiele und DLCs aus dem Steam Store.",
    );
    expect(deSetup["provider-steam-setup"]).toBe(
      "Kein API-Schlüssel erforderlich. Global mit STEAM_API_ENABLED=true aktivieren.",
    );
  });
});
