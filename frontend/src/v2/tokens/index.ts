// RomM v2 Design Tokens
//
// Source of truth for v2 visual language. Mirrored to src/v2/styles/tokens.css
// as CSS custom properties. Vuetify's v2 theme (src/v2/theme/vuetify.ts) derives
// its palette from this file so token names and values never diverge.

export const colorBrand = {
  primary: "#8B74E8",
  primaryHover: "#A18FFF",
  primaryPressed: "#6043C8",
  accent: "#E1A38D",
  rommRed: "#DA3633",
  rommGreen: "#3FB950",
  rommBlue: "#0070F3",
  rommGold: "#FFD700",
} as const;

export const colorStatus = {
  success: "#3FB950",
  warning: "#E3B341",
  danger: "#DA3633",
  info: "#0070F3",
} as const;

export const colorDark = {
  bg: "#0D1117",
  bgElevated: "#161B22",
  surface: "#1C2330",
  fg: "#F0F3FA",
  fgMuted: "#9BA1AD",
  border: "#262C36",
  focus: "#A18FFF",
} as const;

export const colorLight = {
  bg: "#F2F4F8",
  bgElevated: "#FFFFFF",
  surface: "#E4E9F0",
  fg: "#0D1117",
  fgMuted: "#5D6472",
  border: "#D5DAE2",
  focus: "#371f69",
} as const;

export const fontFamily = {
  sans: "'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  display:
    "'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  mono: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace",
} as const;

export const fontSize = {
  xs: "0.75rem",
  sm: "0.875rem",
  md: "1rem",
  lg: "1.125rem",
  xl: "1.25rem",
  "2xl": "1.5rem",
  "3xl": "1.875rem",
  "4xl": "2.25rem",
} as const;

export const lineHeight = {
  tight: "1.2",
  normal: "1.4",
  relaxed: "1.6",
} as const;

export const fontWeight = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const;

// 4px-based spacing scale
export const space = {
  0: "0",
  1: "0.25rem",
  2: "0.5rem",
  3: "0.75rem",
  4: "1rem",
  5: "1.25rem",
  6: "1.5rem",
  8: "2rem",
  10: "2.5rem",
  12: "3rem",
} as const;

export const radius = {
  sm: "4px",
  md: "8px",
  lg: "12px",
  xl: "20px",
  full: "9999px",
} as const;

export const elevation = {
  1: "0 1px 2px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(255, 255, 255, 0.02)",
  2: "0 4px 12px rgba(0, 0, 0, 0.22), 0 0 0 1px rgba(255, 255, 255, 0.02)",
  3: "0 6px 24px rgba(0, 0, 0, 0.30), 0 0 0 1px rgba(255, 255, 255, 0.03)",
  4: "0 10px 32px rgba(0, 0, 0, 0.38), 0 0 0 1px rgba(255, 255, 255, 0.04)",
  5: "0 18px 48px rgba(0, 0, 0, 0.48), 0 0 0 1px rgba(255, 255, 255, 0.05)",
} as const;

export const motion = {
  fast: "150ms",
  med: "220ms",
  slow: "360ms",
  easeOut: "cubic-bezier(0.22, 1, 0.36, 1)",
  easeInOut: "cubic-bezier(0.65, 0, 0.35, 1)",
} as const;

export const focus = {
  ringWidthMouse: "2px",
  ringWidthKey: "3px",
  ringWidthPad: "4px",
  ringOffset: "2px",
} as const;

export const tokens = {
  colorBrand,
  colorStatus,
  colorDark,
  colorLight,
  fontFamily,
  fontSize,
  lineHeight,
  fontWeight,
  space,
  radius,
  elevation,
  motion,
  focus,
} as const;

export type Tokens = typeof tokens;
