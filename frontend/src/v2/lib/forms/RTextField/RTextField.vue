<script setup lang="ts">
// RTextField — wraps v-text-field with the v2 visual language.
//
// Two looks:
//   • Floating label (default, Vuetify-outlined) — used by Auth flows
//     and any place where the label needs to collapse into the field
//     when filled.
//   • Inline label prefix (`inline-label` prop) — the v2-native look
//     for forms inside Settings: the label sits as a slightly darker
//     "well" on the LEFT of the field, separated by a hairline; the
//     input value sits on the right. The label area accepts any
//     content via the `#label` slot (text, RIcon, both…). Width is
//     `labelWidth` (default 120px) so a stack of fields aligns
//     vertically. Falls back to the `label` prop string if the slot
//     is empty.
//
// rules are typed loosely (`unknown[]`) because Vuetify's own rule
// type is structural and works for any function returning
// boolean|string.
import { computed } from "vue";
import { VTextField } from "vuetify/components/VTextField";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: string | number | null;
  label?: string;
  type?: string;
  variant?:
    | "filled"
    | "outlined"
    | "plain"
    | "underlined"
    | "solo"
    | "solo-inverted"
    | "solo-filled";
  density?: "default" | "comfortable" | "compact";
  prependInnerIcon?: string;
  appendInnerIcon?: string;
  autocomplete?: string;
  name?: string;
  rules?: unknown[];
  hint?: string;
  hideDetails?: boolean | "auto";
  required?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  loading?: boolean;
  clearable?: boolean;
  error?: boolean;
  errorMessages?: string | string[];
  /** Render the label as a left "prefix" inside the field instead of
   *  Vuetify's floating label. Use the `#label` slot for icon + text. */
  inlineLabel?: boolean;
  /** Width of the inline label prefix area. Default 120px. */
  labelWidth?: string | number;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  label: undefined,
  type: "text",
  variant: "outlined",
  density: "comfortable",
  prependInnerIcon: undefined,
  appendInnerIcon: undefined,
  autocomplete: undefined,
  name: undefined,
  rules: undefined,
  hint: undefined,
  hideDetails: false,
  errorMessages: undefined,
  inlineLabel: false,
  labelWidth: "120px",
});

defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const labelWidthCss = computed(() =>
  typeof props.labelWidth === "number"
    ? `${props.labelWidth}px`
    : props.labelWidth,
);

// click:append-inner / click:prepend-inner are *not* declared here on
// purpose. Vuetify only makes the inner icon tabbable when a click
// listener is attached, so we let the parent's listener flow through
// `$attrs` instead of always forwarding it. That way `prepend-inner-icon`
// stays decorative (no focus ring, no tab stop) unless the parent
// genuinely subscribes — which is what you want for the password-reveal
// eye icon, but not for a plain mdi-account adornment.
</script>

<template>
  <VTextField
    v-bind="$attrs"
    class="r-text-field"
    :class="{ 'r-text-field--inline-label': inlineLabel }"
    :style="inlineLabel ? { '--rtf-label-w': labelWidthCss } : undefined"
    :model-value="modelValue"
    :label="inlineLabel ? undefined : label"
    :placeholder="($attrs.placeholder as string | undefined) ?? undefined"
    :type="type"
    :variant="variant"
    :density="density"
    :prepend-inner-icon="inlineLabel ? undefined : prependInnerIcon"
    :append-inner-icon="appendInnerIcon"
    :autocomplete="autocomplete"
    :name="name"
    :rules="rules as never"
    :hint="hint"
    :hide-details="hideDetails"
    :required="required"
    :disabled="disabled"
    :readonly="readonly"
    :loading="loading"
    :clearable="clearable"
    :error="error"
    :error-messages="errorMessages"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <!-- Inline label takes over Vuetify's prepend-inner slot when on. -->
    <template v-if="inlineLabel" #prepend-inner>
      <span class="r-text-field__inline-label">
        <slot name="label">{{ label }}</slot>
      </span>
    </template>

    <!-- Pass through every consumer slot. We filter at the iterator
         level (not inside the slot body) so VTextField doesn't see a
         second `prepend-inner` registration when we own it via the
         v-if above. -->
    <template
      v-for="slotName in Object.keys($slots).filter(
        (s) => !(inlineLabel && s === 'prepend-inner'),
      )"
      #[slotName]="slotProps"
      :key="slotName"
    >
      <slot :name="slotName" v-bind="slotProps || {}" />
    </template>
  </VTextField>
