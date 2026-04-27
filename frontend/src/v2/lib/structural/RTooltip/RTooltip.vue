<script setup lang="ts">
// RTooltip — v2 tooltip primitive. Wraps `v-tooltip` and applies the
// `.r-tooltip` skin globally so the teleported content matches the
// rest of the v2 glass language (near-black bg, subtle border, 11 px).
//
// Two activator patterns:
//
//   1. Slot (default — most flexible):
//      <RTooltip text="Classic UI">
//        <template #activator="{ props }">
//          <RBtn v-bind="props" icon="mdi-backup-restore" />
//        </template>
//      </RTooltip>
//
//   2. Parent-attach (pass `activator="parent"` — no extra markup):
//      <button>
//        <RTooltip text="Classic UI" activator="parent" />
//      </button>
//
// Every browser-native `title="…"` hint in v2 should use RTooltip instead.
import { computed } from "vue";
import type { Anchor } from "vuetify";
import { VTooltip } from "vuetify/components/VTooltip";

defineOptions({ inheritAttrs: false });

interface Props {
  text?: string;
  location?: Anchor;
  openDelay?: number | string;
  closeDelay?: number | string;
  modelValue?: boolean;
  contentClass?: string;
  offset?: number | string | number[];
}

const props = withDefaults(defineProps<Props>(), {
  text: undefined,
  location: "bottom",
  openDelay: 300,
  closeDelay: 0,
  contentClass: undefined,
  offset: 6,
});

// Always apply the v2 skin; let callers add more classes via contentClass.
const resolvedContentClass = computed(() =>
  props.contentClass ? `r-tooltip ${props.contentClass}` : "r-tooltip",
);
</script>

<template>
  <VTooltip
    v-bind="$attrs"
    :text="text"
    :location="location"
    :open-delay="openDelay"
    :close-delay="closeDelay"
    :offset="offset"
    :content-class="resolvedContentClass"
    :model-value="modelValue"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VTooltip>
</template>
