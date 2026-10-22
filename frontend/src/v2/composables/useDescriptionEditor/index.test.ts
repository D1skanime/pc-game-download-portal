import { describe, expect, it } from "vitest";
import { effectScope, reactive } from "vue";
import { useDescriptionEditor } from "./index";

function setup() {
  const input = reactive({
    entity: "rom:41",
    locale: "de_DE",
    descriptions: { "de-DE": "Exact", de: "Base", en: "English" } as Record<
      string,
      string
    >,
    version: "v1",
  });
  const scope = effectScope();
  const editor = scope.run(() =>
    useDescriptionEditor({
      entity: () => input.entity,
      locale: () => input.locale,
      descriptions: () => input.descriptions,
      expectedVersion: () => input.version,
    }),
  )!;
  return { input, editor, scope };
}
describe("exact locale draft ownership", () => {
  it("uses only normalized exact manual key, never base or English fallback", () => {
    const { input, editor, scope } = setup();
    expect(editor.draft.value).toBe("Exact");
    editor.selectedLocale.value = "fr_FR";
    expect(editor.draft.value).toBe("");
    expect(input.descriptions.en).toBe("English");
    scope.stop();
  });
  it("blocks dirty locale changes and preserves baseline version on refresh", () => {
    const { input, editor, scope } = setup();
    editor.draft.value = "Unsaved";
    editor.selectedLocale.value = "fr-FR";
    input.locale = "en_US";
    input.descriptions = { "de-DE": "Refreshed" };
    input.version = "v2";
    expect(editor.selectedLocale.value).toBe("de-DE");
    expect(editor.draft.value).toBe("Unsaved");
    expect(editor.expectedVersion.value).toBe("v1");
    editor.cancel();
    expect(editor.draft.value).toBe("Exact");
    scope.stop();
  });
  it("resets draft ownership on entity change even when dirty", () => {
    const { input, editor, scope } = setup();
    editor.draft.value = "Other entity draft";
    input.entity = "component:41:7";
    expect(editor.draft.value).toBe("Exact");
    expect(editor.dirty.value).toBe(false);
    scope.stop();
  });
});

describe("captured save ownership", () => {
  it("captures locale and version, blocks concurrent saves and keeps a failed draft", () => {
    const { input, editor, scope } = setup();
    editor.draft.value = "Unsaved";
    input.version = "v2";
    expect(editor.expectedVersion.value).toBe("v1");
    const save = editor.beginSave()!;
    expect(save).toMatchObject({
      entity: "rom:41",
      locale: "de-DE",
      draft: "Unsaved",
      expectedVersion: "v1",
    });
    expect(editor.beginSave()).toBeNull();
    editor.cancel();
    editor.selectedLocale.value = "en";
    expect(editor.draft.value).toBe("Unsaved");
    expect(editor.selectedLocale.value).toBe("de-DE");
    expect(editor.finishSave(save)).toBe(true);
    expect(editor.dirty.value).toBe(true);
    expect(editor.draft.value).toBe("Unsaved");
    scope.stop();
  });
  it("ignores old entity responses and does not clear a newer save", () => {
    const { input, editor, scope } = setup();
    editor.draft.value = "Old";
    const old = editor.beginSave()!;
    input.entity = "rom:42";
    editor.draft.value = "New";
    const current = editor.beginSave()!;
    expect(editor.finishSave(old, "old-result")).toBe(false);
    expect(editor.saving.value).toBe(true);
    expect(editor.draft.value).toBe("New");
    expect(editor.finishSave(current, "v3")).toBe(true);
    expect(editor.dirty.value).toBe(false);
    expect(editor.expectedVersion.value).toBe("v3");
    expect(editor.finishSave(current, "v4")).toBe(false);
    scope.stop();
  });
  it("invalidates responses after disposal and allows clean normalized locale changes", () => {
    const { editor, scope } = setup();
    editor.selectedLocale.value = "en_US";
    expect(editor.selectedLocale.value).toBe("en-US");
    expect(editor.draft.value).toBe("");
    editor.draft.value = "New";
    const save = editor.beginSave()!;
    scope.stop();
    expect(editor.isCurrent(save)).toBe(false);
  });
});
