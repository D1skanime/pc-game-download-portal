import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/services/api";
import type { UpdateRom } from "@/services/api/rom";
import romApi from "@/services/api/rom";

vi.mock("@/services/api", () => ({
  default: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
}));
vi.mock("@/stores/upload", () => ({ default: vi.fn() }));

const version = "2026-10-22T08:00:00+00:00";

describe("matching locale transport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue({
      data: { expected_version: version, providers: {} },
    });
    vi.mocked(api.put).mockResolvedValue({ data: {} });
    vi.mocked(api.post).mockResolvedValue({ data: {} });
  });

  it.each(["Name", "ID"])(
    "sends captured locale for console %s search",
    async (searchBy) => {
      const request = {
        romId: 41,
        searchTerm: "Game",
        searchBy,
        metadataLocale: "de-CH",
      };
      await romApi.searchRom(request);
      expect(api.get).toHaveBeenCalledWith("/search/roms", {
        params: {
          rom_id: 41,
          search_term: "Game",
          search_by: searchBy,
          metadata_locale: "de-CH",
        },
      });
    },
  );

  it.each([false, true])(
    "sends captured PC candidate locale (component=%s)",
    async (component) => {
      const request = {
        romId: 41,
        componentId: 7,
        query: "Game",
        metadataLocale: "fr",
      };
      if (component) await romApi.searchPcComponentMetadataCandidates(request);
      else await romApi.searchPcMetadataCandidates(request);
      expect(api.get).toHaveBeenCalledWith(
        component
          ? "/roms/41/pc-components/7/metadata-candidates"
          : "/roms/41/pc-metadata-candidates",
        { params: { query: "Game", metadata_locale: "fr" } },
      );
    },
  );

  it.each([false, true])(
    "preserves exact PC selection and version (component=%s)",
    async (component) => {
      const selection = {
        candidate_id: "steam:1",
        expected_version: version,
        query: "Game",
        selected_media_ids: ["cover"],
        metadata_locale: "de",
      };
      if (component)
        await romApi.selectPcComponentMetadataCandidate({
          romId: 41,
          componentId: 7,
          selection,
        });
      else await romApi.selectPcMetadataCandidate({ romId: 41, selection });
      expect(api.post).toHaveBeenCalledWith(
        component
          ? "/roms/41/pc-components/7/metadata-selection"
          : "/roms/41/pc-metadata-selection",
        selection,
      );
    },
  );

  it("keeps console concurrency in query and never synthesizes manual text", async () => {
    await romApi.updateRom({
      rom: { id: 41, ss_id: 33, summary: null } as UpdateRom,
      metadataLocale: "fr",
      expectedVersion: version,
    });
    expect(api.put).toHaveBeenCalledWith("/roms/41", expect.any(FormData), {
      params: {
        remove_cover: false,
        unmatch_metadata: false,
        metadata_locale: "fr",
        expected_version: version,
      },
    });
    const form = vi.mocked(api.put).mock.calls[0][1] as FormData;
    expect(form.has("raw_manual_metadata")).toBe(false);
    expect(form.get("ss_id")).toBe("33");
  });
});
