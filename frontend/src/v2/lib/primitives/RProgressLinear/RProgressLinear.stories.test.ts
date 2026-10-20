import { composeStories } from "@storybook/vue3-vite";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as stories from "./RProgressLinear.stories";

const { LiveTicker } = composeStories(stories);

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("progress demo timer ownership", () => {
  it("advances while mounted and clears its timer on unmount", async () => {
    vi.useFakeTimers();
    const interval = vi.spyOn(globalThis, "setInterval");
    const clear = vi.spyOn(globalThis, "clearInterval");
    const wrapper = mount(
      { render: () => LiveTicker() },
      { attachTo: document.body },
    );
    const timer = interval.mock.results[0].value;
    await vi.advanceTimersByTimeAsync(160);
    expect(
      wrapper.get('[role="progressbar"]').attributes("aria-valuenow"),
    ).toBe("2");
    wrapper.unmount();
    expect(clear).toHaveBeenCalledWith(timer);
    await vi.advanceTimersByTimeAsync(1000);
    expect(interval).toHaveBeenCalledTimes(1);
    expect(clear).toHaveBeenCalledWith(timer);
  });

  it("stops when a portable story canvas is removed before Vue teardown", async () => {
    vi.useFakeTimers();
    const wrapper = mount(
      { render: () => LiveTicker() },
      { attachTo: document.body },
    );
    wrapper.element.remove();
    await vi.advanceTimersByTimeAsync(80);
    expect(vi.getTimerCount()).toBe(0);
    wrapper.unmount();
  });
});
