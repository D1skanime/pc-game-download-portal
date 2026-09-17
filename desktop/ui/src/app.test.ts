import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  renderDesktopApp,
  type DesktopBindings,
  type ShellSnapshot,
} from "./app";

const snapshot: ShellSnapshot = {
  configuredOrigin: "https://romm.example",
  pairing: "paired",
  destinationRoot: "destination-1",
  manifestId: "manifest-opaque-1",
  jobs: [
    {
      jobId: "job-1",
      state: "LOCAL_CONFLICT",
      fileName: "setup.exe",
      completedBytes: 0,
      totalBytes: 20,
    },
  ],
};

function bindings(snapshotValue: ShellSnapshot = snapshot): DesktopBindings {
  return {
    invoke: vi.fn(async (command: string) => {
      if (command === "state_snapshot") return snapshotValue;
      return command === "choose_destination" ? "destination-1" : "job-1";
    }),
    listen: vi.fn(async () => () => undefined),
  };
}

beforeEach(() => {
  document.body.innerHTML = '<main id="app"></main>';
});

describe("desktop shell", () => {
  it("renders pairing, opaque manifest, destination and original-file progress", async () => {
    const native = bindings();
    await renderDesktopApp(document.querySelector("#app")!, native);
    expect(document.body.textContent).toContain("https://romm.example");
    expect(document.body.textContent).toContain("manifest-opaque-1");
    expect(document.body.textContent).toContain("Original file: setup.exe");
    expect(document.body.textContent).toContain("0 B of 20 B");
    expect(document.body.textContent).not.toMatch(
      /Bearer|Authorization|\/mnt|Range|ZIP|install/i,
    );
  });

  it("offers only explicit local conflict actions and waits before invoking overwrite", async () => {
    const native = bindings();
    await renderDesktopApp(document.querySelector("#app")!, native);
    const conflict = document.querySelector("[data-state='LOCAL_CONFLICT']")!;
    expect(conflict.querySelectorAll("button")).toHaveLength(3);
    expect(
      [...conflict.querySelectorAll("button")].map(
        (button) => button.textContent,
      ),
    ).toEqual(["Overwrite", "Choose another destination", "Skip"]);
    expect(native.invoke).not.toHaveBeenCalledWith(
      "select_conflict_action",
      expect.anything(),
    );
    (conflict.querySelector("button") as HTMLButtonElement).click();
    expect(native.invoke).toHaveBeenCalledWith("select_conflict_action", {
      job_id: "job-1",
      action: "overwrite",
    });
  });

  it.each([
    "AUTH_REQUIRED",
    "SOURCE_CHANGED",
    "MANIFEST_STALE",
    "DISK_FULL",
    "PERMISSION_DENIED",
    "NETWORK_ERROR",
    "CHECKSUM_FAILED",
  ])("renders actionable recovery for %s", async (state) => {
    await renderDesktopApp(
      document.querySelector("#app")!,
      bindings({ ...snapshot, jobs: [{ ...snapshot.jobs[0], state }] }),
    );
    const item = document.querySelector(`[data-state='${state}']`)!;
    expect(item.querySelector("button, a")).not.toBeNull();
    expect(item.textContent).not.toContain("Success");
  });
});
