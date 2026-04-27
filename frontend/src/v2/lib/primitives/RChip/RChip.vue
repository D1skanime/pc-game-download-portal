<script setup lang="ts">
import { VChip } from "vuetify/components/VChip";

defineOptions({ inheritAttrs: false });

interface Props {
  variant?: "flat" | "text" | "elevated" | "tonal" | "outlined" | "plain";
  color?: string;
  size?: "x-small" | "small" | "default" | "large" | "x-large";
  label?: boolean;
  closable?: boolean;
  prependIcon?: string;
  appendIcon?: string;
  disabled?: boolean;
  rounded?: string | number | boolean;
}

withDefaults(defineProps<Props>(), {
  variant: "tonal",
  color: undefined,
  size: "default",
  prependIcon: undefined,
  appendIcon: undefined,
  rounded: "full",
});
</script>

<template>
  <VChip
    v-bind="$attrs"
    class="r-chip"
    :variant="variant"
    :color="color"
    :size="size"
    :label="label"
    :closable="closable"
    :prepend-icon="prependIcon"
    :append-icon="appendIcon"
    :disabled="disabled"
    :rounded="rounded"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VChip>
</template>

<style scoped>
.r-chip {
  font-weight: var(--r-font-weight-medium);
  letter-spacing: 0;
}
</style>
