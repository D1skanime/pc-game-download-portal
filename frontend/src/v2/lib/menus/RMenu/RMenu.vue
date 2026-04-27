<script setup lang="ts">
import type { Anchor } from "vuetify";
import { VMenu } from "vuetify/components/VMenu";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: boolean;
  closeOnContentClick?: boolean;
  location?: Anchor;
  offset?: string | number | number[];
  openOnHover?: boolean;
  openOnClick?: boolean;
  transition?: string;
}

withDefaults(defineProps<Props>(), {
  location: "bottom",
  offset: 8,
  closeOnContentClick: true,
  transition: "scale-transition",
  openOnClick: true,
});

defineEmits<{
  (e: "update:modelValue", v: boolean): void;
}>();
</script>

<template>
  <VMenu
    v-bind="$attrs"
    :model-value="modelValue"
    :close-on-content-click="closeOnContentClick"
    :location="location"
    :offset="offset"
    :open-on-hover="openOnHover"
    :open-on-click="openOnClick"
    :transition="transition"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VMenu>
</template>
