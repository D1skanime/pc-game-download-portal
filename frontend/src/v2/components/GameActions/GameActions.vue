<script setup lang="ts">
// GameActions — the 5-button action row in the game-details header:
// Play · Download · Favorite · Share · More. Every icon button is an RBtn
// with an `icon` prop; the More button opens MoreMenu (RMenu +
// GameActionsList) for the full action list.
import { RBtn } from "@v2/lib";
import { toRef } from "vue";
import type { SimpleRom } from "@/stores/roms";
import GameActionsMoreMenu from "@/v2/components/GameActions/MoreMenu.vue";
import { useGameActions } from "@/v2/composables/useGameActions";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  rom: SimpleRom;
  canPlay: boolean;
  downloadHref?: string;
  playHref?: string;
}>();

const romRef = toRef(props, "rom");
const actions = useGameActions(() => romRef.value);
</script>

<template>
  <div class="game-actions">
    <router-link
      v-if="canPlay"
      :to="playHref ?? `/rom/${rom.id}/ejs`"
      class="game-actions__play"
    >
      <i class="mdi mdi-play" aria-hidden="true" />
      Play
    </router-link>

    <RBtn
      v-if="downloadHref"
      icon="mdi-download-outline"
      size="large"
      variant="text"
      class="game-actions__btn"
      :href="downloadHref"
      aria-label="Download"
    />

    <RBtn
      :icon="actions.isFavorited.value ? 'mdi-heart' : 'mdi-heart-outline'"
      size="large"
      variant="text"
      class="game-actions__btn"
      :class="{ 'game-actions__btn--fav-on': actions.isFavorited.value }"
      :aria-label="
        actions.isFavorited.value ? 'Remove from favorites' : 'Favorite'
      "
      @click="actions.favorite"
    />

    <RBtn
      icon="mdi-share-variant"
      size="large"
      variant="text"
      class="game-actions__btn"
      aria-label="Share"
      @click="actions.share"
    />

    <GameActionsMoreMenu :rom="rom">
      <template #activator="{ props: activatorProps }">
        <RBtn
          icon="mdi-dots-horizontal"
          size="large"
          variant="text"
          class="game-actions__btn"
          aria-label="More actions"
          v-bind="activatorProps"
        />
      </template>
    </GameActionsMoreMenu>
  </div>
</template>

<style scoped>
.game-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 6px 0 4px;
}

.game-actions__play {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  background: #fff;
  color: #111;
  border: none;
  border-radius: var(--r-radius-pill);
  padding: 11px 28px;
  font-size: 15px;
  font-weight: var(--r-font-weight-bold);
  text-decoration: none;
  cursor: pointer;
  transition:
    background var(--r-motion-fast),
    transform var(--r-motion-fast);
}
.game-actions__play:hover {
  background: #e0e0e0;
  transform: scale(1.03);
}
.game-actions__play .mdi {
  font-size: 18px;
}

/* Ghost-pill look for the circular icon buttons (matches the old RIconBtn
   "fav" variant — translucent glass; heart turns red when favorited). */
.game-actions__btn {
  background: rgba(255, 255, 255, 0.1) !important;
  border: 1px solid rgba(255, 255, 255, 0.18) !important;
  color: rgba(255, 255, 255, 0.9) !important;
  opacity: 1;
}
.game-actions__btn:hover {
  background: rgba(255, 255, 255, 0.22) !important;
}
.game-actions__btn--fav-on {
  color: var(--r-color-fav) !important;
}

@media (max-width: 768px) {
  .game-actions__play {
    padding: 9px 20px;
    font-size: 14px;
  }
}
</style>
