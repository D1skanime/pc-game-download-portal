<script setup lang="ts">
// SettingsShell — page chrome shared by every Settings route.
//
// Two-column layout: a sticky sidebar on the left (SettingsSidebar) and
// the page content on the right (eyebrow + title + body slot). Each
// individual settings view stays tiny — it declares its metadata and
// renders its body into the default slot.
//
// At <1024px the sidebar collapses to a horizontal scrollable strip on
// top of the content (responsive logic lives inside SettingsSidebar).
import SettingsSidebar from "@/v2/components/Settings/SettingsSidebar.vue";
import { useBackgroundArt } from "@/v2/composables/useBackgroundArt";

defineOptions({ inheritAttrs: false });

defineProps<{
  title: string;
  subtitle?: string;
  eyebrow?: string;
  icon?: string;
  /**
   * When true, renders the content slot directly without the default
   * glass wrapper. Use for views that already provide their own
   * cards/tables (e.g. Administration has UsersTable/TokensTable which
   * are self-carded).
   */
  bare?: boolean;
}>();

// Settings pages share the current cover-art background from wherever
// the user came from. We don't paint over it; just no-op so a stale
// platform/ROM cover doesn't bleed through.
const setBgArt = useBackgroundArt();
setBgArt(null);
</script>

<template>
  <section class="r-v2-settings">
    <SettingsSidebar class="r-v2-settings__sidebar" />

    <div class="r-v2-settings__content">
      <div v-if="bare" class="r-v2-settings__body r-v2-settings__body--bare">
        <slot />
      </div>
      <div v-else class="r-v2-settings__body">
        <div class="r-v2-settings__panel">
          <slot />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.r-v2-settings {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 24px;
  padding: 24px var(--r-row-pad) 48px;
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
  min-height: calc(100vh - var(--r-nav-h));
}

.r-v2-settings__sidebar {
  /* Sidebar applies its own glass surface; the shell just slots it in. */
}

.r-v2-settings__content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.r-v2-settings__head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 2px;
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
  max-width: 640px;
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

/* Bare variant — content slot owns its own surfaces (settings views with
   their own section cards). The wrapper panel is dropped so the
   embedded cards don't double-nest. */
.r-v2-settings__body--bare {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

@media (max-width: 1023px) {
  .r-v2-settings {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
  }
}
</style>
