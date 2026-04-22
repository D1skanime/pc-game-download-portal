<script setup lang="ts">
import { VProgressCircular } from "vuetify/components/VProgressCircular";

defineOptions({ inheritAttrs: false });

interface Props {
  indeterminate?: boolean;
  size?: number | string;
  width?: number | string;
  color?: string;
  modelValue?: number;
}

withDefaults(defineProps<Props>(), {
  indeterminate: true,
  size: 24,
  width: 2,
  color: "primary",
  modelValue: undefined,
});
</script>

<template>
  <VProgressCircular
    v-bind="$attrs"
    :indeterminate="indeterminate"
    :size="size"
    :width="width"
    :color="color"
    :model-value="modelValue"
  >
    <slot />
  </VProgressCircular>
</template>
