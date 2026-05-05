<script setup lang="ts">
// RTag — small inline pill used for header tags (region / language /
// custom tags), hash chips (label + mono value), verification badges
// (icon + label, tone-coloured by status). Lighter than RChip — no
// VChip min-height — and tone variants are a single prop, not parallel
// CSS classes.
//
// Layout:  [icon]  [LABEL]  [text/slot]
//
// Tone drives text + border + tinted background colour. Use the tone
// for state (match/miss → success/neutral) instead of inventing
// per-feature classes.
import { RIcon } from "@v2/lib";

defineOptions({ inheritAttrs: false });

interface Props {
  /** Optional MDI icon shown before the eyebrow label / text. */
  icon?: string;
  /** Tiny uppercase eyebrow label (e.g. "CRC", "MD5"). */
  label?: string;
  /** Primary text. Falls back to the default slot when not set. */
  text?: string | number;
  /** Render the primary text in monospace (hash values etc.). */
  mono?: boolean;
  /** Colour preset. */
  tone?: "neutral" | "brand" | "success" | "danger" | "warning" | "info";
  /** Compact (header chip) vs default (verification chip). */
  size?: "sm" | "md";
}

withDefaults(defineProps<Props>(), {
  icon: undefined,
  label: undefined,
  text: undefined,
  mono: false,
  tone: "neutral",
  size: "md",
});
</script>

<template>
  <span class="r-tag" :class="[`r-tag--${tone}`, `r-tag--${size}`]">
    <RIcon v-if="icon" :icon="icon" class="r-tag__icon" />
    <span v-if="label" class="r-tag__label">{{ label }}</span>
    <span
      v-if="text !== undefined || $slots.default"
      class="r-tag__text"
      :class="{ 'r-tag__text--mono': mono }"
    >
      <slot>{{ text }}</slot>
    </span>
  </span>
</template>

<style scoped>
.r-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: var(--r-radius-chip);
  font-weight: var(--r-font-weight-medium);
  white-space: nowrap;
  max-width: 100%;
  /* Tone variables are set per-tone; the box uses them so a single
     rule paints background / border / text. */
  --r-tag-fg: var(--r-color-fg-secondary);
  --r-tag-border: var(--r-color-border-strong);
  --r-tag-bg: var(--r-color-surface);
  color: var(--r-tag-fg);
  background: var(--r-tag-bg);
  border-color: var(--r-tag-border);
}

/* Sizes */
.r-tag--sm {
  padding: 2px 9px;
  font-size: 11.5px;
  gap: 5px;
}
.r-tag--md {
  padding: 4px 10px;
  font-size: 12px;
  gap: 6px;
}

/* Inner pieces */
.r-tag__icon {
  flex-shrink: 0;
  color: var(--r-tag-fg);
}
.r-tag__label {
  font-size: 10.5px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
  flex-shrink: 0;
}
.r-tag__text {
  min-width: 0;
  word-break: break-all;
}
.r-tag__text--mono {
  font-family: var(--r-font-family-mono);
  font-size: 11px;
  color: var(--r-color-fg-secondary);
}

/* Tones — set the three CSS vars; the .r-tag rule does the painting. */
.r-tag--neutral {
  /* defaults already match neutral */
}
.r-tag--brand {
  --r-tag-fg: color-mix(in srgb, var(--r-color-brand-primary) 90%, transparent);
  --r-tag-border: color-mix(
    in srgb,
    var(--r-color-brand-primary) 40%,
    transparent
  );
  --r-tag-bg: color-mix(in srgb, var(--r-color-brand-primary) 12%, transparent);
}
.r-tag--success {
  --r-tag-fg: var(--r-color-success);
  --r-tag-border: color-mix(in srgb, var(--r-color-success) 35%, transparent);
  --r-tag-bg: color-mix(in srgb, var(--r-color-success) 12%, transparent);
}
.r-tag--danger {
  --r-tag-fg: var(--r-color-danger);
  --r-tag-border: color-mix(in srgb, var(--r-color-danger) 35%, transparent);
  --r-tag-bg: color-mix(in srgb, var(--r-color-danger) 12%, transparent);
}
.r-tag--warning {
  --r-tag-fg: var(--r-color-warning);
  --r-tag-border: color-mix(in srgb, var(--r-color-warning) 35%, transparent);
  --r-tag-bg: color-mix(in srgb, var(--r-color-warning) 12%, transparent);
}
.r-tag--info {
  --r-tag-fg: color-mix(in srgb, var(--r-color-info) 90%, transparent);
  --r-tag-border: color-mix(in srgb, var(--r-color-info) 40%, transparent);
  --r-tag-bg: color-mix(in srgb, var(--r-color-info) 12%, transparent);
}
</style>
