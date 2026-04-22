<script setup lang="ts">
import { VListItem } from "vuetify/components/VList";

defineOptions({ inheritAttrs: false });

interface Props {
  title?: string;
  subtitle?: string;
  value?: unknown;
  prependIcon?: string;
  appendIcon?: string;
  prependAvatar?: string;
  active?: boolean;
  disabled?: boolean;
  density?: "default" | "comfortable" | "compact";
  to?: string | object;
  href?: string;
  color?: string;
  rounded?: string | number | boolean;
}

withDefaults(defineProps<Props>(), {
  title: undefined,
  subtitle: undefined,
  value: undefined,
  prependIcon: undefined,
  appendIcon: undefined,
  prependAvatar: undefined,
  density: "comfortable",
  to: undefined,
  href: undefined,
  color: "primary",
  rounded: "md",
});
</script>

<template>
  <VListItem
    v-bind="$attrs"
    class="r-list-item"
    :title="title"
    :subtitle="subtitle"
    :value="value"
    :prepend-icon="prependIcon"
    :append-icon="appendIcon"
    :prepend-avatar="prependAvatar"
    :active="active"
    :disabled="disabled"
    :density="density"
    :to="to"
    :href="href"
    :color="color"
    :rounded="rounded"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VListItem>
</template>

<style scoped>
.r-list-item {
  color: var(--r-color-fg);
}
</style>
