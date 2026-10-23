import { computed, onScopeDispose, ref, watch } from "vue";
import { normalizeLocale } from "@/v2/composables/useProviderResolution";

interface DescriptionEditorInput {
  entity: () => string;
  locale: () => string;
  descriptions: () => Record<string, string> | null | undefined;
  expectedVersion: () => string | null | undefined;
}
interface DescriptionSave {
  generation: number;
  entity: string;
  locale: string;
  draft: string;
  expectedVersion: string;
}

export function useDescriptionEditor(input: DescriptionEditorInput) {
  const ownedLocale = ref(normalizeLocale(input.locale()));
  const draft = ref("");
  const baseline = ref("");
  const expectedVersion = ref<string | null>(null);
  const saving = ref(false);
  const dirty = computed(() => draft.value !== baseline.value);
  let generation = 0;
  let pending: DescriptionSave | null = null;

  function syncDraft() {
    const value = input.descriptions()?.[ownedLocale.value] ?? "";
    baseline.value = value;
    draft.value = value;
    expectedVersion.value = input.expectedVersion() ?? null;
  }
  const selectedLocale = computed({
    get: () => ownedLocale.value,
    set(value: string) {
      if (dirty.value || saving.value) return;
      ownedLocale.value = normalizeLocale(value);
      syncDraft();
    },
  });
  watch(
    input.entity,
    () => {
      generation++;
      pending = null;
      saving.value = false;
      ownedLocale.value = normalizeLocale(input.locale());
      syncDraft();
    },
    { immediate: true, flush: "sync" },
  );
  watch(
    [input.descriptions, input.expectedVersion],
    () => {
      if (!dirty.value && !saving.value) syncDraft();
    },
    { deep: true, flush: "sync" },
  );
  watch(
    input.locale,
    (value) => {
      selectedLocale.value = value;
    },
    { flush: "sync" },
  );
  onScopeDispose(() => {
    generation++;
    pending = null;
  });

  function cancel() {
    if (!saving.value) draft.value = baseline.value;
  }
  function beginSave(): DescriptionSave | null {
    if (!dirty.value || saving.value || !expectedVersion.value) return null;
    pending = {
      generation,
      entity: input.entity(),
      locale: ownedLocale.value,
      draft: draft.value,
      expectedVersion: expectedVersion.value,
    };
    saving.value = true;
    return pending;
  }
  function isCurrent(save: DescriptionSave) {
    return (
      pending === save &&
      save.generation === generation &&
      save.entity === input.entity()
    );
  }
  function finishSave(save: DescriptionSave, version?: string | null) {
    if (!isCurrent(save)) return false;
    if (version) {
      baseline.value = save.draft;
      expectedVersion.value = version;
    }
    pending = null;
    saving.value = false;
    return true;
  }
  return {
    selectedLocale,
    draft,
    dirty,
    expectedVersion,
    saving,
    cancel,
    beginSave,
    isCurrent,
    finishSave,
  };
}
