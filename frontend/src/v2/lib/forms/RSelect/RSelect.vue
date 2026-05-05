<script setup lang="ts">
import { computed } from "vue";
import { VSelect } from "vuetify/components/VSelect";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: unknown;
  items?: unknown[];
  label?: string;
  variant?:
    | "filled"
    | "outlined"
    | "plain"
    | "underlined"
    | "solo"
    | "solo-inverted"
    | "solo-filled";
  density?: "default" | "comfortable" | "compact";
  itemTitle?: string | ((item: unknown) => string);
  itemValue?: string | ((item: unknown) => unknown);
  multiple?: boolean;
  clearable?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  hideDetails?: boolean | "auto";
  prependInnerIcon?: string;
  appendInnerIcon?: string;
  placeholder?: string;
  chips?: boolean;
  closableChips?: boolean;
  /** Forwarded to VSelect; the v2 panel `contentClass` is merged in so
   *  callers can still set `location`, `offset`, etc. without losing
   *  the panel styling. */
  menuProps?: Record<string, unknown>;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  items: () => [],
  label: undefined,
  variant: "outlined",
  density: "default",
  itemTitle: "title",
  itemValue: "value",
  hideDetails: false,
  prependInnerIcon: undefined,
  appendInnerIcon: undefined,
  placeholder: undefined,
  menuProps: () => ({}),
});

defineEmits<{
  (e: "update:modelValue", value: unknown): void;
}>();

// Always inject the panel content-class so the unscoped overlay
// styles below resolve. If the caller supplies their own
// contentClass we keep both.
const mergedMenuProps = computed(() => {
  const callerClass = props.menuProps.contentClass;
  const own = "r-select__menu";
  const contentClass = callerClass ? [own, callerClass].flat() : own;
  return { ...props.menuProps, contentClass };
});
</script>

<template>
  <VSelect
    v-bind="$attrs"
    class="r-select"
    :model-value="modelValue"
    :items="items as never"
    :label="label"
    :variant="variant"
    :density="density"
    :item-title="itemTitle as never"
    :item-value="itemValue as never"
    :multiple="multiple"
    :clearable="clearable"
    :disabled="disabled"
    :readonly="readonly"
    :hide-details="hideDetails"
    :prepend-inner-icon="prependInnerIcon"
    :append-inner-icon="appendInnerIcon"
    :placeholder="placeholder"
    :chips="chips"
    :closable-chips="closableChips"
    menu-icon="mdi-chevron-down"
    :menu-props="mergedMenuProps"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VSelect>
</template>

<style scoped>
/* Glass-pill look — applied to every RSelect so all the page selects
   share aesthetics (header language picker, Overview status picker,
   Media manual picker…). Vuetify's outlined variant ships with a
   2-piece notched border (`v-field__outline`) that we hide and replace
   with one continuous pill border on the field itself. */
.r-select :deep(.v-field) {
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border-strong);
  border-radius: var(--r-radius-pill);
  color: var(--r-color-fg-secondary);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-select :deep(.v-field__outline) {
  display: none;
}
.r-select :deep(.v-field:hover) {
  background: var(--r-color-surface-hover);
  color: var(--r-color-fg);
}
.r-select :deep(.v-field--focused) {
  background: var(--r-color-surface-hover);
  border-color: var(--r-color-brand-primary);
  color: var(--r-color-fg);
}
.r-select :deep(.v-field__input),
.r-select :deep(.v-select__selection-text) {
  color: inherit;
  font-size: 12.5px;
  font-weight: var(--r-font-weight-medium);
}
.r-select :deep(.v-field__prepend-inner > .v-icon),
.r-select :deep(.v-field__append-inner > .v-icon) {
  opacity: 0.7;
  color: inherit;
}
.r-select :deep(.v-field--focused .v-field__prepend-inner > .v-icon),
.r-select :deep(.v-field--focused .v-field__append-inner > .v-icon) {
  opacity: 1;
}
</style>

<!-- Teleport overrides — VSelect renders its menu into the
     `.v-overlay-container` outside any scoped subtree, so styles for
     it have to be unscoped. The shared panel paint
     (background + blur + border + radius + shadow) lives in
     `global.css` so RSelect's dropdown matches RMenu's popups
     pixel-for-pixel. Here we only style the inner list + rows so they
     mirror RMenuItem. -->
<style>
.r-select__menu .v-list {
  background: transparent !important;
  padding: 6px !important;
  color: var(--r-color-fg);
  font-family: var(--r-font-family-sans);
}

/* Vuetify paints `.v-list-item__overlay` (full-bleed cover) on
   hover/active — kill it so the rounded background we paint on the
   row itself is what shows. Same trick for the focus underlay. */
.r-select__menu .v-list-item__overlay,
.r-select__menu .v-list-item__underlay {
  display: none !important;
}

/* Items — RMenuItem visual: 9px radius, 9px 12px padding, gap 11px,
   13px medium text, surface hover. !important needed because Vuetify
   ships these via theme-scoped rules with higher specificity. */
.r-select__menu .v-list-item {
  display: flex !important;
  align-items: center;
  gap: 11px;
  min-height: 0 !important;
  padding: 9px 12px !important;
  border-radius: 9px !important;
  margin-bottom: 2px;
  font-size: 13px !important;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg-secondary);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-select__menu .v-list-item:last-child {
  margin-bottom: 0;
}
.r-select__menu .v-list-item:hover,
.r-select__menu .v-list-item:focus-visible,
.r-select__menu .v-list-item--active {
  background: var(--r-color-surface) !important;
  color: var(--r-color-fg) !important;
}
/* Selected option — same surface bg as hover, plus a brand-tinted
   tone so the user sees "this is the current value". */
.r-select__menu .v-list-item--active {
  color: var(--r-color-brand-primary) !important;
}
.r-select__menu .v-list-item-title {
  font-size: inherit;
  font-weight: inherit;
}
</style>
