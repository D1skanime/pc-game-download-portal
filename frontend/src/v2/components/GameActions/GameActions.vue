<script setup lang="ts">
// GameActions — the action row in the game-details header.
// Composes GameActionBtn atoms that are shared with the GameCard hover
// overlay so both surfaces stay visually and behaviourally in sync.
// The Play button uses the emphasized + withLabel variant to match the
// original white pill CTA; every other button is a circular glass icon
// button. The `more` action opens the shared GameActionsList.
//
// Right-side group: rating + difficulty score pickers, separated from
// the main ribbon by a spacer. Score writes are optimistic via
// useGameActions.setScore.
import { toRef } from "vue";
import type { SimpleRom } from "@/stores/roms";
import GameActionBtn from "@/v2/components/GameActions/GameActionBtn.vue";
import ScoreMenuBtn from "@/v2/components/GameActions/ScoreMenuBtn.vue";
import { useGameActions } from "@/v2/composables/useGameActions";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  rom: SimpleRom;
  canPlay: boolean;
}>();

const romRef = toRef(props, "rom");
const actions = useGameActions(() => romRef.value);
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
    <GameActionBtn :rom="rom" action="download" size="lg" variant="surface" />
    <GameActionBtn :rom="rom" action="favorite" size="lg" variant="surface" />
    <GameActionBtn :rom="rom" action="collection" size="lg" variant="surface" />
    <GameActionBtn :rom="rom" action="status" size="lg" variant="surface" />
    <GameActionBtn :rom="rom" action="more" size="lg" variant="surface" />

    <div v-if="rom.rom_user" class="game-actions__spacer" />

    <ScoreMenuBtn
      v-if="rom.rom_user"
      label="Rating"
      icon-full="mdi-star"
      icon-empty="mdi-star-outline"
      accent="warning"
      :value="rom.rom_user.rating"
      @update:value="(v) => actions.setScore('rating', v)"
    />
    <ScoreMenuBtn
      v-if="rom.rom_user"
      label="Difficulty"
      icon-full="mdi-chili-mild"
      icon-empty="mdi-chili-mild-outline"
      accent="danger"
      :value="rom.rom_user.difficulty"
      @update:value="(v) => actions.setScore('difficulty', v)"
    />
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
.game-actions__spacer {
  flex: 1;
  min-width: 16px;
}
</style>
