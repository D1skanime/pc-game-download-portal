<script setup lang="ts">
// RExpansionPanel — single disclosure panel matching the v2 panel
// vocabulary (token-driven background, soft border, rounded corners).
// Header is a button row with optional icon + title + chevron; content
// slot expands smoothly via CSS grid trick (no JS height measurement).
//
// `modelValue` controls open state; `defaultOpen` provides the initial
// uncontrolled value when no v-model is bound.
import { RIcon } from "@v2/lib";
import { computed, ref, watch } from "vue";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: boolean;
  defaultOpen?: boolean;
  title?: string;
  icon?: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  defaultOpen: false,
  title: undefined,
  icon: undefined,
  disabled: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
}>();

// Uncontrolled mode: keep our own ref. Controlled mode: prop is the
// source of truth, we never write the local ref.
const isControlled = computed(() => props.modelValue !== undefined);
const localOpen = ref(props.defaultOpen);
const open = computed(() =>
  isControlled.value ? Boolean(props.modelValue) : localOpen.value,
);

watch(
  () => props.modelValue,
  (v) => {
    if (v !== undefined) localOpen.value = v;
  },
);

function toggle() {
  if (props.disabled) return;
  const next = !open.value;
  if (!isControlled.value) localOpen.value = next;
  emit("update:modelValue", next);
}
</script>

<template>
  <div
    class="r-expansion-panel"
    :class="{
      'r-expansion-panel--open': open,
      'r-expansion-panel--disabled': disabled,
    }"
  >
    <button
      type="button"
      class="r-expansion-panel__header"
      :aria-expanded="open"
      :disabled="disabled"
      @click="toggle"
    >
      <RIcon v-if="icon" :icon="icon" class="r-expansion-panel__icon" />
      <span class="r-expansion-panel__title">
        <slot name="title">{{ title }}</slot>
      </span>
      <RIcon icon="mdi-chevron-down" class="r-expansion-panel__chevron" />
    </button>

    <div class="r-expansion-panel__content-wrap" :hidden="!open">
      <div class="r-expansion-panel__content">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.r-expansion-panel {
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  overflow: hidden;
  transition: border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-expansion-panel--open {
  border-color: var(--r-color-border-strong);
}
.r-expansion-panel--disabled {
  opacity: 0.5;
}

.r-expansion-panel__header {
  appearance: none;
  border: 0;
  background: transparent;
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
  padding: var(--r-space-4) var(--r-space-5);
  font-family: inherit;
  font-size: var(--r-font-size-md);
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
  cursor: pointer;
  transition: background var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-expansion-panel__header:hover:not(:disabled) {
  background: var(--r-color-surface-hover);
}
.r-expansion-panel__header:disabled {
  cursor: not-allowed;
}

.r-expansion-panel__icon {
  color: var(--r-color-fg-muted);
}

.r-expansion-panel__title {
  flex: 1;
  text-align: left;
}

.r-expansion-panel__chevron {
  color: var(--r-color-fg-muted);
  transition: transform var(--r-motion-med) var(--r-motion-ease-out);
}
.r-expansion-panel--open .r-expansion-panel__chevron {
  transform: rotate(180deg);
}

/* Smooth open via grid-row trick — content height interpolates without
   a measured pixel value, so it works for any content. */
.r-expansion-panel__content-wrap {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows var(--r-motion-med) var(--r-motion-ease-out);
}
.r-expansion-panel__content-wrap[hidden] {
  display: grid;
}
.r-expansion-panel--open .r-expansion-panel__content-wrap {
  grid-template-rows: 1fr;
}
.r-expansion-panel__content {
  min-height: 0;
  overflow: hidden;
}
.r-expansion-panel--open .r-expansion-panel__content {
  overflow: visible;
}

.r-expansion-panel__content > :first-child {
  padding: 0 var(--r-space-5) var(--r-space-5);
}
</style>
