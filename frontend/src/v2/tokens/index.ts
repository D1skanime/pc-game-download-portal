// RomM v2 Design Tokens
//
// The system is built on a near-black base
// with translucent white surfaces and 1-2 brand accents — a "glass over dark
// artwork" language rather than solid cards on a solid background. CSS
// custom properties are mirrored in src/v2/styles/tokens.css and must be
// kept in sync.

export const colorBrand = {
  // Match v1's purple-first palette (dark-mode values). The original RomM
  // accent colour; `primaryHover` and `primaryPressed` line up with v1's
  // `primary-lighten` / `primary-darken`.
  primary: "#8B74E8",
  primaryHover: "#A18FFF",
  primaryPressed: "#6043C8",
  // Secondary mirrors v1's secondary purple for chips / inactive bits.
  secondary: "#9E8CD6",
  secondaryHover: "#EBE7FA",
  secondaryPressed: "#7A6BB4",
  // Accent is v1's salmon/peach — used sparingly for emphasis.
  accent: "#E1A38D",
  accentHover: "#F0C8B8",
  // User-avatar gradient picks up the primary palette so everything stays
  // in-family. (The mockup's red-to-magenta gradient is dropped here to
  // align with v1.)
  avatarGradient: "linear-gradient(135deg, #A18FFF, #6043C8)",
  // Legacy semantic colours available for specific chips / icons.
  rommRed: "#DA3633",
  rommGreen: "#3FB950",
  rommBlue: "#0070F3",
  rommGold: "#FFD700",
} as const;

export const colorStatus = {
  success: "#4ADE80",
  warning: "#FBBF24",
  danger: "#FF5050",
  info: "#93C5FD",
} as const;

// Dark (default) palette — the mockup is dark-only, so light uses an
// inverted alpha scheme that still reads as translucent glass.
export const colorDark = {
  bg: "#07070f",
  bgElevated: "rgba(255, 255, 255, 0.045)",
  surface: "rgba(255, 255, 255, 0.07)",
  surfaceHover: "rgba(255, 255, 255, 0.12)",
  fg: "#ffffff",
  fgSecondary: "rgba(255, 255, 255, 0.75)",
  fgMuted: "rgba(255, 255, 255, 0.45)",
  fgFaint: "rgba(255, 255, 255, 0.25)",
  border: "rgba(255, 255, 255, 0.07)",
  borderStrong: "rgba(255, 255, 255, 0.15)",
  focus: "#ffffff",
} as const;

export const colorLight = {
  bg: "#f5f5fa",
  bgElevated: "rgba(0, 0, 0, 0.045)",
  surface: "rgba(0, 0, 0, 0.07)",
  surfaceHover: "rgba(0, 0, 0, 0.12)",
  fg: "#111117",
  fgSecondary: "rgba(17, 17, 23, 0.75)",
  fgMuted: "rgba(17, 17, 23, 0.45)",
  fgFaint: "rgba(17, 17, 23, 0.25)",
  border: "rgba(0, 0, 0, 0.07)",
  borderStrong: "rgba(0, 0, 0, 0.15)",
  focus: "#111117",
} as const;

export const fontFamily = {
  sans: "'Segoe UI', -apple-system, BlinkMacSystemFont, system-ui, 'Inter', Roboto, sans-serif",
  display:
    "'Segoe UI', -apple-system, BlinkMacSystemFont, system-ui, 'Inter', Roboto, sans-serif",
  mono: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace",
} as const;

// Mockup-derived sizes lean small/dense — most body text sits around 13px.
export const fontSize = {
  xs: "10.5px",
  sm: "11.5px",
  md: "13px",
  lg: "14.5px",
  xl: "17px",
  "2xl": "22px",
  "3xl": "32px",
  "4xl": "38px",
} as const;

export const lineHeight = {
  tight: "1.1",
  normal: "1.4",
  relaxed: "1.7",
} as const;

export const fontWeight = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
  extrabold: "800",
} as const;

// 4px base, with the mockup's more generous "row-pad" at the top end.
export const space = {
  0: "0",
  1: "4px",
  2: "8px",
  3: "12px",
  4: "16px",
  5: "20px",
  6: "24px",
  7: "28px",
  8: "32px",
  10: "40px",
  12: "48px",
  14: "56px",
  rowPad: "36px",
} as const;

// Radii: `pill` = fully-rounded for buttons/chips/nav, `art` = card art
// (8px), `card` = surface cards (10-14px), `chip` = small tags (4-6px).
export const radius = {
  none: "0",
  xs: "3px",
  sm: "4px",
  chip: "6px",
  md: "8px",
  art: "8px",
  lg: "10px",
  card: "14px",
  xl: "20px",
  pill: "100px",
  full: "9999px",
} as const;

// Elevations match the mockup's single-source-of-truth drop shadows on
// cards and menus. Background blur lives on its own layer, not here.
export const elevation = {
  0: "none",
  1: "0 2px 8px rgba(0, 0, 0, 0.2)",
  2: "0 8px 24px rgba(0, 0, 0, 0.45)",
  3: "0 8px 30px rgba(0, 0, 0, 0.6)",
  4: "0 20px 60px rgba(0, 0, 0, 0.7)",
  5: "0 32px 96px rgba(0, 0, 0, 0.7)",
  cover: "0 24px 48px rgba(0, 0, 0, 0.8)",
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
  ringWidthKey: "2.5px",
  ringWidthPad: "3.5px",
  ringOffset: "3px",
} as const;

// Layout constants from the mockup.
export const layout = {
  navHeight: "58px",
  rowPad: "36px",
  cardArtWidth: "158px",
  cardArtHeight: "213px",
  heroCardWidth: "300px",
  heroCardHeight: "169px",
  detailCoverWidth: "240px",
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
  layout,
} as const;

export type Tokens = typeof tokens;
