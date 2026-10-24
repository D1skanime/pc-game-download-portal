import { flushPromises, mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DetailedRomSchema, PcComponentSchema } from "@/__generated__";
import PcDlcDetails from "./PcDlcDetails.vue";

const {
  getRom,
  setCurrentRom,
  onBeforeRouteUpdate,
  lookupProviderMetadata,
  applyProviderMetadata,
  selectLocalMedia,
  uploadLocalMedia,
  downloadIntoSource,
  deleteFromSource,
  mutateFilesystem,
} = vi.hoisted(() => ({
  getRom: vi.fn(),
  setCurrentRom: vi.fn(),
  onBeforeRouteUpdate: vi.fn(),
  lookupProviderMetadata: vi.fn(),
  applyProviderMetadata: vi.fn(),
  selectLocalMedia: vi.fn(),
  uploadLocalMedia: vi.fn(),
  downloadIntoSource: vi.fn(),
  deleteFromSource: vi.fn(),
  mutateFilesystem: vi.fn(),
}));

let currentRom: Pick<DetailedRomSchema, "id" | "name" | "components"> | null =
  null;

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: vi.fn() }),
}));

const route = {
  params: { rom: "1", component: "2" } as Record<string, unknown>,
};

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "common.library": "Library",
        "rom.loading-rom": "Loading ROM…",
      })[key] ?? key,
  }),
}));

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  onBeforeRouteUpdate,
  useRoute: () => route,
}));

vi.mock("@/services/api/rom", () => ({
  default: {
    getRom,
    lookupProviderMetadata,
    applyProviderMetadata,
    selectLocalMedia,
    uploadLocalMedia,
    downloadIntoSource,
    deleteFromSource,
    mutateFilesystem,
  },
}));

vi.mock("@/stores/roms", () => ({
  default: () => ({
    get currentRom() {
      return currentRom;
    },
    setCurrentRom,
  }),
}));

const dlc = {
  id: 2,
  relative_path: "DLC/expansion",
  kind: "dlc",
  manifest_members: [],
} satisfies PcComponentSchema;

const parent = {
  id: 1,
  name: "Parent game",
  components: [
    dlc,
    {
      id: 3,
      relative_path: "Updates/1.1",
      kind: "update",
      manifest_members: [],
    },
  ],
} satisfies Pick<DetailedRomSchema, "id" | "name" | "components">;

function mountView() {
  return mount(PcDlcDetails, {
    global: {
      stubs: {
        RBtn: {
          template: "<a><slot /></a>",
        },
        REmptyState: {
          props: ["title"],
          template: "<section><h1>{{ title }}</h1><slot /></section>",
        },
        PcDlcDetail: {
          name: "PcDlcDetail",
          props: ["parent", "component"],
          template: "<section />",
        },
      },
    },
  });
}

async function updateRoute(params: Record<string, unknown>) {
  const handler = onBeforeRouteUpdate.mock.calls.at(-1)?.[0] as
    ((to: { params: Record<string, unknown> }) => Promise<void>) | undefined;
  expect(handler).toBeTypeOf("function");
  route.params = params;
  await handler!({ params });
}

