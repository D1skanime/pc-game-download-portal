<script setup lang="ts">
import { VImg } from "vuetify/components/VImg";

defineOptions({ inheritAttrs: false });

interface Props {
  src?: string;
  alt?: string;
  width?: string | number;
  height?: string | number;
  cover?: boolean;
  contain?: boolean;
  aspectRatio?: string | number;
}

withDefaults(defineProps<Props>(), {
  src: undefined,
  alt: undefined,
  width: undefined,
  height: undefined,
  aspectRatio: undefined,
});
</script>

<template>
  <VImg
    v-bind="$attrs"
    :src="src"
    :alt="alt"
    :width="width"
    :height="height"
    :cover="cover"
    :aspect-ratio="aspectRatio"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VImg>
</template>
