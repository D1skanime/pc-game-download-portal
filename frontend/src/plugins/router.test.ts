import { describe, expect, it } from "vitest";
import router, { parseSafeRouteId } from "./router";

describe("safe route ids", () => {
  it.each([
    ["7", 7],
    ["1", 1],
    ["0", 0],
  ])("accepts canonical decimal id %s", (value, expected) => {
    expect(parseSafeRouteId(value)).toBe(expected);
  });

  it.each(["", "-1", "1.5", "01", "1e2", "1%2F2", "abc", null, 7, undefined])(
    "rejects unsafe route id %s",
    (value) => {
      expect(parseSafeRouteId(value)).toBeNull();
    },
  );

  it("defines a named settings layout child to avoid router warnings", () => {
    expect(
      router.getRoutes().some((route) => route.name === "settings-layout"),
    ).toBe(true);
  });
});