describe("PcDlcDetails", () => {
  it("provides a contained refresh callback after component actions", () => {
    const source = readFileSync("src/v2/views/PcDlcDetails.vue", "utf8");

    expect(source).toContain("async function refreshDlc()");
    expect(source).toContain('@refresh="refreshDlc"');
  });

  it("forces a fresh parent read after child mutations", () => {
    const source = readFileSync("src/v2/views/PcDlcDetails.vue", "utf8");

    expect(source).toContain("forceFresh = false");
    expect(source).toContain(
      "!forceFresh && romsStore.currentRom?.id === romId",
    );
    expect(source).toContain("await loadDlc(route.params, true)");
  });

  beforeEach(() => {
    getRom.mockReset();
    setCurrentRom.mockReset();
    onBeforeRouteUpdate.mockReset();
    lookupProviderMetadata.mockReset();
    applyProviderMetadata.mockReset();
    selectLocalMedia.mockReset();
    uploadLocalMedia.mockReset();
    downloadIntoSource.mockReset();
    deleteFromSource.mockReset();
    mutateFilesystem.mockReset();
    currentRom = null;
    route.params = { rom: "1", component: "2" };
  });

  it("renders only a DLC component contained by its fetched parent", async () => {
    getRom.mockResolvedValue({ data: parent });

    const wrapper = mountView();
    await flushPromises();

    expect(getRom).toHaveBeenCalledWith({ romId: 1 });
    expect(wrapper.getComponent({ name: "PcDlcDetail" }).props()).toMatchObject(
      {
        parent,
        component: dlc,
      },
    );
    expect(wrapper.text()).not.toContain("Updates/1.1");
  });

  it.each([
    "",
    "+1",
    "-1",
    " 1",
    "1 ",
    "1.0",
    "1e2",
    "x1",
    "1x",
    "01",
    "9007199254740992",
  ])("does not fetch invalid parent IDs on direct entry: %j", async (rom) => {
    route.params = { rom, component: "2" };

    const wrapper = mountView();
    await flushPromises();

    expect(getRom).not.toHaveBeenCalled();
    expect(wrapper.text()).toBe("Library");
  });

  it.each([
    "",
    "+2",
    "-2",
    " 2",
    "2 ",
    "2.0",
    "2e0",
    "x2",
    "2x",
    "02",
    "9007199254740992",
  ])(
    "does not fetch invalid component IDs on direct entry: %j",
    async (component) => {
      route.params = { rom: "1", component };

      const wrapper = mountView();
      await flushPromises();

      expect(getRom).not.toHaveBeenCalled();
      expect(wrapper.text()).toBe("Library");
    },
  );

  it("rejects array parameters before conversion and fetch", async () => {
    route.params = { rom: ["1"], component: "2" };
    const wrapper = mountView();
    await flushPromises();

    expect(getRom).not.toHaveBeenCalled();
    expect(wrapper.text()).toBe("Library");
  });

  it.each([
    { rom: "1x", component: "2" },
    { rom: "1", component: "2x" },
    { rom: ["1"], component: "2" },
    { rom: "1", component: ["2"] },
  ])(
    "rejects invalid route updates before fetching parent data: %o",
    async (params) => {
      getRom.mockResolvedValue({ data: parent });
      const wrapper = mountView();
      await flushPromises();
      getRom.mockClear();

      await updateRoute(params);

      expect(getRom).not.toHaveBeenCalled();
      expect(wrapper.text()).toBe("Library");
    },
  );

  it("renders no child data for stale or non-DLC components", async () => {
    getRom.mockResolvedValue({ data: parent });
    route.params = { rom: "1", component: "99" };
    const stale = mountView();
    await flushPromises();

    expect(stale.text()).toBe("Library");

    route.params = { rom: "1", component: "3" };
    const nonDlc = mountView();
    await flushPromises();

    expect(nonDlc.text()).toBe("Library");
  });

  it("renders the library escape when the parent request fails", async () => {
    getRom.mockRejectedValue(new Error("parent unavailable"));
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.text()).toBe("Library");
  });

  it("keeps the same detail instance mounted while a mutation refresh is pending", async () => {
    getRom.mockResolvedValueOnce({ data: parent });
    const wrapper = mountView();
    await flushPromises();
    const detail = wrapper.getComponent({ name: "PcDlcDetail" });
    let release!: (value: { data: typeof parent }) => void;
    getRom.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    detail.vm.$emit("refresh");
    await flushPromises();
    expect(wrapper.find('[data-testid="pc-dlc-loading"]').exists()).toBe(false);
    expect(wrapper.getComponent({ name: "PcDlcDetail" }).vm).toBe(detail.vm);
    release({ data: parent });
    await flushPromises();
    expect(wrapper.getComponent({ name: "PcDlcDetail" }).vm).toBe(detail.vm);
  });

  it("retains freshly saved DLC media across a tab-only route update despite an old parent store", async () => {
    currentRom = parent;
    const wrapper = mountView();
    await flushPromises();
    const fresh = {
      ...parent,
      components: [
        { ...dlc, updated_at: "2026-10-24T01:30:00Z", owned_media: [] },
      ],
    };
    getRom.mockResolvedValue({ data: fresh });
    wrapper.getComponent({ name: "PcDlcDetail" }).vm.$emit("refresh");
    await flushPromises();
    expect(
      wrapper.getComponent({ name: "PcDlcDetail" }).props("component"),
    ).toEqual(fresh.components[0]);
    await updateRoute({ rom: "1", component: "2" });
    await flushPromises();
    expect(
      wrapper.getComponent({ name: "PcDlcDetail" }).props("component"),
    ).toEqual(fresh.components[0]);
    expect(getRom).toHaveBeenCalledTimes(1);
    expect(setCurrentRom).toHaveBeenCalledWith(fresh);
  });

  it("uses only the parent read while loading and navigating between DLC routes", async () => {
    getRom.mockResolvedValue({
      data: {
        ...parent,
        components: [...parent.components, { ...dlc, id: 4 }],
      },
    });

    mountView();
    await flushPromises();
    await updateRoute({ rom: "1", component: "4" });

    expect(getRom).toHaveBeenCalledTimes(2);
    expect(getRom).toHaveBeenLastCalledWith({ romId: 1 });
    [
      lookupProviderMetadata,
      applyProviderMetadata,
      selectLocalMedia,
      uploadLocalMedia,
      downloadIntoSource,
      deleteFromSource,
      mutateFilesystem,
    ].forEach((mock) => expect(mock).not.toHaveBeenCalled());
  });
});
