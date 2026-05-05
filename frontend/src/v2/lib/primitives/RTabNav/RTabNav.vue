<script setup lang="ts">
// RTabNav — single component, two visual presentations:
//   * variant="underlined" (default) — horizontal nav with a brand
//     underline on active. Used for primary tabs and tight subtabs.
//   * variant="pill" — stacked menu-like items with a soft rounded
//     fill on active. Pairs naturally with `orientation="vertical"`
//     for left-rail subtabs (SaveDataTab style).
//
// Items can carry an optional leading icon and an optional badge
// (string | number). Items with `show: false` are filtered out so
// callers can pass a single declarative source.
import { RIcon } from "@v2/lib";
import type { RTabNavItem } from "./types";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue: string;
  items: RTabNavItem[];
  size?: "sm" | "md";
  variant?: "underlined" | "pill";
  orientation?: "horizontal" | "vertical";
}

withDefaults(defineProps<Props>(), {
  size: "md",
  variant: "underlined",
  orientation: "horizontal",
});

defineEmits<{
  (e: "update:modelValue", v: string): void;
}>();
</script>

<template>
  <nav
    class="r-tab-nav"
    :class="[
      `r-tab-nav--${size}`,
      `r-tab-nav--${variant}`,
      `r-tab-nav--${orientation}`,
    ]"
    role="tablist"
    :aria-orientation="orientation"
  >
    <button
      v-for="t in items.filter((x) => x.show !== false)"
      :key="t.id"
      type="button"
      role="tab"
      class="r-tab-nav__btn"
      :class="{ 'r-tab-nav__btn--active': modelValue === t.id }"
      :aria-selected="modelValue === t.id"
      @click="$emit('update:modelValue', t.id)"
    >
      <RIcon v-if="t.icon" :icon="t.icon" class="r-tab-nav__icon" />
      <span class="r-tab-nav__label">{{ t.label }}</span>
      <span
        v-if="t.badge !== undefined && t.badge !== null && t.badge !== ''"
        class="r-tab-nav__badge"
      >
        {{ t.badge }}
      </span>
    </button>
  </nav>
</template>

<style scoped>
.r-tab-nav {
  display: flex;
  gap: 0;
}
.r-tab-nav--horizontal {
  flex-direction: row;
  overflow-x: auto;
  scrollbar-width: none;
}
.r-tab-nav--horizontal::-webkit-scrollbar {
  display: none;
}
.r-tab-nav--vertical {
  flex-direction: column;
}

.r-tab-nav__btn {
  appearance: none;
  background: transparent;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: inherit;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg-muted);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-tab-nav__btn:hover {
  color: var(--r-color-fg-secondary);
}
.r-tab-nav__icon {
  flex-shrink: 0;
}
.r-tab-nav__label {
  flex: 1;
  text-align: left;
}

/* ---------- Underlined variant (horizontal only) ---------- */
.r-tab-nav--underlined {
  border-bottom: 1px solid var(--r-color-border-strong);
}
.r-tab-nav--underlined .r-tab-nav__btn {
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  border-radius: 0;
}
.r-tab-nav--underlined .r-tab-nav__btn--active {
  color: var(--r-color-fg);
  border-bottom-color: var(--r-color-brand-primary);
}
.r-tab-nav--underlined.r-tab-nav--md .r-tab-nav__btn {
  padding: 8px 18px;
  font-size: 13px;
}
.r-tab-nav--underlined.r-tab-nav--sm .r-tab-nav__btn {
  padding: 6px 12px;
  font-size: 12px;
}

/* ---------- Pill variant ---------- */
.r-tab-nav--pill {
  gap: 4px;
}
.r-tab-nav--pill .r-tab-nav__btn {
  border-radius: var(--r-radius-md);
  background: transparent;
}
.r-tab-nav--pill .r-tab-nav__btn:hover {
  background: var(--r-color-surface-hover);
  color: var(--r-color-fg);
}
.r-tab-nav--pill .r-tab-nav__btn--active {
  background: color-mix(in srgb, var(--r-color-brand-primary) 18%, transparent);
  color: var(--r-color-brand-primary);
}
.r-tab-nav--pill .r-tab-nav__btn--active .r-tab-nav__icon {
  color: var(--r-color-brand-primary);
}
.r-tab-nav--pill.r-tab-nav--md .r-tab-nav__btn {
  padding: 10px 14px;
  font-size: 13px;
}
.r-tab-nav--pill.r-tab-nav--sm .r-tab-nav__btn {
  padding: 8px 12px;
  font-size: 12px;
}

/* ---------- Badge ---------- */
.r-tab-nav__badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: var(--r-radius-full);
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border);
  color: var(--r-color-fg-muted);
  font-size: 10.5px;
  font-weight: var(--r-font-weight-semibold);
  font-variant-numeric: tabular-nums;
  line-height: 1.4;
  flex-shrink: 0;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-tab-nav__btn--active .r-tab-nav__badge {
  background: color-mix(in srgb, var(--r-color-brand-primary) 18%, transparent);
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 50%,
    transparent
  );
  color: var(--r-color-brand-primary);
}

@media (max-width: 768px) {
  .r-tab-nav--underlined.r-tab-nav--md .r-tab-nav__btn {
    padding: 8px 14px;
    font-size: 12px;
  }
}
</style>