</template>

<style scoped>
/* ── Default outlined variant ─────────────────────────────────────
   Override Vuetify's 4-piece outline to a flat 1px border on
   `--r-color-border`, swapping to brand on focus and danger on error. */

.r-text-field :deep(.v-field) {
  padding-left: 0px !important;
  border-radius: 8px;
  font-size: 14px;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    box-shadow var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-text-field :deep(.v-field--variant-outlined) {
  background: var(--r-color-surface);
}

.r-text-field :deep(.v-field--variant-outlined .v-field__outline__start),
.r-text-field
  :deep(.v-field--variant-outlined .v-field__outline__notch::before),
.r-text-field :deep(.v-field--variant-outlined .v-field__outline__notch::after),
.r-text-field :deep(.v-field--variant-outlined .v-field__outline__end) {
  border-width: 1px;
  border-color: var(--r-color-border);
  opacity: 1;
  transition: border-color var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-text-field
  :deep(.v-field--variant-outlined.v-field--focused .v-field__outline__start),
.r-text-field
  :deep(
    .v-field--variant-outlined.v-field--focused .v-field__outline__notch::before
  ),
.r-text-field
  :deep(
    .v-field--variant-outlined.v-field--focused .v-field__outline__notch::after
  ),
.r-text-field
  :deep(.v-field--variant-outlined.v-field--focused .v-field__outline__end) {
  border-color: var(--r-color-brand-primary);
}

.r-text-field :deep(.v-field--variant-outlined:hover .v-field__outline__start),
.r-text-field
  :deep(.v-field--variant-outlined:hover .v-field__outline__notch::before),
.r-text-field
  :deep(.v-field--variant-outlined:hover .v-field__outline__notch::after),
.r-text-field :deep(.v-field--variant-outlined:hover .v-field__outline__end) {
  border-color: var(--r-color-border-strong);
}

.r-text-field
  :deep(.v-field--variant-outlined.v-field--error .v-field__outline__start),
.r-text-field
  :deep(
    .v-field--variant-outlined.v-field--error .v-field__outline__notch::before
  ),
.r-text-field
  :deep(
    .v-field--variant-outlined.v-field--error .v-field__outline__notch::after
  ),
.r-text-field
  :deep(.v-field--variant-outlined.v-field--error .v-field__outline__end) {
  border-color: var(--r-color-danger);
}

/* Floating label — small + brand on focus + danger on error. */
.r-text-field :deep(.v-field-label) {
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg-muted);
  letter-spacing: 0;
}
.r-text-field :deep(.v-field--focused .v-field-label),
.r-text-field :deep(.v-field--active .v-field-label) {
  font-size: 11px;
  letter-spacing: 0.04em;
}
.r-text-field :deep(.v-field--focused .v-field-label) {
  color: var(--r-color-brand-primary);
}
.r-text-field :deep(.v-field--error .v-field-label) {
  color: var(--r-color-danger) !important;
}

/* Input value */
.r-text-field :deep(.v-field__input) {
  font-size: 14px;
  color: var(--r-color-fg);
  line-height: 1.4;
  min-height: 38px;
  padding-top: 14px;
  padding-bottom: 6px;
}
.r-text-field :deep(.v-field--variant-outlined .v-field__input) {
  padding-inline: 14px;
}

/* Inner icons */
.r-text-field :deep(.v-field__prepend-inner > .v-icon),
.r-text-field :deep(.v-field__append-inner > .v-icon) {
  color: var(--r-color-fg-muted);
  opacity: 1;
  font-size: 18px;
}
.r-text-field :deep(.v-field--focused .v-field__prepend-inner > .v-icon),
.r-text-field :deep(.v-field--focused .v-field__append-inner > .v-icon) {
  color: var(--r-color-brand-primary);
}

/* Hint / error message row */
.r-text-field :deep(.v-input__details) {
  padding-inline: 14px;
  padding-block-start: 4px;
  min-height: 18px;
}
.r-text-field :deep(.v-messages__message) {
  font-size: 11px;
  line-height: 1.4;
  color: var(--r-color-fg-muted);
}
.r-text-field :deep(.v-input--error .v-messages__message) {
  color: var(--r-color-danger);
}

.r-text-field :deep(.v-field--disabled) {
  opacity: 0.55;
}

/* ── Underlined variant — auth flows ───────────────────────────── */

.r-text-field :deep(.v-field--variant-underlined::before) {
  border-color: var(--r-color-border);
}
.r-text-field :deep(.v-field--variant-underlined::after) {
  border-color: var(--r-color-brand-primary);
}

/* ── Solo / filled — subtle bg, no border ──────────────────────── */

.r-text-field :deep(.v-field--variant-solo),
.r-text-field :deep(.v-field--variant-solo-filled),
.r-text-field :deep(.v-field--variant-filled) {
  background: var(--r-color-surface);
  box-shadow: none;
}
.r-text-field :deep(.v-field--variant-solo.v-field--focused),
.r-text-field :deep(.v-field--variant-solo-filled.v-field--focused),
.r-text-field :deep(.v-field--variant-filled.v-field--focused) {
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--r-color-brand-primary) 60%, transparent);
}

