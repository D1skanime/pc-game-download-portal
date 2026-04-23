<script setup lang="ts">
// AppLayout — top-level v2 shell. Thin orchestrator: owns shared
// providers (background art, context-menu opener), mounts the sub-
// components that make up the visual chrome.
//
//   * BackgroundArt   — two-layer blurred backdrop with cross-fade
//   * AppNav          — logo · centered tab pill · user menu
//   * GlobalDialogs   — emitter-driven dialog + notification stack
//   * GameContextMenu — right-click / long-press ROM menu
import { computed, onMounted, provide, ref } from "vue";
import { useTheme } from "vuetify";
import type { SimpleRom } from "@/stores/roms";
import AppNav from "@/v2/components/AppShell/AppNav.vue";
import BackgroundArt from "@/v2/components/AppShell/BackgroundArt.vue";
import GlobalDialogs from "@/v2/components/AppShell/GlobalDialogs.vue";
import GameContextMenu from "@/v2/components/GameContextMenu.vue";
import {
  GAME_CONTEXT_MENU_KEY,
  type OpenGameContextMenu,
} from "@/v2/composables/useGameContextMenu";
import { useInputModality } from "@/v2/composables/useInputModality";
import { V2_THEME_DARK } from "@/v2/theme/vuetify";

const theme = useTheme();
const themeClass = computed(() =>
  theme.global.name.value === V2_THEME_DARK ? "r-v2-dark" : "r-v2-light",
);

// Shared context-menu state. Cards and tiles call the provided opener.
const ctxOpen = ref(false);
const ctxRom = ref<SimpleRom | null>(null);
const ctxX = ref(0);
const ctxY = ref(0);

const openGameContextMenu: OpenGameContextMenu = (rom, event) => {
  ctxRom.value = rom;
  ctxX.value = event.clientX;
  ctxY.value = event.clientY;
  ctxOpen.value = true;
};
provide(GAME_CONTEXT_MENU_KEY, openGameContextMenu);

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
provide("r-v2-set-background-art", setBackgroundArt);

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

    <GameContextMenu v-model:open="ctxOpen" :rom="ctxRom" :x="ctxX" :y="ctxY" />
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
