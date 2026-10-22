<script setup lang="ts">
import { RBtn, RSelect, RTextField } from "@v2/lib";
import { getActivePinia } from "pinia";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { ManualMetadata, SteamMetadataSchema } from "@/__generated__";
import { toBrowserLocale } from "@/utils";
import { useCan } from "@/v2/composables/useCan";
import { useDescriptionEditor } from "@/v2/composables/useDescriptionEditor";
import {
  resolveDescription,
  useManualDescription,
  type DescriptionProvider,
} from "@/v2/composables/useManualDescription";
import {
  descriptionPresentation,
  type ProviderMetadata,
} from "@/v2/composables/useManualDescription/provenance";
import { normalizeLocale } from "@/v2/composables/useProviderResolution";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });
const props = withDefaults(
  defineProps<{
    romId: number;
    componentId?: number;
    expectedVersion?: string | null;
    manualMetadata?: ManualMetadata | null;
    steamMetadata?: SteamMetadataSchema | null;
    ssMetadata?: ProviderMetadata | null;
    provider: DescriptionProvider | null;
    canEdit?: boolean;
  }>(),
  {
    componentId: undefined,
    expectedVersion: null,
    manualMetadata: null,
    steamMetadata: null,
    ssMetadata: null,
  },
);
const emit = defineEmits<{
  saved: [locale: string, description: string | null];
}>();
const { t, locale, availableLocales } = useI18n();
const snackbar = useSnackbar();
const { updateRomDescription, updateComponentDescription } =
  useManualDescription();
const permission = getActivePinia()
  ? useCan("rom.edit", {
      kind: "rom",
      get id() {
        return props.romId;
      },
    })
  : null;
const canEdit = computed(() => props.canEdit ?? permission?.value ?? false);
const editor = useDescriptionEditor({
  entity: () =>
    props.componentId === undefined
      ? `rom:${props.romId}`
      : `component:${props.romId}:${props.componentId}`,
  locale: () => (typeof locale === "string" ? locale : locale.value),
  descriptions: () => props.manualMetadata?.descriptions,
  expectedVersion: () => props.expectedVersion,
});
const { selectedLocale, draft, dirty, expectedVersion, saving, cancel } =
  editor;
const localeItems = computed(() => [
  ...new Set([
    ...(availableLocales ?? []).map(normalizeLocale),
    selectedLocale.value,
  ]),
]);
const resolution = computed(() =>
  resolveDescription({
    manualMetadata: props.manualMetadata,
    steamMetadata: props.steamMetadata,
    ssMetadata: props.ssMetadata,
    provider: props.provider,
    locale: selectedLocale.value,
  }),
);
const provenance = computed(() => {
  const result = resolution.value;
  const language = typeof locale === "string" ? locale : locale.value;
  const names = new Intl.DisplayNames([toBrowserLocale(language)], {
    type: "language",
  });
  return descriptionPresentation(result, {
    source:
      result.source === "manual"
        ? t("rom.description-manual-label")
        : result.source === "steam"
          ? "Steam"
          : "ScreenScraper",
    language: result.resolvedLocale
      ? (names.of(result.resolvedLocale) ?? result.resolvedLocale)
      : "",
    requestedLanguage:
      names.of(result.requestedLocale) ?? result.requestedLocale,
  });
});
function reset() {
  if (canEdit.value && !saving.value) draft.value = "";
}
async function save() {
  if (!canEdit.value) return;
  const romId = props.romId;
  const componentId = props.componentId;
  const capture = editor.beginSave();
  if (!capture) return;
  const description = capture.draft.trim() || null;
  const payload = {
    locale: capture.locale,
    description,
    expected_version: capture.expectedVersion,
  };
  try {
    const response =
      componentId === undefined
        ? await updateRomDescription(romId, payload)
        : await updateComponentDescription(romId, componentId, payload);
    if (!editor.isCurrent(capture)) return;
    editor.finishSave(capture, response.expected_version);
    emit("saved", response.locale, response.description);
    snackbar.success(t("rom.description-saved"));
  } catch (error) {
    if (!editor.isCurrent(capture)) return;
    console.error(error);
    snackbar.error(t("rom.description-save-failed"));
  } finally {
    editor.finishSave(capture);
  }
}
</script>

<template>
  <section
    class="localized-description-editor"
    data-testid="localized-description-editor"
    :aria-label="t('rom.description-editor')"
  >
    <div class="localized-description-editor__head">
      <div>
        <h3 class="localized-description-editor__title">
          {{ t("rom.description-editor") }}
        </h3>
        <p class="localized-description-editor__source" aria-live="polite">
          {{ t(provenance.key, provenance.params) }}
        </p>
      </div>
      <RSelect
        v-model="selectedLocale"
        :items="localeItems"
        :label="t('rom.description-locale')"
        :disabled="dirty || saving"
      />
    </div>
    <RTextField
      v-model="draft"
      multiline
      :rows="5"
      :label="t('rom.description-manual-label')"
      :disabled="!canEdit || saving"
    />
    <p
      v-if="resolution.text"
      data-testid="description-preview"
      class="localized-description-editor__provider"
      :lang="resolution.resolvedLocale ?? undefined"
    >
      {{ resolution.text }}
    </p>
    <p v-else class="localized-description-editor__hint">
      {{ t("rom.description-empty") }}
    </p>
    <div class="localized-description-editor__actions">
      <RBtn variant="text" :disabled="!dirty || saving" @click="cancel">{{
        t("rom.description-cancel")
      }}</RBtn>
      <RBtn
        variant="outlined"
        :disabled="!draft || saving || !canEdit"
        @click="reset"
        >{{ t("rom.description-reset") }}</RBtn
      >
      <RBtn
        color="primary"
        :loading="saving"
        :disabled="!dirty || saving || !canEdit || !expectedVersion"
        @click="save"
        >{{ t("rom.description-save") }}</RBtn
      >
    </div>
    <p v-if="!canEdit" class="localized-description-editor__hint">
      {{ t("rom.description-read-only") }}
    </p>
  </section>
</template>

<style scoped>
.localized-description-editor {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
  padding: var(--r-space-4);
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}
.localized-description-editor__head,
.localized-description-editor__actions {
  display: flex;
  align-items: flex-start;
  gap: var(--r-space-2);
}
.localized-description-editor__head {
  justify-content: space-between;
}
.localized-description-editor__title {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
}
.localized-description-editor__source,
.localized-description-editor__provider,
.localized-description-editor__hint {
  margin: var(--r-space-1) 0 0;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
  overflow-wrap: anywhere;
}
.localized-description-editor__provider {
  padding: var(--r-space-2) var(--r-space-3);
  border-left: 2px solid var(--r-color-brand-primary);
  white-space: pre-wrap;
}
.localized-description-editor__actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}
.localized-description-editor__actions :deep(button) {
  min-height: 44px;
}
:global(html[data-bp~="xs"]) .localized-description-editor__head {
  flex-direction: column;
}
</style>
