import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DetailedRomSchema, PcComponentSchema } from "@/__generated__";
import PcDlcDetails from "./PcDlcDetails.vue";

const { getRom, setCurrentRom, onBeforeRouteUpdate } = vi.hoisted(() => ({
  getRom: vi.fn(),
  setCurrentRom: vi.fn(),
  onBeforeRouteUpdate: vi.fn(),
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

vi.mock("@/services/api/rom", () => ({ default: { getRom } }));

vi.mock("@/stores/roms", () => ({
  default: () => ({ currentRom: null, setCurrentRom }),
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
} as DetailedRomSchema;

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
  beforeEach(() => {
    getRom.mockReset();
    setCurrentRom.mockReset();
    onBeforeRouteUpdate.mockReset();
    route.params = { rom: "1", component: "2" };
  });

  it("renders only a DLC component contained by its fetched parent", async () => {
    getRom.mockResolvedValue({ data: parent });

    const wrapper = mountView();
    await flushPromises();

    expect(getRom).toHaveBeenCalledWith({ romId: 1 });
    expect(wrapper.get("[data-testid='pc-dlc-handoff']").text()).toContain(
      "DLC/expansion",
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

  it("rejects invalid route updates before fetching parent data", async () => {
    getRom.mockResolvedValue({ data: parent });
    mountView();
    await flushPromises();
    getRom.mockClear();

    await updateRoute({ rom: "1", component: ["2"] });

    expect(getRom).not.toHaveBeenCalled();
  });

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
});
