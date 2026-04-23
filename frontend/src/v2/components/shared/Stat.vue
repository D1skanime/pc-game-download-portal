<script setup lang="ts">
// Stat — KPI column: big value on top, small uppercase label below.
// Feature component; InfoPanel and the gallery hero cards reuse it, but
// it's not general enough to be a design-system primitive.

defineOptions({ inheritAttrs: false });

interface Props {
  value?: string | number;
  label?: string;
}

withDefaults(defineProps<Props>(), {
  value: undefined,
  label: undefined,
});
</script>

<template>
  <div class="stat">
    <div class="stat__value">
      <slot>{{ value }}</slot>
    </div>
    <div class="stat__label">
      <slot name="label">{{ label }}</slot>
    </div>
  </div>
</template>

<style scoped>
.stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.stat__value {
  font-size: var(--r-font-size-2xl);
  font-weight: var(--r-font-weight-bold);
  color: rgba(255, 255, 255, 0.92);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

:global(.r-v2.r-v2-light) .stat__value {
  color: var(--r-color-fg);
}

.stat__label {
  font-size: 10px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.25);
}

:global(.r-v2.r-v2-light) .stat__label {
  color: var(--r-color-fg-muted);
}
</style>
