import { shallowMount, flushPromises } from "@vue/test-utils";
import mitt from "mitt";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import type { SimpleRom } from "@/stores/roms";
import type { Events } from "@/types/emitter";
import MatchRomDialog from "@/v2/components/Dialogs/MatchRomDialog.vue";
import {
  isPcMatchTarget,
  type PcMatchTarget,
} from "@/v2/components/MatchRom/types";
import { resolveDescription } from "@/v2/composables/useManualDescription";

describe("MatchRomDialog PC targets", () => {
  it("requires a concrete classified component identity", () => {
    const target = {
      kind: "component",
      romId: 41,
      componentId: 7,
      componentKind: "dlc",
      label: "The Royal Edition",
    } satisfies PcMatchTarget;

    expect(target.componentKind).toBe("dlc");
    expect(isPcMatchTarget(target)).toBe(true);
  });
});

function matchDialogSource(): string {
  return readFileSync(
    resolve(process.cwd(), "src/v2/components/Dialogs/MatchRomDialog.vue"),
    "utf8",
  );
}

describe("MatchRomDialog operation parity guards", () => {
  it("uses the typed PC cover helper without changing classic search mapping", () => {
    const source = matchDialogSource();

    expect(source).toContain("getPcCandidateCover(candidate)");
    expect(source).not.toContain("candidate.media[0]?.url");
  });

  it("keeps the classic match context until the update succeeds", () => {
    const source = matchDialogSource();

    expect(source).toContain("const updatedRom = {\n    ...targetRom");
    expect(source).toContain("closeDialog();\n  } catch");
    expect(source).not.toContain(
      "} finally {\n    matching.value = false;\n    closeDialog();",
    );
  });

  it("keeps specialized PC parent and DLC endpoints behind their target guard", () => {
    const source = matchDialogSource();

    expect(source).toContain('pcTarget.value.kind === "component"');
    expect(source).toContain("romApi.selectPcComponentMetadataCandidate");
    expect(source).toContain("romApi.selectPcMetadataCandidate");
    expect(source).toContain("expected_version: expectedVersion");
    expect(source).toContain("selected_media_ids: selectedMedia");
  });

  it("closes PC matches before best-effort refresh and isolates refresh errors", () => {
    const source = matchDialogSource();
    const pcAssignment = source.slice(
      source.indexOf("if (pcTarget.value)"),
      source.indexOf("const targetRom"),
    );
    const closeIndex = pcAssignment.indexOf("closeDialog();");
    const refreshIndex = pcAssignment.indexOf("await refresh");

    expect(closeIndex).toBeGreaterThan(-1);
    expect(refreshIndex).toBeGreaterThan(closeIndex);
    expect(pcAssignment).toContain("try {");
    expect(pcAssignment).toContain("catch (refreshError: unknown)");
    expect(pcAssignment).toContain(
      "closeDialog();\n    try {\n      await refresh?.();",
    );
  });
});

