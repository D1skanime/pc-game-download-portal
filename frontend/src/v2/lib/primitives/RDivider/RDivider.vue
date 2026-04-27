<script setup lang="ts">
import { VDivider } from "vuetify/components/VDivider";

defineOptions({ inheritAttrs: false });

interface Props {
  vertical?: boolean;
  inset?: boolean;
  thickness?: number | string;
}

withDefaults(defineProps<Props>(), {
  thickness: undefined,
});
</script>

<template>
  <VDivider
    v-bind="$attrs"
    :vertical="vertical"
    :inset="inset"
    :thickness="thickness"
  >
    <template v-if="$slots.default" #default>
      <slot />
    </template>
  </VDivider>
</template>
