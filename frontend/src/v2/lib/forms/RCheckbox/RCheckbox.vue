<script setup lang="ts">
import { VCheckbox } from "vuetify/components/VCheckbox";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: boolean | null;
  label?: string;
  color?: string;
  density?: "default" | "comfortable" | "compact";
  disabled?: boolean;
  indeterminate?: boolean;
  hideDetails?: boolean | "auto";
}

withDefaults(defineProps<Props>(), {
  modelValue: false,
  label: undefined,
  color: "primary",
  density: "comfortable",
  hideDetails: "auto",
});

defineEmits<{
  (e: "update:modelValue", value: boolean | null): void;
}>();
</script>

<template>
  <VCheckbox
    v-bind="$attrs"
    :model-value="modelValue"
    :label="label"
    :color="color"
    :density="density"
    :disabled="disabled"
    :indeterminate="indeterminate"
    :hide-details="hideDetails"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VCheckbox>
</template>
