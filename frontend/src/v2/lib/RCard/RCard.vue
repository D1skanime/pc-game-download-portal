<script setup lang="ts">
import { VCard } from "vuetify/components/VCard";

defineOptions({ inheritAttrs: false });

interface Props {
  variant?: "flat" | "elevated" | "tonal" | "outlined" | "text" | "plain";
  elevation?: number | string;
  rounded?: string | number | boolean;
  title?: string;
  subtitle?: string;
  loading?: boolean;
}

withDefaults(defineProps<Props>(), {
  variant: "flat",
  elevation: undefined,
  rounded: "lg",
  title: undefined,
  subtitle: undefined,
});
</script>

<template>
  <VCard
    v-bind="$attrs"
    class="r-card"
    :variant="variant"
    :elevation="elevation"
    :rounded="rounded"
    :title="title"
    :subtitle="subtitle"
    :loading="loading"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VCard>
</template>

<style scoped>
.r-card {
  background-color: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  color: var(--r-color-fg);
}
</style>
