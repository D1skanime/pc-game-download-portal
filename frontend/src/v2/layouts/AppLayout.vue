<script setup lang="ts">
// AppLayout — top-level v2 shell. Thin orchestrator: owns the background-art
// provider and mounts the visual chrome.
//
//   * BackgroundArt — two-layer blurred backdrop with cross-fade
//   * AppNav        — logo · centred tab pill · user menu
//   * GlobalDialogs — emitter-driven dialog + notification stack
//
// Per-ROM action menus are not app-wide: each GameCard owns its own
// `MoreMenu` dropdown on the three-dots button. Right-click is left to
// the browser so "Open in new tab" etc. keep working.
import { onBeforeUnmount, onMounted, provide, ref } from "vue";
import { useRouter } from "vue-router";
import AppNav from "@/v2/components/AppShell/AppNav.vue";
import BackgroundArt from "@/v2/components/AppShell/BackgroundArt.vue";
import GlobalDialogs from "@/v2/components/AppShell/GlobalDialogs.vue";
import { BACKGROUND_ART_KEY } from "@/v2/composables/useBackgroundArt";
import { useGamepad } from "@/v2/composables/useGamepad";
import { useGlobalHotkeys } from "@/v2/composables/useGlobalHotkeys";
import { useInputModality } from "@/v2/composables/useInputModality";
import { useThemeClass } from "@/v2/composables/useThemeClass";
import { installBackMorph } from "@/v2/composables/useViewTransition";

const themeClass = useThemeClass();

// Shared reactive background art — views paint covers via the injected setter.
const layerA = ref<string | null>(null);
const layerB = ref<string | null>(null);
const activeLayer = ref<"a" | "b">("a");

function setBackgroundArt(url: string | null) {
  if (activeLayer.value === "a") {
    if (layerA.value === url) return;
    layerB.value = url;
    activeLayer.value = "b";
  } else {
    if (layerB.value === url) return;
    layerA.value = url;
    activeLayer.value = "a";
  }
}
provide(BACKGROUND_ART_KEY, setBackgroundArt);

const { install: installInputModality } = useInputModality();
const { install: installGamepad } = useGamepad();
const { install: installGlobalHotkeys } = useGlobalHotkeys();
const router = useRouter();

let removeBackMorph: (() => void) | null = null;

onMounted(() => {
  installInputModality();
  installGamepad();
  installGlobalHotkeys();
  // Mirror morph: GameDetails cover → destination card on back/navbar/popstate.
  // Forward direction is handled at the source side in GameCard.
  removeBackMorph = installBackMorph(router);
});

onBeforeUnmount(() => {
  removeBackMorph?.();
  removeBackMorph = null;
});
</script>

<template>
  <div class="r-v2 r-v2-shell" :class="themeClass">
    <a href="#r-v2-main" class="r-v2-skip-link">Skip to main content</a>

    <BackgroundArt
      :layer-a="layerA"
      :layer-b="layerB"
      :active-layer="activeLayer"
    />

    <div class="r-v2-shell__app">
      <AppNav />
      <main id="r-v2-main" class="r-v2-shell__main" tabindex="-1">
        <router-view name="v2" />
      </main>
    </div>

    <GlobalDialogs />
  </div>
</template>

<style scoped>
.r-v2-shell {
  min-height: 100vh;
  color: var(--r-color-fg);
  position: relative;
}

.r-v2-shell__app {
  position: relative;
  z-index: 2;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.r-v2-shell__main {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow-x: hidden;
  outline: none;
}

/* Skip link — stays off-screen until focused via keyboard, then lands in
   the top-left as an always-on-top focusable anchor. */
.r-v2-skip-link {
  position: absolute;
  top: 6px;
  left: -200px;
  z-index: 9999;
  padding: 8px 14px;
  border-radius: var(--r-radius-pill);
  background: var(--r-color-brand-primary);
  color: #fff;
  font-size: 13px;
  font-weight: var(--r-font-weight-semibold);
  text-decoration: none;
  transition: left var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-skip-link:focus,
.r-v2-skip-link:focus-visible {
  left: 12px;
  outline: 2px solid #fff;
  outline-offset: 2px;
}
</style>
