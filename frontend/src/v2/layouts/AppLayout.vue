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
import { onMounted, provide, ref } from "vue";
import AppNav from "@/v2/components/AppShell/AppNav.vue";
import BackgroundArt from "@/v2/components/AppShell/BackgroundArt.vue";
import GlobalDialogs from "@/v2/components/AppShell/GlobalDialogs.vue";
import { BACKGROUND_ART_KEY } from "@/v2/composables/useBackgroundArt";
import { useInputModality } from "@/v2/composables/useInputModality";
import { useThemeClass } from "@/v2/composables/useThemeClass";

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
onMounted(() => {
  installInputModality();
});
</script>

<template>
  <div class="r-v2 r-v2-shell" :class="themeClass">
    <BackgroundArt
      :layer-a="layerA"
      :layer-b="layerB"
      :active-layer="activeLayer"
    />

    <div class="r-v2-shell__app">
      <AppNav />
      <main class="r-v2-shell__main">
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
}
</style>
