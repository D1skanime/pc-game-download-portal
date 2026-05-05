<script setup lang="ts">
// REmptyState — generic "nothing here yet" placeholder.
// Used wherever a list / panel can have zero items: media subtabs,
// save data subtabs, empty filters. Icon + title + optional hint +
// optional `actions` slot for CTAs (primitive contract: text via
// props/slots, no i18n inside).
import { RIcon } from "@v2/lib";

defineOptions({ inheritAttrs: false });

interface Props {
  icon?: string;
  title?: string;
  hint?: string;
  iconSize?: string | number;
  size?: "compact" | "default";
}

withDefaults(defineProps<Props>(), {
  icon: "mdi-tray-remove",
  iconSize: 48,
  size: "default",
});
</script>

<template>
  <div class="r-empty-state" :class="`r-empty-state--${size}`">
    <slot name="icon">
      <RIcon :icon="icon" :size="iconSize" />
    </slot>
    <div v-if="title || $slots.title" class="r-empty-state__title">
      <slot name="title">{{ title }}</slot>
    </div>
    <div v-if="hint || $slots.hint" class="r-empty-state__hint">
      <slot name="hint">{{ hint }}</slot>
    </div>
    <div v-if="$slots.actions" class="r-empty-state__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.r-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--r-space-3);
  padding: var(--r-space-10) var(--r-space-6);
  background: var(--r-color-bg-elevated);
  border: 1px dashed var(--r-color-border);
  border-radius: var(--r-radius-md);
  text-align: center;
  color: var(--r-color-fg-muted);
}
.r-empty-state--compact {
  padding: var(--r-space-6) var(--r-space-4);
  gap: var(--r-space-2);
}

.r-empty-state__title {
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
}
.r-empty-state--compact .r-empty-state__title {
  font-size: var(--r-font-size-md);
}

.r-empty-state__hint {
  max-width: 440px;
  font-size: var(--r-font-size-sm);
  line-height: var(--r-line-height-relaxed);
}

.r-empty-state__actions {
  display: flex;
  gap: var(--r-space-2);
  flex-wrap: wrap;
  justify-content: center;
  margin-top: var(--r-space-2);
}
</style>
