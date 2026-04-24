<script setup lang="ts">
// GameActionBtn — single icon button for the per-ROM action set
// shared between the RGameCard hover overlay and the GameDetails
// header. One component, three sizes, auto-wires to `useGameActions`
// so both surfaces stay in sync.
//
// Actions:
//   play        → router.push /rom/:id/ejs
//   download    → direct download link click
//   favorite    → toggleFavorite; active state when `isFavorited`
//   collection  → open AddToCollectionDialog; hidden if no collections
//   more        → open MoreMenu (GameActionsList dropdown)
//
// Sizes (controls diameter + icon size + padding):
//   sm  → 28px — RGameCard hover overlay
//   md  → 40px — default, GameDetails header
//   lg  → 44px — larger emphasis
//
// Variants:
//   glass      → default translucent frosted-glass pill
//   emphasized → white-on-dark (used by Play in card + details)
//
// `withLabel` turns the button into a pill with "Play" / "Download" /
// etc. text next to the icon, matching the GameDetails Play CTA.
import { RIcon, RMenu, RMenuPanel } from "@v2/lib";
import { computed, ref, toRef } from "vue";
import type { SimpleRom } from "@/stores/roms";
import GameActionsList from "@/v2/components/GameActions/GameActionsList.vue";
import { useGameActions } from "@/v2/composables/useGameActions";

defineOptions({ inheritAttrs: false });

export type GameAction =
  | "play"
  | "download"
  | "favorite"
  | "collection"
  | "more";

interface Props {
  rom: SimpleRom;
  action: GameAction;
  size?: "sm" | "md" | "lg";
  variant?: "glass" | "emphasized";
  withLabel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: "md",
  variant: "glass",
  withLabel: false,
});

const romRef = toRef(props, "rom");
const actions = useGameActions(() => romRef.value);

type Preset = {
  icon: string;
  label: string;
  activeIcon: string | null;
  onClick: (() => void) | null;
  active: boolean;
};

// Presentation metadata per action — icon swaps when active, different
// aria labels, different click handlers. Written as an if-chain instead
// of a switch so the linter can see every path returns.
const preset = computed<Preset>(() => {
  if (props.action === "play") {
    return {
      icon: "mdi-play",
      label: "Play",
      activeIcon: null,
      onClick: actions.play,
      active: false,
    };
  }
  if (props.action === "download") {
    return {
      icon: "mdi-download-outline",
      label: "Download",
      activeIcon: null,
      onClick: actions.download,
      active: false,
    };
  }
  if (props.action === "favorite") {
    return {
      icon: "mdi-heart-outline",
      activeIcon: "mdi-heart",
      label: actions.isFavorited.value ? "Remove favorite" : "Favorite",
      onClick: actions.favorite,
      active: actions.isFavorited.value,
    };
  }
  if (props.action === "collection") {
    return {
      icon: "mdi-bookmark-outline",
      activeIcon: null,
      label: "Add to collection",
      onClick: actions.addToCollection,
      active: false,
    };
  }
  // "more" — the RMenu owns activation; no direct click handler.
  return {
    icon: "mdi-dots-horizontal",
    activeIcon: null,
    label: "More actions",
    onClick: null,
    active: false,
  };
});

const displayedIcon = computed(
  () => (preset.value.active && preset.value.activeIcon) || preset.value.icon,
);

const moreOpen = ref(false);

// For the play/download links we could render `<router-link>` /
// `<a href>` for right-click-open-in-new-tab support, but keeping
// `<button>` here lets the parent surface own the semantics (the whole
// card is already a link). Both direct actions live in the composable.
function onClick(e: MouseEvent) {
  if (props.action === "more") return; // menu owns the click
  e.preventDefault();
  e.stopPropagation();
  preset.value.onClick?.();
}
</script>

<template>
  <template v-if="action === 'more'">
    <RMenu v-model="moreOpen" :offset="[8, 0]">
      <template #activator="{ props: activatorProps }">
        <button
          v-bind="activatorProps"
          type="button"
          class="r-v2-game-btn"
          :class="[
            `r-v2-game-btn--${size}`,
            `r-v2-game-btn--${variant}`,
            { 'r-v2-game-btn--labelled': withLabel },
          ]"
          :aria-label="preset.label"
          @click.prevent.stop
        >
          <RIcon :icon="displayedIcon" />
          <span v-if="withLabel" class="r-v2-game-btn__label">
            {{ preset.label }}
          </span>
        </button>
      </template>
      <RMenuPanel width="260px">
        <GameActionsList :rom="rom" @close="moreOpen = false" />
      </RMenuPanel>
    </RMenu>
  </template>
  <button
    v-else
    type="button"
    class="r-v2-game-btn"
    :class="[
      `r-v2-game-btn--${size}`,
      `r-v2-game-btn--${variant}`,
      {
        'r-v2-game-btn--labelled': withLabel,
        'r-v2-game-btn--active': preset.active,
        [`r-v2-game-btn--active-${action}`]: preset.active,
      },
    ]"
    :aria-label="preset.label"
    @click="onClick"
  >
    <RIcon :icon="displayedIcon" />
    <span v-if="withLabel" class="r-v2-game-btn__label">
      {{ preset.label }}
    </span>
  </button>
</template>

<style scoped>
.r-v2-game-btn {
  appearance: none;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--r-radius-pill);
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  font-weight: var(--r-font-weight-semibold);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out),
    transform var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-game-btn:hover {
  background: rgba(255, 255, 255, 0.22);
}
.r-v2-game-btn:active {
  transform: scale(0.94);
}

/* Sizing — circular unless `--labelled`. */
.r-v2-game-btn--sm {
  width: 28px;
  height: 28px;
  font-size: 11px;
}
.r-v2-game-btn--sm :deep(.mdi) {
  font-size: 16px;
}
.r-v2-game-btn--md {
  width: 40px;
  height: 40px;
  font-size: 13px;
}
.r-v2-game-btn--md :deep(.mdi) {
  font-size: 20px;
}
.r-v2-game-btn--lg {
  width: 44px;
  height: 44px;
  font-size: 14px;
}
.r-v2-game-btn--lg :deep(.mdi) {
  font-size: 22px;
}

/* Labelled — expands to a pill with text. Used by Play in the
   GameDetails header. Height stays the same as the circular variant so
   it can live in the same row without visual jumps. */
.r-v2-game-btn--labelled {
  width: auto;
  padding: 0 18px;
}
.r-v2-game-btn--labelled.r-v2-game-btn--sm {
  padding: 0 12px;
}
.r-v2-game-btn--labelled.r-v2-game-btn--lg {
  padding: 0 24px;
}

/* Emphasized — the primary-action look (white on dark). Used by Play. */
.r-v2-game-btn--emphasized {
  background: #fff !important;
  border-color: #fff !important;
  color: #111 !important;
}
.r-v2-game-btn--emphasized:hover {
  background: #e6e6e6 !important;
  transform: translateY(-1px);
}
.r-v2-game-btn--emphasized:active {
  transform: scale(0.96);
}

/* Active-state colour swaps per action. Favorite goes red; collection
   picks up a subtle accent. */
.r-v2-game-btn--active-favorite {
  color: var(--r-color-fav) !important;
}
</style>
