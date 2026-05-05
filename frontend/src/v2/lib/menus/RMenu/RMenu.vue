<script setup lang="ts">
import { computed } from "vue";
import type { Anchor } from "vuetify";
import { VMenu } from "vuetify/components/VMenu";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: boolean;
  closeOnContentClick?: boolean;
  location?: Anchor;
  offset?: string | number | number[];
  openOnHover?: boolean;
  openOnClick?: boolean;
  transition?: string;
  /** Extra class merged into the overlay content. The base `r-menu`
   *  class is always present so the unscoped reset below applies. */
  contentClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  location: "bottom",
  offset: 8,
  closeOnContentClick: true,
  transition: "scale-transition",
  openOnClick: true,
  contentClass: undefined,
});

defineEmits<{
  (e: "update:modelValue", v: boolean): void;
}>();

const overlayClass = computed(() =>
  props.contentClass ? ["r-menu", props.contentClass].join(" ") : "r-menu",
);
</script>

<template>
  <VMenu
    v-bind="$attrs"
    :model-value="modelValue"
    :close-on-content-click="closeOnContentClick"
    :location="location"
    :offset="offset"
    :open-on-hover="openOnHover"
    :open-on-click="openOnClick"
    :transition="transition"
    :content-class="overlayClass"
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VMenu>
</template>

<!-- Panel paint lives in `global.css` under
     `.v-overlay__content.r-menu, .v-overlay__content.r-select__menu`
     so RMenu and RSelect dropdowns share the exact same single layer.
     RMenuPanel inside the slot is a transparent layout container. -->
