import { describe, expect, it } from "vitest";
import { ROUTES } from "@/plugins/router";
import { routeInventory } from "@/v2/router/routeInventory";
import { v2RouteComponents } from "@/v2/router/routes";

describe("v2 route inventory", () => {
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
});