/* ────────────────────────────────────────────────────────────────
   Inline-label variant — label-prefix on the left, input on the
   right, single bordered container around both. The Vuetify
   floating label is suppressed (we passed `:label="undefined"`)
   and the prepend-inner slot hosts the `#label` slot content.
   ──────────────────────────────────────────────────────────────── */

.r-text-field--inline-label :deep(.v-field) {
  background: var(--r-color-surface);
  overflow: hidden;
  /* Reset Vuetify's outline pieces so the wrapper border is one
     continuous frame instead of the 4-piece notched look. */
  border: 1px solid var(--r-color-border);
}
.r-text-field--inline-label :deep(.v-field__outline) {
  display: none;
}
.r-text-field--inline-label:hover :deep(.v-field) {
  border-color: var(--r-color-border-strong);
}
.r-text-field--inline-label :deep(.v-field--focused) {
  border-color: var(--r-color-brand-primary);
}
.r-text-field--inline-label :deep(.v-field--error) {
  border-color: var(--r-color-danger);
}

/* The label "well" on the left — slightly darker bg, hairline divider
   to the input area. */
.r-text-field--inline-label :deep(.v-field__prepend-inner) {
  width: var(--rtf-label-w, 120px);
  min-width: var(--rtf-label-w, 120px);
  padding: 0 14px;
  align-self: stretch;
  display: flex;
  align-items: center;
  background: var(--r-color-bg-elevated);
  border-right: 1px solid var(--r-color-border);
  color: var(--r-color-fg-secondary);
  /* Reset Vuetify's default top padding for prepend-inner. */
  padding-top: 0;
}
.r-text-field--inline-label :deep(.v-field--focused .v-field__prepend-inner) {
  border-right-color: var(--r-color-brand-primary);
}
.r-text-field--inline-label :deep(.v-field--error .v-field__prepend-inner) {
  border-right-color: var(--r-color-danger);
}

.r-text-field__inline-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--r-color-fg-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.r-text-field--inline-label
  :deep(.v-field--focused)
  .r-text-field__inline-label {
  color: var(--r-color-brand-primary);
}
.r-text-field--inline-label :deep(.v-field--error) .r-text-field__inline-label {
  color: var(--r-color-danger);
}

/* Input area — let it breathe inside the field, no extra padding-top
   since there's no floating label to make room for. */
.r-text-field--inline-label :deep(.v-field__field) {
  flex: 1;
  min-width: 0;
}
.r-text-field--inline-label :deep(.v-field__input) {
  padding: 10px 14px;
  min-height: 38px;
}

/* Append icons (clear button etc.) sit on the right inside the input
   area, no special styling needed. */
</style>
