<script setup lang="ts">
import { useIdle, useLocalStorage } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useTheme } from "vuetify";
import SoundtrackMiniPlayer from "@/components/common/SoundtrackMiniPlayer.vue";
import { useUiVersion } from "@/composables/useUiVersion";
import storeConsole from "@/stores/console";
import storeLanguage from "@/stores/language";
import { V2_THEME_DARK, V2_THEME_LIGHT } from "@/v2/theme/vuetify";

const { locale } = useI18n();
const languageStore = storeLanguage();
const consoleStore = storeConsole();
const vuetifyTheme = useTheme();
const { consoleMode } = storeToRefs(consoleStore);
const { defaultLanguage, languages } = storeToRefs(languageStore);
const storedLocale = useLocalStorage("settings.locale", "");
const selectedLanguage = ref(
  languages.value.find((lang) => lang.value === storedLocale.value) ||
    defaultLanguage.value,
);
locale.value = selectedLanguage.value.value;
languageStore.setLanguage(selectedLanguage.value);

// NOTE: uiVersion uses a module-level singleton ref (useUiVersion) so a write
// from the settings page is the SAME ref RomM.vue reads, triggering a gate
// re-evaluation and an instant v1 ↔ v2 swap with no reload. Theme likewise
// reads the raw localStorage ref — we stay off useUISettings here because it
// imports the API layer and would trigger an API-client ↔ router circular-
// import TDZ during bootstrap (RomM.vue is the first module main.ts loads).
const uiVersion = useUiVersion();
const themeSetting = useLocalStorage<"auto" | "dark" | "light">(
  "settings.theme",
  "auto",
);

const { idle: mouseIdle } = useIdle(100, {
  events: ["mousemove", "mousedown", "wheel", "touchstart"],
});

// Centralized theme resolution — the v1 "dark"/"light" themes and v2
// "v2-dark"/"v2-light" themes live side by side in Vuetify. Picking the right
// name based on uiVersion + user preference + system preference happens here
// so neither the Settings UI nor the Vuetify plugin has to know about both.
const mediaMatch = window.matchMedia("(prefers-color-scheme: dark)");
const systemPrefersDark = ref(mediaMatch.matches);

function handleSystemThemeChange(event: MediaQueryListEvent) {
  systemPrefersDark.value = event.matches;
}

onMounted(() => {
  mediaMatch.addEventListener("change", handleSystemThemeChange);
});

onUnmounted(() => {
  mediaMatch.removeEventListener("change", handleSystemThemeChange);
});

const activeThemeName = computed(() => {
  const prefersDark =
    themeSetting.value === "dark" ||
    (themeSetting.value === "auto" && systemPrefersDark.value);
  if (uiVersion.value === "v2") {
    return prefersDark ? V2_THEME_DARK : V2_THEME_LIGHT;
  }
  return prefersDark ? "dark" : "light";
});

watch(
  activeThemeName,
  (name) => {
    if (vuetifyTheme.global.name.value !== name) {
      vuetifyTheme.change(name);
    }
  },
  { immediate: true },
);

const isV2 = computed(() => uiVersion.value === "v2");
</script>

<template>
  <v-app id="application" :class="{ 'mouse-hidden': consoleMode && mouseIdle }">
    <v-main id="main" class="no-transition">
      <router-view v-if="!isV2" v-slot="{ Component }">
        <component :is="Component" />
        <!-- Fade out the app loading logo -->
        <Transition name="fade" mode="out-in">
          <div v-if="!Component" id="app-loading-logo">
            <img
              src="/assets/logos/romm_logo_xbox_one_circle_grayscale.svg"
              alt="Romm Logo"
            />
          </div>
        </Transition>
      </router-view>
      <router-view v-else name="v2" />
    </v-main>
    <SoundtrackMiniPlayer />
  </v-app>
</template>

<style scoped>
#main.no-transition {
  transition: none;
}

#application.mouse-hidden,
#application.mouse-hidden * {
  cursor: none !important;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
