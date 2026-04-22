<script setup lang="ts">
import { VBtn } from "vuetify/components/VBtn";

defineOptions({ inheritAttrs: false });

// RBtn — thin wrapper around v-btn with RomM v2 defaults:
//   - variant="flat" (our primary visual style)
//   - color="primary"
//   - rounded="md"
//   - font-weight medium, no uppercase (Vuetify's default)
// Every Vuetify prop remains available via $attrs.
interface Props {
  variant?: "flat" | "text" | "elevated" | "tonal" | "outlined" | "plain";
  color?: string;
  rounded?: string | number | boolean;
  loading?: boolean;
  disabled?: boolean;
  block?: boolean;
  size?: "x-small" | "small" | "default" | "large" | "x-large";
  prependIcon?: string;
  appendIcon?: string;
  type?: "button" | "submit" | "reset";
}

withDefaults(defineProps<Props>(), {
  variant: "flat",
  color: "primary",
  rounded: "md",
  size: "default",
  type: "button",
  prependIcon: undefined,
  appendIcon: undefined,
});
</script>

<template>
  <VBtn
    v-bind="$attrs"
    class="r-btn"
    :variant="variant"
    :color="color"
    :rounded="rounded"
    :loading="loading"
    :disabled="disabled"
    :block="block"
    :size="size"
    :prepend-icon="prependIcon"
    :append-icon="appendIcon"
    :type="type"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VBtn>
</template>

<style scoped>
.r-btn {
  font-weight: var(--r-font-weight-medium);
  letter-spacing: 0;
}
</style>
