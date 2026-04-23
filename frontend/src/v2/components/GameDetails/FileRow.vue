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
  color: rgba(255, 255, 255, 0.28);
}

:global(.r-v2.r-v2-light) .file-row__label {
  color: var(--r-color-fg-muted);
}

.file-row__value {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  word-break: break-all;
}

:global(.r-v2.r-v2-light) .file-row__value {
  color: var(--r-color-fg);
}

.file-row__value--mono {
  font-family: var(--r-font-family-mono);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--r-radius-chip);
  padding: 4px 10px;
  align-self: flex-start;
  max-width: 100%;
}
</style>
