<script setup lang="ts">
// SettingsShell — page chrome shared by every Settings route.
//
// Mock-faithful layout: full viewport height, two columns sharing a
// vertical hairline divider. The sidebar stays put; the content column
// owns its own scroll so the page title (when present) and the navbar
// don't shift on scroll. The sidebar's active item is the navigation
// cue, so each view skips a redundant title hero.
//
// At <1024px the sidebar collapses to a horizontal scrollable strip on
// top of the content (responsive logic lives inside SettingsSidebar).
import SettingsSidebar from "@/v2/components/Settings/SettingsSidebar.vue";
import { useBackgroundArt } from "@/v2/composables/useBackgroundArt";

defineOptions({ inheritAttrs: false });

defineProps<{
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
  display: flex;
  height: calc(100vh - var(--r-nav-h));
  overflow: hidden;
  width: 100%;
}

.r-v2-settings__sidebar {
  width: 220px;
  flex-shrink: 0;
}

.r-v2-settings__content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 32px 40px 60px;
  scrollbar-width: thin;
  scrollbar-color: var(--r-color-border-strong) transparent;
}
.r-v2-settings__content::-webkit-scrollbar {
  width: 4px;
}
.r-v2-settings__content::-webkit-scrollbar-thumb {
  background: var(--r-color-border-strong);
  border-radius: 2px;
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

/* Bare variant — content slot owns its own surfaces (settings views
   with their own section cards). The wrapper panel is dropped so the
   embedded cards don't double-nest. */
.r-v2-settings__body--bare {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 1023px) {
  .r-v2-settings {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - var(--r-nav-h));
    overflow: visible;
  }
  .r-v2-settings__sidebar {
    width: 100%;
  }
  .r-v2-settings__content {
    overflow: visible;
    padding: 24px var(--r-row-pad) 48px;
  }
}
</style>
