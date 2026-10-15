<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core";
import { storeToRefs } from "pinia";
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";
import { useI18n } from "vue-i18n";
import { useTheme } from "vuetify";
import storeLanguage from "@/stores/language";

// Lazy-loaded: RomM.vue is the first module main.ts evaluates, and the banner
// transitively imports the API layer (stores → services/api → router). A
// static import would pull that graph into bootstrap and trip the
// api-client ↔ router circular-import TDZ (see the theme/scope notes below).
const BackendStatusBanner = defineAsyncComponent(
  () => import("@/v2/components/AppShell/BackendStatusBanner.vue"),
);

const { locale } = useI18n();
const languageStore = storeLanguage();
const vuetifyTheme = useTheme();
const { languages } = storeToRefs(languageStore);
const storedLocale = useLocalStorage("settings.locale", "");
const selectedLanguage = ref(
  languages.value.find((lang) => lang.value === storedLocale.value) ||
    languageStore.detectBrowserLanguage(),
);
locale.value = selectedLanguage.value.value;
languageStore.setLanguage(selectedLanguage.value);

// Theme reads the raw localStorage ref. We stay off useUISettings here because it
// imports the API layer and would trigger an API-client ↔ router circular-
// import TDZ during bootstrap (RomM.vue is the first module main.ts loads).
const themeSetting = useLocalStorage<"auto" | "dark" | "light">(
  "settings.theme",
  "dark",
);

// Centralized theme resolution — Vuetify only knows the "dark" / "light"
// pair (used by v1 surfaces and any remaining v1 components rendered
// inside v2). v2's own colour story is driven by tokens on the .r-v2-*
// classes below, not by Vuetify's runtime theme.
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

const prefersDark = computed(
  () =>
    themeSetting.value === "dark" ||
    (themeSetting.value === "auto" && systemPrefersDark.value),
);

const activeThemeName = computed<"dark" | "light">(() =>
  prefersDark.value ? "dark" : "light",
);

watch(
  activeThemeName,
  (name) => {
    if (vuetifyTheme.global.name.value !== name) {
      vuetifyTheme.change(name);
    }
  },
  { immediate: true },
);

// Apply the v2 token scope to <html>. Vuetify teleports
// overlays (VDialog, VMenu) into `<body> > .v-overlay-container` — which
// sits OUTSIDE both the AppLayout `.r-v2` wrapper AND <v-app>. Putting the
// classes on <html> means the entire document inherits the v2 CSS custom
// properties so `var(--r-color-...)` resolves inside any teleported dialog.
watch(
  prefersDark,
  (dark) => {
    const root = document.documentElement;
    root.classList.add("r-v2");
    root.classList.toggle("r-v2-dark", dark);
    root.classList.toggle("r-v2-light", !dark);
  },
  { immediate: true },
);
</script>

<template>
  <v-app id="application">
    <v-main id="main" class="no-transition">
      <router-view />
    </v-main>
    <!-- v2-only: backend reachability strip. Mounted at the root so it
         covers both the auth layout (login/setup) and the main shell, and
         owns the app-wide connection poll + auto-recovery. -->
    <BackendStatusBanner />
  </v-app>
</template>

<style scoped>
#main.no-transition {
  transition: none;
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
