<script setup lang="ts">
import { VToolbar } from "vuetify/components/VToolbar";

defineOptions({ inheritAttrs: false });

interface Props {
  color?: string;
  density?: "default" | "comfortable" | "compact";
  flat?: boolean;
  title?: string;
  height?: number | string;
  rounded?: string | number | boolean;
}

withDefaults(defineProps<Props>(), {
  color: undefined,
  density: "default",
  title: undefined,
  height: undefined,
  rounded: undefined,
});
</script>

<template>
  <VToolbar
    v-bind="$attrs"
    class="r-toolbar"
    :color="color"
    :density="density"
    :flat="flat"
    :title="title"
    :height="height"
    :rounded="rounded"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VToolbar>
</template>

<style scoped>
.r-toolbar {
  background-color: var(--r-color-bg-elevated);
  border-bottom: 1px solid var(--r-color-border);
}
</style>
