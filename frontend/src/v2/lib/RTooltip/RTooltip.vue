<script setup lang="ts">
import type { Anchor } from "vuetify";
import { VTooltip } from "vuetify/components/VTooltip";

defineOptions({ inheritAttrs: false });

interface Props {
  text?: string;
  location?: Anchor;
  openDelay?: number | string;
  modelValue?: boolean;
}

withDefaults(defineProps<Props>(), {
  text: undefined,
  location: "bottom",
  openDelay: 400,
});
</script>

<template>
  <VTooltip
    v-bind="$attrs"
    :text="text"
    :location="location"
    :open-delay="openDelay"
    :model-value="modelValue"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VTooltip>
</template>
