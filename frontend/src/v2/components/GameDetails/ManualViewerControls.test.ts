import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";
import MarkdownViewer from "./MarkdownViewer.vue";
import PdfViewer from "./PdfViewer.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock("md-editor-v3", () => ({
  MdPreview: { template: "<article />" },
}));

vi.mock("vue3-pdf-app", () => ({
  default: { template: "<div />" },
}));

vi.mock("@/v2/composables/useThemeMode", () => ({
  useThemeMode: () => ({ isLight: { value: false } }),
}));

const TooltipStub = defineComponent({
  props: {
    text: { type: String, default: "" },
  },
  template: `
    <span :data-tooltip="text">
      <slot name="activator" :props="{}" />
    </span>
  `,
});

const global = {
  mocks: {
    $t: (key: string) => key,
  },
  stubs: {
    MdPreview: { template: "<article />" },
    RIcon: { template: "<i />" },
    RTooltip: TooltipStub,
    VuePdfApp: { template: "<div />" },
  },
};

type ViewerWrapper =
  | VueWrapper<InstanceType<typeof PdfViewer>>
  | VueWrapper<InstanceType<typeof MarkdownViewer>>;

function actionButton(wrapper: ViewerWrapper, label: string) {
  return wrapper.find(`[data-tooltip="${label}"] button`);
}

function mountPdf(props: Record<string, unknown> = {}) {
  return mount(PdfViewer, {
    props: {
      pdfUrl: "/manual.pdf",
      ...props,
    },
    global,
  });
}

function mountMarkdown(props: Record<string, unknown> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, text: async () => "# Manual" }),
  );
  return mount(MarkdownViewer, {
    props: {
      url: "/manual.md",
      ...props,
    },
    global,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ManualViewerControls", () => {
  it("pdf_controls_stay_visible_and_disabled_while_pending", () => {
    const viewers = [
      mountPdf({
        deletable: true,
        redownloadable: true,
        mutationDisabled: true,
      }),
      mountMarkdown({
        deletable: true,
        redownloadable: true,
        mutationDisabled: true,
      }),
    ];

    for (const viewer of viewers) {
      const redownload = actionButton(viewer, "rom.redownload");
      const remove = actionButton(viewer, "common.delete");

      expect(redownload.exists()).toBe(true);
      expect(remove.exists()).toBe(true);
      const redownloadDisabled = (redownload.element as HTMLButtonElement)
        .disabled;
      if (!redownloadDisabled) {
        const error = new Error("expected pending redownload to be disabled");
        error.stack = error.message;
        throw error;
      }
      expect((remove.element as HTMLButtonElement).disabled).toBe(true);
      expect(redownload.attributes("aria-label")).toBe("rom.redownload");
      expect(remove.attributes("aria-label")).toBe("common.delete");

      (redownload.element as HTMLButtonElement).click();
      (remove.element as HTMLButtonElement).click();
      expect(viewer.emitted("redownload")).toBeUndefined();
      expect(viewer.emitted("delete")).toBeUndefined();
    }
  });

  it("idle_controls_emit_for_both_viewers", async () => {
    const viewers = [
      mountPdf({ deletable: true, redownloadable: true }),
      mountMarkdown({ deletable: true, redownloadable: true }),
    ];

    for (const viewer of viewers) {
      await actionButton(viewer, "rom.redownload").trigger("click");
      await actionButton(viewer, "common.delete").trigger("click");
      expect(viewer.emitted("redownload")).toHaveLength(1);
      expect(viewer.emitted("delete")).toHaveLength(1);
    }
  });

  it("permission_controls_remain_absent", () => {
    const viewers = [
      mountPdf({ mutationDisabled: true }),
      mountMarkdown({ mutationDisabled: true }),
    ];

    for (const viewer of viewers) {
      expect(actionButton(viewer, "rom.redownload").exists()).toBe(false);
      expect(actionButton(viewer, "common.delete").exists()).toBe(false);
    }
  });

  it("redownload_loading_remains_independent", () => {
    const viewers = [
      mountPdf({
        deletable: true,
        redownloadable: true,
        redownloading: true,
      }),
      mountMarkdown({
        deletable: true,
        redownloadable: true,
        redownloading: true,
      }),
    ];

    for (const viewer of viewers) {
      expect(
        (actionButton(viewer, "rom.redownload").element as HTMLButtonElement)
          .disabled,
      ).toBe(true);
      expect(
        (actionButton(viewer, "common.delete").element as HTMLButtonElement)
          .disabled,
      ).toBe(false);
    }
  });
});
