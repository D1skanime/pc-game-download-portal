<script setup lang="ts">
import { VAvatar } from "vuetify/components/VAvatar";

defineOptions({ inheritAttrs: false });

interface Props {
  size?: string | number;
  color?: string;
  image?: string;
  icon?: string;
  rounded?: string | number | boolean;
  variant?: "flat" | "elevated" | "tonal" | "outlined" | "text" | "plain";
}

withDefaults(defineProps<Props>(), {
  size: "default",
  color: undefined,
  image: undefined,
  icon: undefined,
  rounded: undefined,
  variant: "flat",
});
</script>

<template>
  <VAvatar
    v-bind="$attrs"
    class="r-avatar"
    :size="size"
    :color="color"
    :image="image"
    :icon="icon"
    :rounded="rounded"
    :variant="variant"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VAvatar>
</template>
