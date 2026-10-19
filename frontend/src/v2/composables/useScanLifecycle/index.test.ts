import { mount, type VueWrapper } from "@vue/test-utils";
import mitt from "mitt";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, effectScope } from "vue";
import type { ScanStats } from "@/__generated__";
import storeScanning from "@/stores/scanning";

const fake = vi.hoisted(() => ({
  handlers: new Map<string, Set<(payload: unknown) => void>>(),
  connect: vi.fn(),
  platformResponse: { id: 1, rom_count: 0 },
}));

vi.mock("@/v2/composables/useScanOperationStatus", () => ({
  useScanOperationStatus: () => ({ refresh: vi.fn() }),
}));
vi.mock("@/v2/data/adapters/legacy/services/socket", () => ({
  default: {
    connected: true,
    connect: fake.connect,
    on(event: string, handler: (payload: unknown) => void) {
      const handlers = fake.handlers.get(event) ?? new Set();
      handlers.add(handler);
      fake.handlers.set(event, handlers);
    },
    off(event: string, handler: (payload: unknown) => void) {
      fake.handlers.get(event)?.delete(handler);
    },
  },
}));
vi.mock("@/v2/data/adapters/legacy/services/api/platform", () => ({
  default: {
    getPlatform: vi.fn(async () => ({ data: fake.platformResponse })),
  },
}));
vi.mock("@/v2/data/adapters/legacy/stores/platforms", async () => {
  const { defineStore } = await import("pinia");
  return {
    default: defineStore("phase34-platforms", {
      state: () => ({ item: { id: 1, rom_count: 0 } }),
      actions: {
        has() {
          return true;
        },
        get() {
          return this.item;
        },
        add() {},
        async fetchPlatforms() {
          return [this.item];
        },
      },
    }),
  };
});
vi.mock("@/v2/data/adapters/legacy/stores/roms", async () => {
  const { defineStore } = await import("pinia");
  return {
    default: defineStore("phase34-roms", {
      state: () => ({
        currentPlatform: null as { id: number } | null,
        filteredRoms: [] as { id: number }[],
        recent: [] as { id: number }[],
      }),
      actions: {
        removeFromRecent(rom: { id: number }) {
          this.recent = this.recent.filter((item) => item.id !== rom.id);
        },
        addToRecent(rom: { id: number }) {
          this.recent.push(rom);
        },
        update() {},
        add() {},
      },
    }),
  };
});
vi.mock("@/v2/stores/galleryRoms", async () => {
  const { defineStore } = await import("pinia");
  return {
    default: defineStore("phase34-gallery", {
      state: () => ({ currentPlatform: null as { id: number } | null }),
      actions: { invalidateWindows() {}, async fetchInitialMetadata() {} },
    }),
  };
});

function emit(event: string, payload: unknown) {
  for (const handler of [...(fake.handlers.get(event) ?? [])]) handler(payload);
}
function listenerCount() {
  return [...fake.handlers.values()].reduce(
    (sum, handlers) => sum + handlers.size,
    0,
  );
}
const stats: ScanStats = {
  total_platforms: 1,
  scanned_platforms: 0,
  new_platforms: 0,
  identified_platforms: 0,
  total_roms: 2,
  scanned_roms: 1,
  new_roms: 1,
  identified_roms: 0,
  scanned_firmware: 0,
  new_firmware: 0,
};

describe("scan lifecycle scope ownership", () => {
  const owners: VueWrapper[] = [];
  let install: () => void;
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(async () => {
    // Each case gets a clean baseline; disposal/remount within a case never resets modules.
    vi.resetModules();
    vi.useFakeTimers();
    fake.handlers.clear();
    fake.connect.mockClear();
    pinia = createPinia();
    setActivePinia(pinia);
    install = (await import("@/v2/composables/useScanLifecycle"))
      .installScanLifecycle;
  });
  afterEach(() => {
    owners.splice(0).forEach((owner) => owner.unmount());
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  function owner() {
    const wrapper = mount(
      defineComponent({
        setup() {
          effectScope().run(install);
          return () => null;
        },
      }),
      { global: { plugins: [pinia], provide: { emitter: mitt() } } },
    );
    owners.push(wrapper);
    return wrapper;
  }

  it("reinstalls listeners after scope disposal", () => {
    const scanning = storeScanning(pinia);
    const updates = vi.spyOn(scanning, "setScanStats");
    const first = owner();
    expect(listenerCount()).toBe(5);
    emit("scan:update_stats", stats);
    expect(updates).toHaveBeenCalledTimes(1);
    expect(scanning.scanStats.scanned_roms).toBe(1);
    first.unmount();
    owners.splice(owners.indexOf(first), 1);
    expect(listenerCount()).toBe(0);
    owner();
    emit("scan:update_stats", { ...stats, scanned_roms: 2 });
    expect(
      listenerCount(),
      "P34_REMOUNT: fresh scope must reinstall exactly once",
    ).toBe(5);
    expect(updates).toHaveBeenCalledTimes(2);
    expect(scanning.scanStats.scanned_roms).toBe(2);
  });

  it("keeps listeners while another owner survives", () => {
    const scanning = storeScanning(pinia);
    const updates = vi.spyOn(scanning, "setScanStats");
    const first = owner();
    owner();
    expect(listenerCount()).toBe(5);
    emit("scan:update_stats", stats);
    expect(updates).toHaveBeenCalledTimes(1);
    first.unmount();
    owners.splice(owners.indexOf(first), 1);
    emit("scan:update_stats", { ...stats, scanned_roms: 2 });
    expect(
      listenerCount(),
      "P34_OWNERS: disposing one owner must preserve the other",
    ).toBe(5);
    expect(updates).toHaveBeenCalledTimes(2);
  });

  it("cancels debounce work on final disposal", async () => {
    const scanning = storeScanning(pinia);
    const first = owner();
    emit("scan:scanning_rom", {
      id: 7,
      platform_id: 1,
      platform_fs_slug: "pc",
      platform_display_name: "PC",
      platform_slug: "pc",
      name: "Synthetic",
    });
    expect(scanning.scanning).toBe(false);
    expect(scanning.scanningPlatforms).toHaveLength(0);
    first.unmount();
    owners.splice(owners.indexOf(first), 1);
    expect(listenerCount()).toBe(0);
    await vi.advanceTimersByTimeAsync(1500);
    expect(
      scanning.scanningPlatforms,
      "P34_DEBOUNCE: disposed scope must not mutate stores",
    ).toHaveLength(0);
  });
});
