<script setup lang="ts">
import { RBtn, RSelect, RTextField } from "@v2/lib";
import { getActivePinia } from "pinia";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { ManualMetadata, SteamMetadataSchema } from "@/__generated__";
import { useCan } from "@/v2/composables/useCan";
import {
  resolveManualDescription,
  useManualDescription,
} from "@/v2/composables/useManualDescription";
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
    fallbackDescription?: string | null;
    providerSummaryIsAuthoritative?: boolean;
    canEdit?: boolean;
  }>(),
  {
    componentId: undefined,
    expectedVersion: null,
    manualMetadata: null,
    steamMetadata: null,
    fallbackDescription: null,
    providerSummaryIsAuthoritative: true,
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
  ? useCan("rom.edit", { kind: "rom", id: props.romId })
  : null;
const canEdit = computed(() => props.canEdit ?? permission?.value ?? true);
const currentLocale = computed(() =>
  typeof locale === "string" ? locale : locale.value,
);
const selectedLocale = ref(normalizeLocale(currentLocale.value));
const draft = ref("");
const baseline = ref("");
const saving = ref(false);
const localeItems = computed(() =>
  (availableLocales ?? []).map(normalizeLocale),
);
const manualDescription = computed(() => {
  const descriptions = props.manualMetadata?.descriptions ?? {};
  const normalized = normalizeLocale(selectedLocale.value);
  const language = normalized.split("-", 1)[0];
  return descriptions[normalized] ?? descriptions[language] ?? null;
});
const providerDescription = computed(() => {
  if (!props.providerSummaryIsAuthoritative) return null;
  const variants = props.steamMetadata?.text_variants as
    Record<string, { summary?: string | null } | undefined> | null | undefined;
  if (!variants) return null;
  const normalized = normalizeLocale(selectedLocale.value);
  const language = normalized.split("-", 1)[0];
  const candidate =
    variants[normalized]?.summary ??
    variants[language]?.summary ??
    variants.en?.summary;
  return typeof candidate === "string" && candidate.trim()
    ? candidate.trim()
    : null;
});
const resolvedDescription = computed(() =>
  resolveManualDescription({
    manualMetadata: props.manualMetadata,
    steamMetadata: props.steamMetadata,
    legacySummary: props.fallbackDescription,
    locale: selectedLocale.value,
    providerSummaryIsAuthoritative: props.providerSummaryIsAuthoritative,
  }),
);
const sourceKey = computed(() => {
  if (manualDescription.value?.trim()) return "rom.description-source-manual";
  if (providerDescription.value) return "rom.description-source-provider";
  if (props.fallbackDescription?.trim())
    return "rom.description-source-fallback";
  return "rom.description-source-empty";
});
const dirty = computed(() => draft.value !== baseline.value);
function exactManualDescription() {
  const descriptions = props.manualMetadata?.descriptions ?? {};
  return descriptions[normalizeLocale(selectedLocale.value)] ?? "";
}
function syncDraft() {
  const next = exactManualDescription();
  draft.value = next;
  baseline.value = next;
}
watch(
  [selectedLocale, () => props.manualMetadata],
  () => {
    if (!dirty.value) syncDraft();
  },
  { immediate: true, deep: true },
);
watch(currentLocale, (value) => {
  const next = normalizeLocale(value);
  if (!dirty.value && localeItems.value.includes(next))
    selectedLocale.value = next;
});
function cancel() {
  draft.value = baseline.value;
}
function reset() {
  draft.value = "";
}
async function save() {
  if (!dirty.value || saving.value || !canEdit.value || !props.expectedVersion)
    return;
  saving.value = true;
  const description = draft.value.trim() || null;
  try {
    const response = props.componentId
      ? await updateComponentDescription(props.romId, props.componentId, {
          locale: selectedLocale.value,
          description,
          expected_version: props.expectedVersion,
        })
      : await updateRomDescription(props.romId, {
          locale: selectedLocale.value,
          description,
          expected_version: props.expectedVersion,
        });
    baseline.value = draft.value;
    emit("saved", response.locale, response.description);
    snackbar.success(t("rom.description-saved"));
  } catch (error) {
    console.error(error);
    snackbar.error(t("rom.description-save-failed"));
  } finally {
    saving.value = false;
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
          {{ t(sourceKey) }}
        </p>
      </div>
      <RSelect
        v-model="selectedLocale"
        :items="localeItems"
        :label="t('rom.description-locale')"
        density="compact"
        :disabled="saving"
      />
    </div>
    <RTextField
      v-model="draft"
      multiline
      :rows="5"
      :label="t('rom.description-manual-label')"
      :hint="resolvedDescription || t('rom.description-empty')"
      persistent-hint
      :disabled="!canEdit || saving"
    />
    <p
      v-if="providerDescription && !manualDescription"
      class="localized-description-editor__provider"
    >
      {{ t("rom.description-provider-preview") }} {{ providerDescription }}
    </p>
    <p
      v-else-if="
        props.fallbackDescription && !manualDescription && !providerDescription
      "
      class="localized-description-editor__provider"
    >
      {{ t("rom.description-fallback-preview") }}
      {{ props.fallbackDescription }}
    </p>
    <div class="localized-description-editor__actions">
      <RBtn variant="text" :disabled="!dirty || saving" @click="cancel">{{
        t("rom.description-cancel")
      }}</RBtn>
      <RBtn
        variant="outlined"
        :disabled="!dirty || saving || !canEdit"
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
  gap: var(--r-space-3);
  padding: var(--r-space-4);
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}
.localized-description-editor__head,
.localized-description-editor__actions {
  display: flex;
  align-items: flex-start;
  gap: var(--r-space-3);
}
.localized-description-editor__head {
  justify-content: space-between;
}
.localized-description-editor__title {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
}
.localized-description-editor__source,
.localized-description-editor__provider,
.localized-description-editor__hint {
  margin: var(--r-space-1) 0 0;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
}
.localized-description-editor__provider {
  padding: var(--r-space-2) var(--r-space-3);
  border-left: 2px solid var(--r-color-brand-primary);
}
.localized-description-editor__actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}
@media (max-width: 599px) {
  .localized-description-editor__head {
    flex-direction: column;
  }
}
</style>
