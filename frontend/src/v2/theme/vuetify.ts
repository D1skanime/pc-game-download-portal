// v2 Vuetify theme definitions. Palette derives from src/v2/tokens/index.ts so
// Vuetify components (those we wrap with R-components) use the same colors as
// our design tokens.
//
// Note on rgba tokens: Vuetify accepts hex / named colors but some internal
// calculations (opacity multipliers, contrast) expect solid values. We keep
// `background` / `surface` / `toplayer` solid here and let the mockup's
// translucent glass surfaces come from CSS variables on R-components.
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
    secondary: colorBrand.secondary,
    accent: colorBrand.accent,
    background: colorDark.bg,
    surface: colorDark.vuetifySurface,
    toplayer: colorDark.vuetifyToplayer,
    "on-surface": colorDark.fg,
    "on-background": colorDark.fg,
    "primary-lighten": colorBrand.primaryHover,
    "primary-darken": colorBrand.primaryPressed,
    "secondary-lighten": colorBrand.secondaryHover,
    "secondary-darken": colorBrand.secondaryPressed,
    success: colorStatus.success,
    warning: colorStatus.warning,
    error: colorStatus.danger,
    danger: colorStatus.danger,
    info: colorStatus.info,
    ...commonColors,
  },
};

export const v2Light: ThemeDefinition = {
  dark: false,
  colors: {
    // v1's light-mode primary is a deeper purple for contrast against the
    // off-white page; the brand-light tokens carry the pair.
    primary: colorBrand.primaryLight,
    secondary: colorBrand.secondaryLight,
    accent: colorBrand.accent,
    background: colorLight.bg,
    surface: colorLight.vuetifySurface,
    toplayer: colorLight.vuetifyToplayer,
    "on-surface": colorLight.fg,
    "on-background": colorLight.fg,
    "primary-lighten": colorBrand.primaryLightHover,
    "primary-darken": colorBrand.primaryLightPressed,
    "secondary-lighten": colorBrand.secondaryLightHover,
    "secondary-darken": colorBrand.secondaryLightPressed,
    success: colorStatus.success,
    warning: colorStatus.warning,
    error: colorStatus.danger,
    danger: colorStatus.danger,
    info: colorStatus.info,
    ...commonColors,
  },
};

export const V2_THEME_DARK = "v2-dark";
export const V2_THEME_LIGHT = "v2-light";
