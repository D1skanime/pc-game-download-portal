<script setup lang="ts">
import { VRating } from "vuetify/components/VRating";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: number;
  length?: number | string;
  color?: string;
  activeColor?: string;
  emptyIcon?: string;
  fullIcon?: string;
  halfIcon?: string;
  clearable?: boolean;
  ripple?: boolean;
  size?:
    | "x-small"
    | "small"
    | "default"
    | "large"
    | "x-large"
    | string
    | number;
  readonly?: boolean;
  halfIncrements?: boolean;
  density?: "default" | "comfortable" | "compact";
  hover?: boolean;
  itemLabels?: string[];
}

withDefaults(defineProps<Props>(), {
  modelValue: 0,
  length: 5,
  color: "romm-gold",
  activeColor: "romm-gold",
  emptyIcon: undefined,
  fullIcon: undefined,
  halfIcon: undefined,
  clearable: false,
  ripple: true,
  size: "default",
  density: "default",
  itemLabels: undefined,
});

defineEmits<{
  (e: "update:modelValue", value: number): void;
}>();
</script>

<template>
  <VRating
    v-bind="$attrs"
    class="r-rating"
    :model-value="modelValue"
    :length="length"
    :color="color"
    :active-color="activeColor"
    :empty-icon="emptyIcon"
    :full-icon="fullIcon"
    :half-icon="halfIcon"
    :clearable="clearable"
    :ripple="ripple"
    :size="size"
    :readonly="readonly"
    :half-increments="halfIncrements"
    :density="density"
    :hover="hover"
    :item-labels="itemLabels"
    @update:model-value="(v) => $emit('update:modelValue', Number(v))"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VRating>
</template>

<style scoped>
/* Strip the Vuetify VBtn backplate from each rating item — the v1
   look paints an opaque hover circle behind the icon; v2 lets the
   icon stand alone with our own hover lift / scale. */
.r-rating :deep(.v-rating__item .v-btn) {
  background: transparent !important;
  box-shadow: none !important;
}
.r-rating :deep(.v-rating__item .v-btn__overlay),
.r-rating :deep(.v-rating__item .v-btn__underlay) {
  display: none;
}

/* Juicier interactions: each item lifts + scales on hover, the active
   filled icons get a subtle pop on click via CSS animation. Vuetify's
   own ripple still fires on top. */
.r-rating :deep(.v-rating__item) {
  transition:
    transform var(--r-motion-fast) var(--r-motion-ease-out),
    filter var(--r-motion-fast) var(--r-motion-ease-out);
  will-change: transform;
}
.r-rating :deep(.v-rating__item:hover) {
  transform: translateY(-2px) scale(1.12);
  filter: drop-shadow(0 4px 8px color-mix(in srgb, black 35%, transparent));
}
.r-rating :deep(.v-rating__item:active) {
  transform: scale(0.92);
  transition-duration: 80ms;
}
/* Pop animation on the icons that just transitioned to filled. */
.r-rating :deep(.v-rating__item--full .v-icon) {
  animation: r-rating-pop var(--r-motion-med) var(--r-motion-ease-out);
}
@keyframes r-rating-pop {
  0% {
    transform: scale(0.6);
  }
  60% {
    transform: scale(1.18);
  }
  100% {
    transform: scale(1);
  }
}
</style>
