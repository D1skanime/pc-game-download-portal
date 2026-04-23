// useThemeClass — returns a reactive class string ("r-v2-dark" | "r-v2-light")
// derived from the active Vuetify theme. Layouts attach it to their root
// element so theme-scoped CSS (`:global(.r-v2.r-v2-light) .foo`) flips with
// the theme.
import { computed, type ComputedRef } from "vue";
import { useTheme } from "vuetify";
import { V2_THEME_DARK } from "@/v2/theme/vuetify";

export function useThemeClass(): ComputedRef<"r-v2-dark" | "r-v2-light"> {
  const theme = useTheme();
  return computed(() =>
    theme.global.name.value === V2_THEME_DARK ? "r-v2-dark" : "r-v2-light",
  );
}
