import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import OperationStatusPanel from "./OperationStatusPanel.vue";

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("@v2/lib", () => ({
  RAlert: { template: "<div><slot /></div>" },
  RProgressLinear: { template: "<div />" },
  RCheckbox: { template: "<input type=checkbox />" },
  RBtn: { template: "<button><slot /></button>" },
}));

const mounted: ReturnType<typeof mount>[] = [];
afterEach(() => {
  mounted.forEach((wrapper) => wrapper.unmount());
  mounted.length = 0;
  document.body.replaceChildren();
});
function render() {
  const wrapper = mount(OperationStatusPanel, {
    attachTo: document.body,
    props: {
      snapshot: null,
      checking: false,
      uncertain: true,
      disconnected: false,
      reconciling: false,
      actionError: null,
      status: "idle",
      canManage: false,
    },
    global: { stubs: { RBtn: false } },
  });
  mounted.push(wrapper);
  return wrapper;
}

describe("Phase 35 status-control focus", () => {
  it("restores focus to its status heading when a focused recovery control disappears", async () => {
    const wrapper = render();
    const retry = wrapper.get("button").element as HTMLButtonElement;
    retry.focus();
    expect(document.activeElement).toBe(retry);
    await wrapper.setProps({ uncertain: false });
    expect(wrapper.find("button").exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.get("h2").element);
  });

  it("retains focus intent across a pending disabled recovery control", async () => {
    const wrapper = render();
    const retry = wrapper.get("button").element as HTMLButtonElement;
    retry.focus();
    expect(document.activeElement).toBe(retry);
    await wrapper.setProps({ checking: true });
    expect(retry.disabled).toBe(true);
    // Chromium blurs a focused button when native disabled is applied.
    document.body.tabIndex = -1;
    document.body.focus();
    document.body.removeAttribute("tabindex");
    expect(document.activeElement).toBe(document.body);
    await wrapper.setProps({ checking: false, uncertain: false });
    expect(document.activeElement).toBe(wrapper.get("h2").element);
  });

  it("preserves focus outside the panel when recovery finishes", async () => {
    const wrapper = render();
    const input = document.createElement("input");
    document.body.append(input);
    input.focus();
    await wrapper.setProps({ uncertain: false });
    expect(document.activeElement).toBe(input);
  });
});
