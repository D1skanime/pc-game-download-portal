<script setup lang="ts">
// DetailsTabs — underlined tab nav for GameDetails.
//
// Parent owns the active-tab state (mirrored to `?tab=` in the URL) and
// feeds us a `tabs` array of `{ id, label, visible? }`. Hidden tabs aren't
// rendered so the nav doesn't have dead chips.

defineOptions({ inheritAttrs: false });

type Tab = {
  id: string;
  label: string;
  show?: boolean;
};

defineProps<{
  modelValue: string;
  tabs: Tab[];
}>();

defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();
</script>

<template>
  <nav class="r-v2-det-tabs" role="tablist">
    <button
      v-for="t in tabs.filter((x) => x.show !== false)"
      :key="t.id"
      type="button"
      role="tab"
      :class="[
        'r-v2-det-tabs__btn',
        { 'r-v2-det-tabs__btn--active': modelValue === t.id },
      ]"
      :aria-selected="modelValue === t.id"
      @click="$emit('update:modelValue', t.id)"
    >
      {{ t.label }}
    </button>
  </nav>
</template>

<style scoped>
.r-v2-det-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--r-color-border-strong);
  margin: 14px 0 16px;
  overflow-x: auto;
  scrollbar-width: none;
}
.r-v2-det-tabs::-webkit-scrollbar {
  display: none;
}

.r-v2-det-tabs__btn {
  appearance: none;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg-muted);
  cursor: pointer;
  white-space: nowrap;
  transition:
    color var(--r-motion-fast),
    border-color var(--r-motion-fast);
  font-family: inherit;
}
.r-v2-det-tabs__btn:hover {
  color: var(--r-color-fg-secondary);
}
.r-v2-det-tabs__btn--active {
  color: var(--r-color-fg);
  border-bottom-color: var(--r-color-fg);
}

@media (max-width: 768px) {
  .r-v2-det-tabs__btn {
    padding: 8px 14px;
    font-size: 12px;
  }
}
</style>
