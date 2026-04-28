<script setup lang="ts">
// SettingsShell — page chrome shared by all 7 Settings routes. Emits:
// • a v2 hero (eyebrow + title + optional subtitle),
// • the SettingsNav pill strip,
// • a glass container that hosts the page's content via the default slot.
//
// Keeps each individual settings view tiny — it only declares its metadata
// and drops its body into the default slot.
import { RIcon } from "@v2/lib";
import SettingsNav from "@/v2/components/Settings/SettingsNav.vue";
import { useBackgroundArt } from "@/v2/composables/useBackgroundArt";

defineOptions({ inheritAttrs: false });

defineProps<{
  title: string;
  subtitle?: string;
  eyebrow?: string;
  icon?: string;
  /**
   * When true, renders the content slot directly without the default glass
   * wrapper. Use for views that already provide their own cards/tables
   * (e.g. Administration has UsersTable/TokensTable which are self-carded).
   */
  bare?: boolean;
}>();

// Settings pages share the current cover art background from wherever the
// user was last, which is fine — just a no-op here to avoid stale art.
const setBgArt = useBackgroundArt();
setBgArt(null);
</script>

<template>
  <section class="r-v2-settings">
    <header class="r-v2-settings__head">
      <div class="r-v2-settings__title-block">
        <span class="r-v2-settings__eyebrow">
          <RIcon v-if="icon" :icon="icon" size="13" />
          {{ eyebrow ?? "Settings" }}
        </span>
        <h1 class="r-v2-settings__title">
          {{ title }}
        </h1>
        <p v-if="subtitle" class="r-v2-settings__subtitle">
          {{ subtitle }}
        </p>
      </div>
    </header>

    <SettingsNav />

    <div v-if="bare" class="r-v2-settings__body r-v2-settings__body--bare">
      <slot />
    </div>
    <div v-else class="r-v2-settings__body">
      <div class="r-v2-settings__panel">
        <slot />
      </div>
    </div>
  </section>
</template>

<style scoped>
.r-v2-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px var(--r-row-pad) 48px;
  max-width: 1120px;
  margin: 0 auto;
  width: 100%;
  min-height: calc(100vh - var(--r-nav-h));
}

.r-v2-settings__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.r-v2-settings__title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.r-v2-settings__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 10px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-brand-primary);
}

.r-v2-settings__title {
  margin: 0;
  font-size: var(--r-font-size-xl);
  font-weight: var(--r-font-weight-bold);
}

.r-v2-settings__subtitle {
  margin: 2px 0 0;
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-sm);
  max-width: 560px;
}

.r-v2-settings__body {
  display: flex;
  flex-direction: column;
}

.r-v2-settings__panel {
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  padding: 18px;
}

/* Bare variant — content slot owns its own surfaces (e.g. v1 RSection
   cards for tables). We strip the wrapper panel so the embedded cards
   don't double-nest. */
.r-v2-settings__body--bare {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
