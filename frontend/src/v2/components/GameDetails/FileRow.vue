<script setup lang="ts">
// FileRow — label (uppercase eyebrow) over value. Used by the FilesTab on
// GameDetails. `mono` renders the value as a monospace chip for hashes
// and paths.

defineOptions({ inheritAttrs: false });

interface Props {
  label?: string;
  value?: string | number;
  mono?: boolean;
}

withDefaults(defineProps<Props>(), {
  label: undefined,
  value: undefined,
  mono: false,
});
</script>

<template>
  <div class="file-row">
    <div class="file-row__label">
      <slot name="label">{{ label }}</slot>
    </div>
    <div class="file-row__value" :class="{ 'file-row__value--mono': mono }">
      <slot>{{ value }}</slot>
    </div>
  </div>
</template>

<style scoped>
.file-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-row__label {
  font-size: 10.5px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
}

.file-row__value {
  font-size: 13px;
  color: var(--r-color-fg-secondary);
  word-break: break-all;
}

.file-row__value--mono {
  font-family: var(--r-font-family-mono);
  font-size: 11px;
  color: var(--r-color-fg-secondary);
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border-strong);
  border-radius: var(--r-radius-chip);
  padding: 4px 10px;
  align-self: flex-start;
  max-width: 100%;
}
</style>
