// v2 Vuetify theme definitions. Palette derives from src/v2/tokens/index.ts so
// Vuetify components (those we wrap with R-components) use the same colors as
// our design tokens.
import type { ThemeDefinition } from "vuetify";
import { colorBrand, colorDark, colorLight, colorStatus } from "@/v2/tokens";

const commonColors = {
  "romm-red": colorBrand.rommRed,
  "romm-green": colorBrand.rommGreen,
  "romm-blue": colorBrand.rommBlue,
  "romm-gold": colorBrand.rommGold,
};

export const v2Dark: ThemeDefinition = {
  dark: true,
  colors: {
    primary: colorBrand.primary,
    secondary: colorBrand.accent,
    accent: colorBrand.accent,
    background: colorDark.bg,
    surface: colorDark.bgElevated,
    toplayer: colorDark.surface,
    "on-surface": colorDark.fg,
    "on-background": colorDark.fg,
    success: colorStatus.success,
    warning: colorStatus.warning,
    error: colorStatus.danger,
    info: colorStatus.info,
    ...commonColors,
  },
};

export const v2Light: ThemeDefinition = {
  dark: false,
  colors: {
    primary: colorBrand.primary,
    secondary: colorBrand.accent,
    accent: colorBrand.accent,
    background: colorLight.bg,
    surface: colorLight.bgElevated,
    toplayer: colorLight.surface,
    "on-surface": colorLight.fg,
    "on-background": colorLight.fg,
    success: colorStatus.success,
    warning: colorStatus.warning,
    error: colorStatus.danger,
    info: colorStatus.info,
    ...commonColors,
  },
};

export const V2_THEME_DARK = "v2-dark";
export const V2_THEME_LIGHT = "v2-light";