const dialogMocks = vi.hoisted(() => ({
  locale: { value: "de" },
  searchRom: vi.fn(),
  searchPcMetadataCandidates: vi.fn(),
  searchPcComponentMetadataCandidates: vi.fn(),
  selectPcMetadataCandidate: vi.fn(),
  selectPcComponentMetadataCandidate: vi.fn(),
  updateRom: vi.fn(),
  update: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    locale: dialogMocks.locale,
    t: (key: string) => key,
  }),
}));
vi.mock("vue-router", () => ({ useRoute: () => ({ name: "rom" }) }));
vi.mock("@/v2/composables/useBreakpoint", () => ({
  useBreakpoint: () => ({ lgAndUp: true }),
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({
    success: dialogMocks.success,
    error: dialogMocks.error,
  }),
}));
vi.mock("@/v2/data/adapters/legacy/services/api/rom", () => ({
  default: dialogMocks,
}));
vi.mock("@/v2/data/adapters/legacy/stores/roms", () => ({
  default: () => ({
    update: dialogMocks.update,
  }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/heartbeat", () => ({
  default: () =>
    ref({
      METADATA_SOURCES: { SS_API_ENABLED: true, STEAM_API_ENABLED: true },
    }),
}));
vi.mock("@v2/lib", async () => {
  const { defineComponent } = await import("vue");
  return Object.fromEntries(
    [
      "RBtn",
      "RDialog",
      "RIcon",
      "RSelect",
      "RSliderBtnGroup",
      "RSpinner",
      "RTextField",
    ].map((key) => [
      key,
      defineComponent({ name: key, template: "<div><slot /></div>" }),
    ]),
  );
});
vi.mock("@/v2/components/MatchRom/MatchRomBodyGrid.vue", () => ({
  default: {
    name: "MatchRomBodyGrid",
    props: ["results", "searching"],
    template: "<div />",
  },
}));
vi.mock("@/v2/components/MatchRom/MatchRomBodyList.vue", () => ({
  default: {
    name: "MatchRomBodyList",
    props: ["results"],
    template: "<div />",
  },
}));
vi.mock("@/v2/components/MatchRom/MatchRomProviderFilter.vue", () => ({
  default: { template: "<div />" },
}));

const version = "2026-10-22T08:00:00+00:00";
const matched = {
  id: 9,
  platform_id: 1,
  name: "Game",
  ss_id: 33,
  summary: "Untrusted fallback",
  ss_metadata: {
    text_variants: { de: { source_language: "de", summary: "Deutsch" } },
  },
};
const targetFields: Partial<SimpleRom> = {
  id: 41,
  name: "Game",
  fs_name_no_tags: "Game",
  updated_at: version,
  ss_id: 33,
  manual_metadata: { descriptions: { en: "Saved English" } },
};
const target = targetFields as SimpleRom;
const pcCandidate = {
  id: "steam:33",
  provider: "steam",
  title: "Game",
  media: [],
  steam_metadata: {
    text_variants: { de: { source_language: "german", summary: "Deutsch" } },
  },
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function mountDialog() {
  const emitter = mitt<Events>();
  const wrapper = shallowMount(MatchRomDialog, {
    global: {
      provide: { emitter },
      stubs: {
        RDialog: {
          name: "RDialog",
          props: ["modelValue"],
          template:
            "<div><slot name='toolbar' /><slot name='content' /><slot name='footer' /></div>",
        },
      },
    },
  });
  const search = async () => {
    wrapper
      .findComponent({ name: "RTextField" })
      .vm.$emit("keyup", { key: "Enter" });
    await flushPromises();
  };
  const body = () => wrapper.findComponent({ name: "MatchRomBodyGrid" });
  const confirm = async () => {
    body().vm.$emit("confirm", {
      matchedRom: body().props("results")[0],
      cover: undefined,
    });
    await flushPromises();
  };
  return { wrapper, emitter, search, body, confirm };
}

describe("matching captured language event flow", () => {
  const mounted: ReturnType<typeof mountDialog>[] = [];
  beforeEach(() => {
    vi.clearAllMocks();
    dialogMocks.locale.value = "de";
    dialogMocks.searchRom.mockResolvedValue({ data: [matched] });
    dialogMocks.searchPcMetadataCandidates.mockResolvedValue({
      expectedVersion: version,
      candidates: [pcCandidate],
    });
    dialogMocks.searchPcComponentMetadataCandidates.mockResolvedValue({
      expectedVersion: version,
      candidates: [pcCandidate],
    });
    dialogMocks.selectPcMetadataCandidate.mockResolvedValue({});
    dialogMocks.selectPcComponentMetadataCandidate.mockResolvedValue({});
    dialogMocks.updateRom.mockResolvedValue({ data: target });
  });
  afterEach(() => {
    mounted.splice(0).forEach(({ wrapper }) => wrapper.unmount());
  });
  function setup() {
    const result = mountDialog();
    mounted.push(result);
    return result;
  }

  it.each(["de", "fr", "en"])(
    "captures %s search and confirmation without copying display text into a draft",
    async (locale) => {
      const ui = setup();
      dialogMocks.locale.value = locale;
      ui.emitter.emit("showMatchRomDialog", target);
      await ui.search();
      expect(dialogMocks.searchRom).toHaveBeenCalledWith(
        expect.objectContaining({ metadataLocale: locale }),
      );
      dialogMocks.locale.value = "fr-CH";
      await ui.confirm();
      expect(dialogMocks.updateRom).toHaveBeenCalledWith(
        expect.objectContaining({
          metadataLocale: locale,
          expectedVersion: version,
        }),
      );
      const submitted = dialogMocks.updateRom.mock.calls[0][0].rom;
      expect(submitted.manual_metadata).toBeNull();
      expect(submitted.summary).not.toBe("Untrusted fallback");
      expect(dialogMocks.update).toHaveBeenCalledWith(target);
      expect(target.manual_metadata?.descriptions?.en).toBe("Saved English");
    },
  );

  it.each(["rom", "component"] as const)(
    "captures PC %s search and selection language and version",
    async (kind) => {
      const ui = setup();
      const refresh = vi.fn();
      ui.emitter.emit("showPcMatchRomDialog", {
        target:
          kind === "rom"
            ? { kind, romId: 41, label: "Game" }
            : {
                kind,
                romId: 41,
                componentId: 7,
                componentKind: "dlc",
                label: "Game",
              },
        refresh,
      });
      await ui.search();
      const search =
        kind === "rom"
          ? dialogMocks.searchPcMetadataCandidates
          : dialogMocks.searchPcComponentMetadataCandidates;
      expect(search).toHaveBeenCalledWith(
        expect.objectContaining({ metadataLocale: "de" }),
      );
      dialogMocks.locale.value = "fr";
      await ui.confirm();
      const select =
        kind === "rom"
          ? dialogMocks.selectPcMetadataCandidate
          : dialogMocks.selectPcComponentMetadataCandidate;
      expect(select).toHaveBeenCalledWith(
        expect.objectContaining({
          selection: expect.objectContaining({
            candidate_id: "steam:33",
            metadata_locale: "de",
            expected_version: version,
          }),
        }),
      );
      expect(refresh).toHaveBeenCalledOnce();
    },
  );

  it("invalidates a pending search when another entity opens", async () => {
    const pending = deferred<{ data: (typeof matched)[] }>();
    dialogMocks.searchRom.mockReturnValueOnce(pending.promise);
    const ui = setup();
    ui.emitter.emit("showMatchRomDialog", target);
    await ui.search();
    ui.emitter.emit("showMatchRomDialog", { ...target, id: 42 });
    pending.resolve({ data: [matched] });
    await flushPromises();
    expect(ui.body().props("results")).toEqual([]);
    expect(ui.body().props("searching")).toBe(false);
  });

  it("keeps newer candidates when an older request resolves last", async () => {
    const pending = deferred<{ data: (typeof matched)[] }>();
    dialogMocks.searchRom.mockReturnValueOnce(pending.promise);
    const ui = setup();
    ui.emitter.emit("showMatchRomDialog", target);
    await ui.search();
    ui.emitter.emit("showMatchRomDialog", { ...target, id: 42 });
    dialogMocks.locale.value = "fr";
    await ui.search();
    pending.resolve({ data: [{ ...matched, name: "Old result" }] });
    await flushPromises();
    expect(ui.body().props("results")[0].name).toBe("Game");
    await ui.confirm();
    expect(dialogMocks.updateRom).toHaveBeenCalledWith(
      expect.objectContaining({
        metadataLocale: "fr",
        rom: expect.objectContaining({ id: 42 }),
      }),
    );
  });

  it("keeps failed confirmation open for retry without false success", async () => {
    dialogMocks.updateRom.mockRejectedValueOnce(new Error("conflict"));
    const ui = setup();
    ui.emitter.emit("showMatchRomDialog", target);
    await ui.search();
    await ui.confirm();
    expect(dialogMocks.success).not.toHaveBeenCalled();
    expect(dialogMocks.error).toHaveBeenCalledOnce();
    expect(ui.body().props("results")).toHaveLength(1);
    await ui.confirm();
    expect(dialogMocks.success).toHaveBeenCalledOnce();
  });
  it("captures a fresh preference only for the next explicit search", async () => {
    const ui = setup();
    ui.emitter.emit("showMatchRomDialog", target);
    await ui.search();
    dialogMocks.locale.value = "fr";
    expect(dialogMocks.searchRom).toHaveBeenCalledTimes(1);
    await ui.search();
    expect(dialogMocks.searchRom).toHaveBeenLastCalledWith(
      expect.objectContaining({ metadataLocale: "fr" }),
    );
    await ui.confirm();
    expect(dialogMocks.updateRom).toHaveBeenCalledWith(
      expect.objectContaining({ metadataLocale: "fr" }),
    );
  });

  it("retains PC candidate query, language and selection after a failed confirmation", async () => {
    const ui = setup();
    const refresh = vi.fn();
    ui.emitter.emit("showPcMatchRomDialog", {
      target: { kind: "rom", romId: 41, label: "Game" },
      refresh,
    });
    await ui.search();
    ui.wrapper
      .findComponent({ name: "RTextField" })
      .vm.$emit("update:modelValue", "Changed input");
    dialogMocks.locale.value = "fr";
    dialogMocks.selectPcMetadataCandidate.mockRejectedValueOnce(
      new Error("conflict"),
    );
    await ui.confirm();
    expect(dialogMocks.success).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
    expect(ui.body().props("results")).toHaveLength(1);
    await ui.confirm();
    expect(dialogMocks.selectPcMetadataCandidate).toHaveBeenLastCalledWith(
      expect.objectContaining({
        selection: expect.objectContaining({
          query: "Game",
          metadata_locale: "de",
          expected_version: version,
        }),
      }),
    );
    expect(refresh).toHaveBeenCalledOnce();
  });

  it.each(["de", "fr"])(
    "renders reloaded %s provider provenance ahead of protected manual English",
    async (locale) => {
      const manual = { descriptions: { en: "Saved English" } };
      const provider = {
        text_variants: {
          [locale]: { source_language: locale, summary: "Localized provider" },
        },
      };
      const reloaded = {
        ...target,
        manual_metadata: manual,
        ss_metadata: provider,
      };
      dialogMocks.updateRom.mockResolvedValueOnce({ data: reloaded });
      const ui = setup();
      dialogMocks.locale.value = locale;
      ui.emitter.emit("showMatchRomDialog", target);
      await ui.search();
      await ui.confirm();
      const saved = dialogMocks.update.mock.calls[0][0] as typeof reloaded;
      expect(
        resolveDescription({
          manualMetadata: saved.manual_metadata,
          ssMetadata: saved.ss_metadata,
          provider: "screenscraper",
          locale,
        }),
      ).toMatchObject({
        text: "Localized provider",
        source: "screenscraper",
        resolvedLocale: locale,
        match: "exact",
      });
      expect(saved.manual_metadata.descriptions.en).toBe("Saved English");
      expect(
        resolveDescription({
          manualMetadata: {
            descriptions: {
              ...manual.descriptions,
              [locale]: "Manual preferred",
            },
          },
          ssMetadata: provider,
          provider: "screenscraper",
          locale,
        }).source,
      ).toBe("manual");
    },
  );

  it("keeps unavailable preferred text as an explicit English resolution after reload", async () => {
    const reloaded = {
      ...target,
      ss_metadata: {
        text_variants: {
          en: { source_language: "en", summary: "Provider English" },
        },
      },
    };
    dialogMocks.updateRom.mockResolvedValueOnce({ data: reloaded });
    const ui = setup();
    ui.emitter.emit("showMatchRomDialog", target);
    await ui.search();
    await ui.confirm();
    const saved = dialogMocks.update.mock.calls[0][0] as typeof reloaded;
    expect(
      resolveDescription({
        manualMetadata: saved.manual_metadata,
        ssMetadata: saved.ss_metadata,
        provider: "screenscraper",
        locale: "de",
      }),
    ).toMatchObject({
      text: "Saved English",
      source: "manual",
      resolvedLocale: "en",
      match: "english_fallback",
    });
    expect(
      dialogMocks.updateRom.mock.calls[0][0].rom.manual_metadata,
    ).toBeNull();
  });

  it("ignores confirmation completion after another entity has opened", async () => {
    const pending = deferred<{ data: SimpleRom }>();
    dialogMocks.updateRom.mockReturnValueOnce(pending.promise);
    const ui = setup();
    ui.emitter.emit("showMatchRomDialog", target);
    await ui.search();
    await ui.confirm();
    ui.emitter.emit("showMatchRomDialog", { ...target, id: 42 });
    pending.resolve({ data: target });
    await flushPromises();
    expect(dialogMocks.update).not.toHaveBeenCalled();
    expect(dialogMocks.success).not.toHaveBeenCalled();
    expect(
      ui.wrapper.findComponent({ name: "RDialog" }).props("modelValue"),
    ).toBe(true);
  });
});
