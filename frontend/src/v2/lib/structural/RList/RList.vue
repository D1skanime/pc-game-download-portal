<script setup lang="ts">
import { VList } from "vuetify/components/VList";

defineOptions({ inheritAttrs: false });

interface Props {
  density?: "default" | "comfortable" | "compact";
  nav?: boolean;
  lines?: "one" | "two" | "three" | false;
  rounded?: string | number | boolean;
  color?: string;
  bgColor?: string;
}

withDefaults(defineProps<Props>(), {
  density: "comfortable",
  lines: "one",
  rounded: "md",
  color: undefined,
  bgColor: undefined,
});
</script>

<template>
  <VList
    v-bind="$attrs"
    class="r-list"
    :density="density"
    :nav="nav"
    :lines="lines"
    :rounded="rounded"
    :color="color"
    :bg-color="bgColor"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </VList>
</template>

<style scoped>
.r-list {
  background-color: transparent;
}
</style>
