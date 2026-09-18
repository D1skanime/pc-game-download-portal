import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import DownloadManager from "./DownloadManager.vue";

describe("DownloadManager", () => {
  it("does not offer enhanced mode when directory access is unavailable", () => {
    const wrapper = mount(DownloadManager, {
      props: { items: [] },
    });
    expect(wrapper.text()).not.toContain("Enhanced folder download");
  });
});
