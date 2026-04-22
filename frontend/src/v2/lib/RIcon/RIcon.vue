<script setup lang="ts">
import { VIcon } from "vuetify/components/VIcon";

defineOptions({ inheritAttrs: false });

interface Props {
  icon?: string;
  size?: string | number;
  color?: string;
}

withDefaults(defineProps<Props>(), {
  icon: undefined,
  size: undefined,
  color: undefined,
});
</script>

<template>
  <VIcon v-bind="$attrs" :icon="icon" :size="size" :color="color">
    <slot />
  </VIcon>
</template>
