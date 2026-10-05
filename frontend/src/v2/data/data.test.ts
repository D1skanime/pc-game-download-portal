import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import {
  createCatalogRepository,
  createRepository,
  throwIfAborted,
} from "./index";

describe("v2 data boundary", () => {
  it("normalizes legacy failures without changing repository callers", async () => {
    const repository = createRepository(async () => {
      throw { response: { status: 409, data: { detail: "stale" } } };
    });
    await expect(repository.query(undefined)).rejects.toMatchObject({
      message: "stale",
      status: 409,
    });
  });

  it("stops before invoking a legacy query when aborted", async () => {
    const query = vi.fn();
    const controller = new AbortController();
    controller.abort();
    const repository = createRepository(query);

    await expect(
      repository.query(undefined, { signal: controller.signal }),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(query).not.toHaveBeenCalled();
  });

  it("keeps invalidation explicit for catalog adapters", async () => {
    const invalidate = vi.fn();
    const repository = createCatalogRepository(
      async () => ({ items: [], total: 0, page: 1, pageSize: 20 }),
      invalidate,
    );

    await expect(repository.query({})).resolves.toEqual({
      items: [],
      total: 0,
      page: 1,
      pageSize: 20,
    });
    repository.invalidate();
    expect(invalidate).toHaveBeenCalledOnce();
  });

  it("exports an abort helper for boundary implementations", () => {
    expect(() => throwIfAborted()).not.toThrow();
  });

  it("keeps legacy imports out of the v2 data boundary", () => {
    const dataRoot = resolve(process.cwd(), "src/v2/data");
    const files = readdirSync(dataRoot, {
      recursive: true,
      withFileTypes: true,
    })
      .filter((entry) => entry.isFile() && /\.(ts|tsx)$/.test(entry.name))
      .map((entry) => resolve(entry.parentPath, entry.name));
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      expect(source, file).not.toMatch(/@\/(stores|services)\//);
    }
  });
});
