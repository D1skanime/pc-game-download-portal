import { describe, expect, it } from "vitest";
import { ROUTES } from "@/plugins/router";
import router from "@/plugins/router";
import { routeInventory } from "@/v2/router/routeInventory";
import { v2RouteComponents } from "@/v2/router/routes";

describe("v2 route inventory", () => {
  it("registers the canonical parent-owned PC DLC route", () => {
    expect(ROUTES).toHaveProperty("PC_DLC", "pc-dlc");

    const record = router.getRoutes().find((route) => route.name === "pc-dlc");
    expect(record?.path).toBe("/rom/:rom/dlc/:component");
  });

  it("classifies every public route", () => {
    expect(Object.keys(routeInventory).sort()).toEqual(
      Object.values(ROUTES).sort(),
    );
  });

  it("binds each regular view to a real v2 component", () => {
    for (const [name, outcome] of Object.entries(routeInventory)) {
      if (
        outcome.kind !== "view" ||
        ["main", "pair", "pair-device", "404"].includes(name)
      ) {
        continue;
      }
      expect(v2RouteComponents[name], name).toBeTypeOf("function");
    }
  });

  it("redirects only to declared non-removed routes", () => {
    for (const outcome of Object.values(routeInventory)) {
      if (outcome.kind !== "redirect") continue;
      expect(routeInventory[outcome.target]).toBeDefined();
      expect(routeInventory[outcome.target].kind).not.toBe("removed");
    }
  });

  it("installs a component or redirect matching every declared outcome", () => {
    const records = new Map(
      router.getRoutes().map((route) => [String(route.name), route]),
    );

    for (const [name, outcome] of Object.entries(routeInventory)) {
      const record = records.get(name);
      expect(record, name).toBeDefined();
      if (outcome.kind === "redirect") {
        expect(record?.redirect, name).toBeTruthy();
      } else {
        expect(record?.components?.default, name).toBeTruthy();
      }
    }
  });
});
