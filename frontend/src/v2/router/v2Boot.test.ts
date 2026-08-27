import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const bootModules = import.meta.glob([
  "../../RomM.vue",
  "../../plugins/router.ts",
  "../../stores/auth.ts",
  "../../stores/config.ts",
  "../../stores/heartbeat.ts",
  "../../stores/language.ts",
  "../../stores/roms.ts",
  "../../services/api/rom.ts",
  "../../services/api/user.ts",
  "../layouts/AppLayout.vue",
  "../layouts/AuthLayout.vue",
  "../layouts/SettingsLayout.vue",
  "../views/PairDispatcher.vue",
  "../views/DevicePair.vue",
  "../components/Dialogs/GlobalDialogs.vue",
  "../components/Notifications/NotificationHost.vue",
]);

const generatedTypes = import.meta.glob("../../__generated__/**/*.ts");

describe("v2-only boot graph", () => {
  it("keeps every required boot dependency importable", () => {
    expect(Object.keys(bootModules)).toHaveLength(16);
    expect(
      Object.values(bootModules).every(
        (loader) => typeof loader === "function",
      ),
    ).toBe(true);
    expect(Object.keys(generatedTypes).length).toBeGreaterThan(0);
  });

  it("has no frozen source trees", () => {
    for (const directory of ["components", "views", "layouts", "console"]) {
      const path = resolve(process.cwd(), "src", directory);
      const files = existsSync(path)
        ? readdirSync(path, { recursive: true, withFileTypes: true }).filter(
            (entry) => entry.isFile(),
          )
        : [];
      expect(files, directory).toHaveLength(0);
    }
  });

  it("boots one default v2 router view without compatibility fallbacks", () => {
    const root = readFileSync(resolve(process.cwd(), "src/RomM.vue"), "utf8");
    const router = readFileSync(
      resolve(process.cwd(), "src/plugins/router.ts"),
      "utf8",
    );
    const registry = readFileSync(
      resolve(process.cwd(), "src/v2/router/routes.ts"),
      "utf8",
    );

    expect(root).toContain("<router-view />");
    expect(root).not.toContain('name="v2"');
    expect(router).not.toContain("components:");
    expect(registry).not.toContain("fallbackComponent");
    expect(registry).not.toContain("NotReady");
  });
});
