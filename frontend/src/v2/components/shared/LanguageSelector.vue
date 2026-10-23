<script setup lang="ts">
// LanguageSelector wraps the language store in an RSelect so it
// shares aesthetics with every other v2 select (status picker on the
// Overview tab, etc). Persists the choice via useUISettings + sets the
// vue-i18n locale.
//
// Two looks:
//   • Default — compact pill, used on Auth/Pair shells.
//   • `prefixLabel` — full-width prefix-label field, used in Settings.
import { RIcon, RSelect } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useSystemLanguage } from "@/v2/composables/useSystemLanguage";
import storeLanguage from "@/v2/data/adapters/legacy/stores/language";

defineOptions({ inheritAttrs: false });

interface Props {
  prefixLabel?: boolean;
}
withDefaults(defineProps<Props>(), { prefixLabel: false });

const { t } = useI18n();
const { languages } = storeToRefs(storeLanguage());
const { currentValue, saving } = useSystemLanguage();
const items = computed(() =>
  languages.value.map((l) => ({ value: l.value, title: l.name })),
);
</script>

<template>
  <RSelect
    v-if="prefixLabel"
    v-model="currentValue"
    :items="items"
    :loading="saving"
    prefix-label="stacked"
    hide-details
  >
    <template #prefix-label>
      <RIcon icon="mdi-translate" size="14" />
      {{ t("settings.language") }}
    </template>
  </RSelect>
  <RSelect
    v-else
    v-model="currentValue"
    :items="items"
    :loading="saving"
    density="compact"
    variant="outlined"
    hide-details
    prepend-inner-icon="mdi-translate"
    class="language-selector"
    :menu-props="{ location: 'top start' }"
  />
</template>

<style scoped>
.language-selector {
  min-width: 200px;
  max-width: 240px;
}
</style>
