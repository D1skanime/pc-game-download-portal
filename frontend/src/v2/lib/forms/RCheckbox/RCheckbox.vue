<script setup lang="ts">
// RCheckbox — wraps v-checkbox with the v2 visual language: a small
// rounded square that fills with brand-primary on check, with a white
// tick on top. The 36×36 click target is preserved (good for touch and
// pad); the 18×18 visible box is drawn as a pseudo-element so the hit
// area never shrinks below comfortable.
//
// Indeterminate renders mdi-minus; error tints the box with --r-color-danger.
// Focus is modality-gated (visible only on key/pad).
import { VCheckbox } from "vuetify/components/VCheckbox";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: boolean | null;
  label?: string;
  density?: "default" | "comfortable" | "compact";
  disabled?: boolean;
  indeterminate?: boolean;
  hideDetails?: boolean | "auto";
  size?: "sm" | "md";
}

withDefaults(defineProps<Props>(), {
  modelValue: false,
  label: undefined,
  density: "comfortable",
  hideDetails: "auto",
  size: "md",
});

defineEmits<{
  (e: "update:modelValue", value: boolean | null): void;
}>();
</script>

<template>
  <VCheckbox
    v-bind="$attrs"
    class="r-checkbox"
    :class="`r-checkbox--${size}`"
    :model-value="modelValue"
    :label="label"
    :density="density"
    :disabled="disabled"
    :indeterminate="indeterminate"
    :hide-details="hideDetails"
    false-icon=""
    true-icon="mdi-check"
    indeterminate-icon="mdi-minus"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VCheckbox>
</template>

<style scoped>
.r-checkbox :deep(.v-selection-control) {
  min-height: 36px;
}
.r-checkbox :deep(.v-selection-control__wrapper),
.r-checkbox :deep(.v-selection-control__input) {
  width: 36px;
  height: 36px;
}

/* Visible 18×18 box drawn as a pseudo-element so the click target
   stays 36×36 (touch / pad friendly). */
.r-checkbox :deep(.v-selection-control__input) {
  position: relative;
  border-radius: 8px;
}
.r-checkbox :deep(.v-selection-control__input)::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  width: 18px;
  height: 18px;
  margin-top: -9px;
  margin-left: -9px;
  border-radius: 4px;
  border: 1.5px solid var(--r-color-border-strong);
  background: transparent;
  pointer-events: none;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}

/* Hover (only when interactive). */
.r-checkbox
  :deep(.v-selection-control:not(.v-selection-control--disabled))
  .v-selection-control__input:hover::before {
  border-color: var(--r-color-fg-secondary);
  background: var(--r-color-surface-hover);
}

/* Vuetify ripple — off; we own the visual feedback. */
.r-checkbox :deep(.v-selection-control__input .v-ripple__container) {
  display: none;
}

/* Checked / indeterminate fill. */
.r-checkbox
  :deep(.v-selection-control--dirty .v-selection-control__input)::before,
.r-checkbox
  :deep(
    .v-selection-control--indeterminate .v-selection-control__input
  )::before {
  background: var(--r-color-brand-primary);
  border-color: var(--r-color-brand-primary);
}
.r-checkbox
  :deep(.v-selection-control--dirty:not(.v-selection-control--disabled))
  .v-selection-control__input:hover::before,
.r-checkbox
  :deep(.v-selection-control--indeterminate:not(.v-selection-control--disabled))
  .v-selection-control__input:hover::before {
  background: var(--r-color-brand-primary-hover);
  border-color: var(--r-color-brand-primary-hover);
}

/* The mdi-check / mdi-minus glyph sits on top of the filled box. */
.r-checkbox :deep(.v-selection-control__input .v-icon) {
  position: relative;
  z-index: 1;
  color: var(--r-color-overlay-fg);
  font-size: 16px;
  opacity: 1;
}

/* Modality-gated focus on the visible box. The native <input> is
   visually hidden so :focus-within on the wrapper is the right hook. */
html[data-input="key"]
  .r-checkbox
  :deep(.v-selection-control__input:focus-within)::before,
html[data-input="pad"]
  .r-checkbox
  :deep(.v-selection-control__input:focus-within)::before {
  outline: var(--r-focus-ring-width) solid var(--r-color-focus);
  outline-offset: 2px;
}
html[data-input="pad"]
  .r-checkbox
  :deep(.v-selection-control__input:focus-within)::before {
  box-shadow: 0 0 0 5px
    color-mix(in srgb, var(--r-color-brand-primary) 20%, transparent);
}

/* Disabled. */
.r-checkbox :deep(.v-selection-control--disabled) {
  opacity: 0.45;
}

/* Label. */
.r-checkbox :deep(.v-label) {
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-md);
  opacity: 1;
}
.r-checkbox :deep(.v-selection-control--disabled .v-label) {
  color: var(--r-color-fg-faint);
}

/* Error state — red box + label. Vuetify adds .v-input--error to the
   outer wrapper when the field's rules fail or :error is true. */
.r-checkbox :deep(.v-input--error .v-selection-control__input)::before {
  border-color: var(--r-color-danger) !important;
}
.r-checkbox
  :deep(
    .v-input--error.v-selection-control--dirty .v-selection-control__input
  )::before {
  background: var(--r-color-danger);
}
.r-checkbox :deep(.v-input--error .v-label),
.r-checkbox :deep(.v-input--error .v-messages) {
  color: var(--r-color-danger);
}

/* ── Small variant ── */
.r-checkbox--sm :deep(.v-selection-control) {
  min-height: 28px;
}
.r-checkbox--sm :deep(.v-selection-control__wrapper),
.r-checkbox--sm :deep(.v-selection-control__input) {
  width: 28px;
  height: 28px;
}
.r-checkbox--sm :deep(.v-selection-control__input)::before {
  width: 16px;
  height: 16px;
  margin-top: -8px;
  margin-left: -8px;
  border-radius: 3px;
}
.r-checkbox--sm :deep(.v-selection-control__input .v-icon) {
  font-size: 13px;
}
.r-checkbox--sm :deep(.v-label) {
  font-size: var(--r-font-size-sm);
}
</style>
