<script setup lang="ts">
import { VRating } from "vuetify/components/VRating";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: number;
  length?: number | string;
  color?: string;
  activeColor?: string;
  size?:
    | "x-small"
    | "small"
    | "default"
    | "large"
    | "x-large"
    | string
    | number;
  readonly?: boolean;
  halfIncrements?: boolean;
  density?: "default" | "comfortable" | "compact";
  hover?: boolean;
  itemLabels?: string[];
}

withDefaults(defineProps<Props>(), {
  modelValue: 0,
  length: 5,
  color: "romm-gold",
  activeColor: "romm-gold",
  size: "default",
  density: "default",
  itemLabels: undefined,
});

defineEmits<{
  (e: "update:modelValue", value: number): void;
}>();
</script>

<template>
  <VRating
    v-bind="$attrs"
    :model-value="modelValue"
    :length="length"
    :color="color"
    :active-color="activeColor"
    :size="size"
    :readonly="readonly"
    :half-increments="halfIncrements"
    :density="density"
    :hover="hover"
    :item-labels="itemLabels"
    @update:model-value="(v) => $emit('update:modelValue', Number(v))"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VRating>
</template>
