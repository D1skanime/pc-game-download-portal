<script setup lang="ts">
import { VSelect } from "vuetify/components/VSelect";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: unknown;
  items?: unknown[];
  label?: string;
  variant?:
    | "filled"
    | "outlined"
    | "plain"
    | "underlined"
    | "solo"
    | "solo-inverted"
    | "solo-filled";
  density?: "default" | "comfortable" | "compact";
  itemTitle?: string | ((item: unknown) => string);
  itemValue?: string | ((item: unknown) => unknown);
  multiple?: boolean;
  clearable?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  hideDetails?: boolean | "auto";
  prependInnerIcon?: string;
  appendInnerIcon?: string;
  placeholder?: string;
  chips?: boolean;
  closableChips?: boolean;
}

withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  items: () => [],
  label: undefined,
  variant: "outlined",
  density: "default",
  itemTitle: "title",
  itemValue: "value",
  hideDetails: false,
  prependInnerIcon: undefined,
  appendInnerIcon: undefined,
  placeholder: undefined,
});

defineEmits<{
  (e: "update:modelValue", value: unknown): void;
}>();
</script>

<template>
  <VSelect
    v-bind="$attrs"
    class="r-select"
    :model-value="modelValue"
    :items="items as never"
    :label="label"
    :variant="variant"
    :density="density"
    :item-title="itemTitle as never"
    :item-value="itemValue as never"
    :multiple="multiple"
    :clearable="clearable"
    :disabled="disabled"
    :readonly="readonly"
    :hide-details="hideDetails"
    :prepend-inner-icon="prependInnerIcon"
    :append-inner-icon="appendInnerIcon"
    :placeholder="placeholder"
    :chips="chips"
    :closable-chips="closableChips"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VSelect>
</template>
