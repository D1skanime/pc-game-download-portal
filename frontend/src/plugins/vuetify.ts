import "@mdi/font/css/materialdesignicons.css";
import { useLocalStorage } from "@vueuse/core";
import { createVuetify } from "vuetify";
import { VDateInput } from "vuetify/labs/VDateInput";
import "vuetify/styles";
import { dark, light } from "@/styles/themes";
import {
  V2_THEME_DARK,
  V2_THEME_LIGHT,
  v2Dark,
  v2Light,
} from "@/v2/theme/vuetify";

// Initial theme resolution only — runtime theme changes (including uiVersion
// and system-preference reactions) are owned by RomM.vue so theme names stay
// in sync with the active UI generation.
function getInitialTheme() {
  const storedTheme = useLocalStorage("settings.theme", "auto");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const storedUiVersion = useLocalStorage("settings.uiVersion", "v1");

  let base: "dark" | "light";
  if (storedTheme.value === "dark" || storedTheme.value === "light") {
    base = storedTheme.value;
  } else {
    base = prefersDark ? "dark" : "light";
  }

  if (storedUiVersion.value === "v2") {
    return base === "dark" ? V2_THEME_DARK : V2_THEME_LIGHT;
  }
  return base;
}

const instance = createVuetify({
  components: {
    VDateInput,
  },
  icons: {
    defaultSet: "mdi",
  },
  theme: {
    defaultTheme: getInitialTheme(),
    themes: {
      dark,
      light,
      [V2_THEME_DARK]: v2Dark,
      [V2_THEME_LIGHT]: v2Light,
    },
  },
});

export default instance;
