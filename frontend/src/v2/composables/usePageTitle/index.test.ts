import { afterEach, describe, expect, it } from "vitest";
import { effectScope, nextTick, ref } from "vue";
import { usePageTitle } from "./index";

describe("reactive page title", () => {
  const scopes: ReturnType<typeof effectScope>[] = [];
  afterEach(() => scopes.splice(0).forEach((scope) => scope.stop()));

  it.each([null, undefined, ""])("defaults %s to the product name", (value) => {
    const scope = effectScope();
    scopes.push(scope);
    scope.run(() => usePageTitle(() => value));
    expect(document.title).toBe("ZockArchive");
  });

  it("updates meaningful titles and the fallback", async () => {
    const title = ref<string | null>("First game");
    const scope = effectScope();
    scopes.push(scope);
    scope.run(() => usePageTitle(() => title.value));
    expect(document.title).toBe("First game");
    title.value = "Second game";
    await nextTick();
    expect(document.title).toBe("Second game");
    title.value = null;
    await nextTick();
    expect(document.title).toBe("ZockArchive");
  });

  it("keeps the next route title on unmount", () => {
    const scope = effectScope();
    scope.run(() => usePageTitle(() => "Game"));
    document.title = "Library";
    scope.stop();
    expect(document.title).toBe("Library");
  });
});
