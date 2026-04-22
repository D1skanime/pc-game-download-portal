<script setup lang="ts">
import type { Anchor } from "vuetify";
import { VBadge } from "vuetify/components/VBadge";

defineOptions({ inheritAttrs: false });

interface Props {
  content?: string | number;
  color?: string;
  dot?: boolean;
  bordered?: boolean;
  inline?: boolean;
  location?: Anchor;
  modelValue?: boolean;
  floating?: boolean;
  max?: number;
  icon?: string;
}

withDefaults(defineProps<Props>(), {
  content: undefined,
  color: "error",
  location: "top end",
  modelValue: true,
  max: 99,
  icon: undefined,
});
</script>

<template>
  <VBadge
    v-bind="$attrs"
    :content="content"
    :color="color"
    :dot="dot"
    :bordered="bordered"
    :inline="inline"
    :location="location"
    :model-value="modelValue"
    :floating="floating"
    :max="max"
    :icon="icon"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VBadge>
</template>
