<script setup lang="ts">
// MoreMenu — dropdown "more actions" for a ROM, anchored to the trigger
// button you pass in via the `#activator` slot. Wraps RMenu + RMenuPanel
// around the shared GameActionsList, so the items match the right-click
// context menu exactly.
//
// Usage:
//   <MoreMenu :rom="rom">
//     <template #activator="{ props }">
//       <RBtn icon="mdi-dots-horizontal" v-bind="props" />
//     </template>
//   </MoreMenu>
import { RMenu, RMenuPanel } from "@v2/lib";
import { ref } from "vue";
import type { SimpleRom } from "@/stores/roms";
import GameActionsList from "@/v2/components/GameActions/GameActionsList.vue";

defineOptions({ inheritAttrs: false });

defineProps<{ rom: SimpleRom | null }>();

const open = ref(false);
</script>

<template>
  <RMenu v-model="open" location="bottom end" :offset="[8, 0]">
    <template #activator="{ props: activatorProps }">
      <slot name="activator" :props="activatorProps" />
    </template>
    <RMenuPanel width="260px">
      <GameActionsList :rom="rom" @close="open = false" />
    </RMenuPanel>
  </RMenu>
</template>
