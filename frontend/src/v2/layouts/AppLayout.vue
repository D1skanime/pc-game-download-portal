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
import storeCollections from "@/stores/collections";
import AppNav from "@/v2/components/AppShell/AppNav.vue";
import BackgroundArt from "@/v2/components/AppShell/BackgroundArt.vue";
import GlobalDialogs from "@/v2/components/AppShell/GlobalDialogs.vue";
import { BACKGROUND_ART_KEY } from "@/v2/composables/useBackgroundArt";
import { installPermissionsHydration } from "@/v2/composables/useCan";
import { useGamepad } from "@/v2/composables/useGamepad";
import { useGlobalHotkeys } from "@/v2/composables/useGlobalHotkeys";
import { useInputModality } from "@/v2/composables/useInputModality";
import { installBackMorph } from "@/v2/composables/useViewTransition";

installPermissionsHydration();

const collectionsStore = storeCollections();

// Shared reactive background art — views paint covers via the injected setter.
const layerA = ref<string | null>(null);
const layerB = ref<string | null>(null);
const activeLayer = ref<"a" | "b">("a");

// Dwell before applying a backdrop swap. Without it, dragging the cursor
// across the gallery would trigger one cross-fade per card and the
// 700ms fades collide as flashes; the latest call wins after the dwell.
const BG_HOVER_DWELL_MS = 80;
let bgTimer: ReturnType<typeof setTimeout> | null = null;

function setBackgroundArt(url: string | null) {
  const current = activeLayer.value === "a" ? layerA.value : layerB.value;
  if (current === url) {
    if (bgTimer !== null) {
      clearTimeout(bgTimer);
      bgTimer = null;
    }
    return;
  }
  if (bgTimer !== null) clearTimeout(bgTimer);
  bgTimer = setTimeout(() => {
    bgTimer = null;
    if (activeLayer.value === "a") {
      layerB.value = url;
      activeLayer.value = "b";
    } else {
      layerA.value = url;
      activeLayer.value = "a";
    }
  }, BG_HOVER_DWELL_MS);
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
  // Hydrate collections (incl. favoriteCollection) so per-ROM favorite
  // state resolves on direct navigation to /rom/:id without going
  // through Home / Collections first. v1 did this in `Main.vue`.
  if (collectionsStore.allCollections.length === 0) {
    void collectionsStore.fetchCollections();
  }
});

onBeforeUnmount(() => {
  removeBackMorph?.();
  removeBackMorph = null;
  if (bgTimer !== null) {
    clearTimeout(bgTimer);
    bgTimer = null;
  }
});
</script>

<template>
  <div class="r-v2-shell">
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
/* Lock the v2 shell to the viewport — the gallery owns its own
   internal scroll, and the document itself must never scroll
   (otherwise the navbar disappears as the page slides up). */
.r-v2-shell {
  height: 100vh;
  overflow: hidden;
  color: var(--r-color-fg);
  position: relative;
}

.r-v2-shell__app {
  position: relative;
  z-index: 2;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.r-v2-shell__main {
  flex: 1;
  min-height: 0;
  position: relative;
  /* Vertical overflow scrolls INSIDE main, not at the document level
     (the outer `.r-v2-shell` is locked with `overflow: hidden`). This
     way views without an internal scroller (Home, Settings, etc.)
     scroll within main while the navbar stays put. Views that own
     their own scroll (Gallery — `<section>` is exactly main's height
     with `overflow: hidden` and an internal `RVirtualScroller`)
     simply don't generate any overflow at this level, so there's
     never a competing scrollbar. */
  overflow-y: auto;
  overflow-x: hidden;
  outline: none;
}
</style>
