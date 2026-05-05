<script setup lang="ts">
// RSlider — thin wrapper around v-slider with v2 defaults.
// Accepts the full Vuetify slider API via $attrs. The model is coerced
// to number on emit so consumers always receive `number` (Vuetify can
// emit `number | string` when `step` is a string).
import { VSlider } from "vuetify/components/VSlider";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: number;
  min?: number;
  max?: number;
  step?: number;
  color?: string;
  trackColor?: string;
  thumbColor?: string;
  size?:
    | "x-small"
    | "small"
    | "default"
    | "large"
    | "x-large"
    | string
    | number;
  density?: "default" | "comfortable" | "compact";
  hideDetails?: boolean | "auto";
  disabled?: boolean;
  readonly?: boolean;
  thumbLabel?: boolean | "always";
}

withDefaults(defineProps<Props>(), {
  modelValue: 0,
  min: 0,
  max: 100,
  step: 1,
  color: "primary",
  trackColor: undefined,
  thumbColor: undefined,
  size: "default",
  density: "default",
  hideDetails: true,
});

defineEmits<{
  (e: "update:modelValue", value: number): void;
}>();
</script>

<template>
  <VSlider
    v-bind="$attrs"
    class="r-slider"
    :model-value="modelValue"
    :min="min"
    :max="max"
    :step="step"
    :color="color"
    :track-color="trackColor"
    :thumb-color="thumbColor"
    :size="size"
    :density="density"
    :hide-details="hideDetails"
    :disabled="disabled"
    :readonly="readonly"
    :thumb-label="thumbLabel"
    @update:model-value="(v) => $emit('update:modelValue', Number(v))"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VSlider>
</template>

<style scoped>
/* Smoother drag — Vuetify defaults are a touch snappy. */
.r-slider :deep(.v-slider-thumb__surface) {
  transition:
    box-shadow var(--r-motion-fast) var(--r-motion-ease-out),
    transform var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-slider :deep(.v-slider-thumb:hover .v-slider-thumb__surface),
.r-slider :deep(.v-slider-thumb--focused .v-slider-thumb__surface) {
  transform: scale(1.1);
}
</style>
