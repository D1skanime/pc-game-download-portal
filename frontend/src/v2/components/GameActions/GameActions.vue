<script setup lang="ts">
// GameActions — the action row in the game-details header.
// Composes GameActionBtn atoms that are shared with the RGameCard hover
// overlay so both surfaces stay visually and behaviourally in sync.
// The Play button uses the emphasized + withLabel variant to match the
// original white pill CTA; every other button is a circular glass icon
// button. The `more` action opens the shared GameActionsList.
import type { SimpleRom } from "@/stores/roms";
import GameActionBtn from "@/v2/components/GameActions/GameActionBtn.vue";

defineOptions({ inheritAttrs: false });

defineProps<{
  rom: SimpleRom;
  canPlay: boolean;
}>();
</script>

<template>
  <div class="game-actions">
    <GameActionBtn
      v-if="canPlay"
      :rom="rom"
      action="play"
      size="lg"
      variant="emphasized"
      with-label
    />
    <GameActionBtn :rom="rom" action="download" size="lg" />
    <GameActionBtn :rom="rom" action="favorite" size="lg" />
    <GameActionBtn :rom="rom" action="collection" size="lg" />
    <GameActionBtn :rom="rom" action="more" size="lg" />
  </div>
</template>

<style scoped>
.game-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 6px 0 4px;
  flex-wrap: wrap;
}
</style>
