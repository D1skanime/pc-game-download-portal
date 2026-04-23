<script setup lang="ts">
// LanguageSelector — glass-pill activator that opens an RMenu with the
// language list. Uses lib menu primitives end-to-end so the dropdown
// matches the look of the user menu and right-click context menu.
//
// Sets the vue-i18n locale and persists the choice via useUISettings.
import { RIcon, RMenu, RMenuItem, RMenuPanel } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useUISettings } from "@/composables/useUISettings";
import storeLanguage from "@/stores/language";

defineOptions({ inheritAttrs: false });

const { locale } = useI18n();
const languageStore = storeLanguage();
const { languages, selectedLanguage } = storeToRefs(languageStore);
const { locale: localeStorage } = useUISettings();

const open = ref(false);

const currentValue = computed(() => selectedLanguage.value.value);

function select(lang: { value: string; name: string }) {
  selectedLanguage.value = lang;
  locale.value = lang.value;
  localeStorage.value = lang.value;
  open.value = false;
}
</script>

<template>
  <RMenu v-model="open" location="top start" :offset="[8, 0]">
    <template #activator="{ props: activatorProps }">
      <button
        v-bind="activatorProps"
        type="button"
        class="lang-pill"
        :aria-label="`Language: ${selectedLanguage.name}`"
      >
        <RIcon icon="mdi-translate" size="14" class="lang-pill__leading" />
        <span class="lang-pill__name">{{ selectedLanguage.name }}</span>
        <RIcon
          icon="mdi-chevron-up"
          size="14"
          class="lang-pill__chevron"
          :class="{ 'lang-pill__chevron--open': open }"
        />
      </button>
    </template>

    <RMenuPanel width="220px">
      <RMenuItem
        v-for="lang in languages"
        :key="lang.value"
        :label="lang.name"
        :variant="lang.value === currentValue ? 'active' : 'default'"
        @click="select(lang)"
      />
    </RMenuPanel>
  </RMenu>
</template>

<style scoped>
.lang-pill {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--r-radius-pill);
  padding: 5px 10px 5px 12px;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  font-weight: var(--r-font-weight-medium);
  color: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}

.lang-pill:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}

:global(.r-v2.r-v2-light) .lang-pill {
  background: rgba(17, 17, 23, 0.06);
  border-color: rgba(17, 17, 23, 0.12);
  color: rgba(17, 17, 23, 0.85);
}
:global(.r-v2.r-v2-light) .lang-pill:hover {
  background: rgba(17, 17, 23, 0.1);
  color: var(--r-color-fg);
}

.lang-pill__leading {
  opacity: 0.7;
}

.lang-pill__name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.lang-pill__chevron {
  opacity: 0.55;
  transition: transform var(--r-motion-fast) var(--r-motion-ease-out);
}
.lang-pill__chevron--open {
  transform: rotate(180deg);
}
</style>
