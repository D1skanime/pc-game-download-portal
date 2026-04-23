<script setup lang="ts">
// UserInterface — v2-native. The `UIVersion` toggle is the load-bearing
// primitive: users need a reliable way to flip between v1 and v2 while the
// v2 UI is still in beta. Language uses the shared v2 LanguageSelector;
// Theme renders three compact cards; the advanced interface flags are
// deferred to the v1 Interface component embedded in a glass panel — those
// toggles are already functional and a deep rebuild is a separate effort.
import { RIcon } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import V1Interface from "@/components/Settings/UserInterface/Interface.vue";
import { useUISettings } from "@/composables/useUISettings";
import { useUiVersion } from "@/composables/useUiVersion";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";
import LanguageSelector from "@/v2/components/shared/LanguageSelector.vue";

const { t } = useI18n();
const uiVersion = useUiVersion();
const { theme: selectedTheme } = useUISettings();

type Theme = "dark" | "light" | "auto";
const themeOptions: { value: Theme; label: string; icon: string }[] = [
  { value: "dark", label: "Dark", icon: "mdi-moon-waning-crescent" },
  { value: "light", label: "Light", icon: "mdi-white-balance-sunny" },
  { value: "auto", label: "Auto", icon: "mdi-theme-light-dark" },
];

function setTheme(value: Theme) {
  selectedTheme.value = value;
}

function setVersion(value: "v1" | "v2") {
  uiVersion.value = value;
}

const uiVersionCards = computed(() => [
  {
    value: "v1" as const,
    title: t("settings.ui-version-classic", "Classic UI"),
    icon: "mdi-star-outline",
    blurb: "The familiar RomM interface.",
  },
  {
    value: "v2" as const,
    title: t("settings.ui-version-new", "New UI (beta)"),
    icon: "mdi-star-four-points",
    blurb: "The new design language — switch is instant.",
  },
]);
</script>

<template>
  <SettingsShell
    :title="t('common.user-interface')"
    :subtitle="
      t('settings.ui-subtitle', 'Theme, language, and home layout preferences.')
    "
    eyebrow="Settings"
    icon="mdi-palette"
    bare
  >
    <!-- UI version -->
    <section class="r-v2-ui__section">
      <header class="r-v2-ui__section-head">
        <RIcon icon="mdi-new-box" size="16" />
        <h2>{{ t("settings.ui-version", "UI version") }}</h2>
      </header>
      <p class="r-v2-ui__desc">
        {{
          t(
            "settings.ui-version-desc",
            "Preview the new RomM UI (beta). Switching is instant and you can flip back at any time.",
          )
        }}
      </p>
      <div class="r-v2-ui__version-grid">
        <button
          v-for="card in uiVersionCards"
          :key="card.value"
          type="button"
          class="r-v2-ui__version-card"
          :class="{
            'r-v2-ui__version-card--active': uiVersion === card.value,
          }"
          :aria-pressed="uiVersion === card.value"
          @click="setVersion(card.value)"
        >
          <RIcon :icon="card.icon" size="26" />
          <span class="r-v2-ui__version-title">{{ card.title }}</span>
          <span class="r-v2-ui__version-blurb">{{ card.blurb }}</span>
          <span v-if="uiVersion === card.value" class="r-v2-ui__version-dot">
            <RIcon icon="mdi-check" size="12" />
          </span>
        </button>
      </div>
    </section>

    <!-- Language -->
    <section class="r-v2-ui__section">
      <header class="r-v2-ui__section-head">
        <RIcon icon="mdi-translate" size="16" />
        <h2>{{ t("settings.language") }}</h2>
      </header>
      <LanguageSelector />
    </section>

    <!-- Theme -->
    <section class="r-v2-ui__section">
      <header class="r-v2-ui__section-head">
        <RIcon icon="mdi-brush-variant" size="16" />
        <h2>{{ t("settings.theme") }}</h2>
      </header>
      <div class="r-v2-ui__theme-grid">
        <button
          v-for="opt in themeOptions"
          :key="opt.value"
          type="button"
          class="r-v2-ui__theme-card"
          :class="{
            'r-v2-ui__theme-card--active': selectedTheme === opt.value,
          }"
          :aria-pressed="selectedTheme === opt.value"
          @click="setTheme(opt.value)"
        >
          <RIcon :icon="opt.icon" size="22" />
          <span>{{ opt.label }}</span>
        </button>
      </div>
    </section>

    <!-- Advanced interface toggles — reuses the v1 component for now. -->
    <section class="r-v2-ui__section r-v2-ui__section--legacy">
      <header class="r-v2-ui__section-head">
        <RIcon icon="mdi-tune" size="16" />
        <h2>{{ t("settings.home-layout", "Home layout") }}</h2>
      </header>
      <V1Interface />
    </section>
  </SettingsShell>
</template>

<style scoped>
.r-v2-ui__section {
  background: rgba(13, 17, 23, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.r-v2-ui__section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.7);
}
.r-v2-ui__section-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: var(--r-font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(255, 255, 255, 0.85);
}

.r-v2-ui__desc {
  margin: 0;
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  line-height: 1.5;
  max-width: 640px;
}

.r-v2-ui__version-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.r-v2-ui__version-card,
.r-v2-ui__theme-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--r-radius-md);
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  text-align: left;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    transform var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-ui__version-card:hover,
.r-v2-ui__theme-card:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.14);
  transform: translateY(-1px);
}
.r-v2-ui__version-card--active,
.r-v2-ui__theme-card--active {
  background: rgba(139, 116, 232, 0.14);
  border-color: rgba(139, 116, 232, 0.45);
  color: #fff;
}

.r-v2-ui__version-title {
  font-size: 14px;
  font-weight: var(--r-font-weight-semibold);
}
.r-v2-ui__version-blurb {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.r-v2-ui__version-dot {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--r-color-brand-primary);
  color: #0d1117;
  display: grid;
  place-items: center;
  font-weight: var(--r-font-weight-bold);
}

.r-v2-ui__theme-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.r-v2-ui__theme-card {
  flex-direction: row;
  gap: 10px;
  align-items: center;
}

.r-v2-ui__section--legacy :deep(.v-card) {
  background: transparent !important;
}
.r-v2-ui__section--legacy :deep(.v-card-title) {
  display: none;
}

@media (max-width: 720px) {
  .r-v2-ui__version-grid {
    grid-template-columns: 1fr;
  }
  .r-v2-ui__theme-grid {
    grid-template-columns: 1fr;
  }
}
</style>
