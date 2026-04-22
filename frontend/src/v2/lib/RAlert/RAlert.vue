<script setup lang="ts">
import { VAlert } from "vuetify/components/VAlert";

defineOptions({ inheritAttrs: false });

interface Props {
  type?: "success" | "info" | "warning" | "error";
  variant?: "flat" | "elevated" | "tonal" | "outlined" | "text";
  closable?: boolean;
  icon?: string | false;
  density?: "default" | "comfortable" | "compact";
  title?: string;
  text?: string;
  rounded?: string | number | boolean;
}

withDefaults(defineProps<Props>(), {
  type: undefined,
  variant: "tonal",
  icon: undefined,
  density: "default",
  title: undefined,
  text: undefined,
  rounded: "md",
});
</script>

<template>
  <VAlert
    v-bind="$attrs"
    class="r-alert"
    :type="type"
    :variant="variant"
    :closable="closable"
    :icon="icon"
    :density="density"
    :title="title"
    :text="text"
    :rounded="rounded"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VAlert>
</template>

<style scoped>
.r-alert {
  font-size: var(--r-font-size-sm);
  line-height: var(--r-line-height-normal);
}
</style>
