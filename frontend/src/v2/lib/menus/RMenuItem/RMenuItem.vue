<script setup lang="ts">
// RMenuItem — clickable row used inside RMenuPanel.
//
// Renders either a `<button>` (default) or `<router-link>` when `to` is set,
// or an `<a>` when `href` is set. Stays visually consistent across all use
// cases: 15px leading-icon slot (left), label, 9px rounded hover bg.
//
// Variants:
//   * default — white-ish text, hover background rgba(255,255,255,0.09)
//   * active  — filled accent (favourited style, brand "--r-color-fav")
//   * danger  — red text, red-tinted hover (destructive actions)
import { computed } from "vue";

defineOptions({ inheritAttrs: false });

type Variant = "default" | "active" | "danger";

interface Props {
  label?: string;
  icon?: string; // optional mdi class — falls back to the slot
  variant?: Variant;
  disabled?: boolean;
  // Routing — mutually exclusive; if neither is set we render a button.
  to?: string | object;
  href?: string;
  // `closeOnClick` makes the menu parent close when true (default). Handled
  // by the parent (RMenu auto-closes); this prop is mainly documentation
  // for consumers that wire their own open state.
  closeOnClick?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  label: undefined,
  icon: undefined,
  variant: "default",
  to: undefined,
  href: undefined,
  closeOnClick: true,
});

defineEmits<{
  (e: "click", event: MouseEvent): void;
}>();

const tag = computed(() => {
  if (props.to) return "router-link";
  if (props.href) return "a";
  return "button";
});
</script>

<template>
  <component
    :is="tag"
    v-bind="$attrs"
    :to="to"
    :href="href"
    :type="tag === 'button' ? 'button' : undefined"
    :role="tag === 'button' ? undefined : 'menuitem'"
    :disabled="disabled"
    class="r-menu-item"
    :class="{
      'r-menu-item--active': variant === 'active',
      'r-menu-item--danger': variant === 'danger',
      'r-menu-item--disabled': disabled,
    }"
    @click="(e: MouseEvent) => !disabled && $emit('click', e)"
  >
    <span class="r-menu-item__icon">
      <slot name="icon">
        <!-- Use Vuetify v-icon glyph if `icon` is set. -->
        <i v-if="icon" :class="['mdi', icon]" aria-hidden="true" />
      </slot>
    </span>
    <span class="r-menu-item__label">
      <slot>{{ label }}</slot>
    </span>
    <slot name="append" />
  </component>
</template>

<style scoped>
.r-menu-item {
  appearance: none;
  border: 0;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 12px;
  border-radius: 9px;
  cursor: pointer;
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: rgba(255, 255, 255, 0.8);
  font-family: inherit;
  text-align: left;
  text-decoration: none;
  width: 100%;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
  user-select: none;
}

.r-v2.r-v2-light .r-menu-item {
  color: rgba(17, 17, 23, 0.85);
}

.r-menu-item:hover:not(.r-menu-item--disabled) {
  background: rgba(255, 255, 255, 0.09);
  color: #fff;
}

.r-v2.r-v2-light .r-menu-item:hover:not(.r-menu-item--disabled) {
  background: rgba(17, 17, 23, 0.07);
  color: var(--r-color-fg);
}

.r-menu-item__icon {
  flex-shrink: 0;
  width: 15px;
  height: 15px;
  display: grid;
  place-items: center;
  color: currentColor;
  opacity: 0.65;
  transition: opacity var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-menu-item:hover:not(.r-menu-item--disabled) .r-menu-item__icon {
  opacity: 1;
}

.r-menu-item__icon :deep(svg) {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.r-menu-item__icon :deep(.mdi) {
  font-size: 17px;
  line-height: 1;
}

.r-menu-item__label {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Active: filled "fav" colour */
.r-menu-item--active,
.r-menu-item--active:hover {
  color: var(--r-color-fav);
}
.r-menu-item--active .r-menu-item__icon {
  opacity: 1;
}
.r-menu-item--active .r-menu-item__icon :deep(svg) {
  fill: currentColor;
  stroke: currentColor;
}

/* Danger: destructive actions */
.r-menu-item--danger {
  color: rgba(255, 90, 90, 0.85);
}
.r-menu-item--danger:hover:not(.r-menu-item--disabled) {
  background: rgba(255, 80, 80, 0.12);
  color: #ff5050;
}

/* Disabled */
.r-menu-item--disabled {
  opacity: 0.45;
  cursor: default;
}
</style>
