<script setup lang="ts">
// GameActionBtn — single icon button for the per-ROM action set
// shared between the GameCard hover overlay and the GameDetails
// header. One component, three sizes, auto-wires to `useGameActions`
// so both surfaces stay in sync.
//
// Actions:
//   play        → router.push /rom/:id/ejs
//   download    → direct download link click
//   favorite    → toggleFavorite; active state when `isFavorited`
//   collection  → open AddToCollectionDialog; hidden if no collections
//   status      → open status-enum picker (RMenu); icon swaps to the
//                 current status icon when set, dashed border when empty
//   more        → open MoreMenu (GameActionsList dropdown)
//
// Sizes (controls diameter + icon size + padding):
//   sm  → 28px — GameCard hover overlay
//   md  → 40px — default, GameDetails header
//   lg  → 44px — larger emphasis
//
// Variants:
//   glass      → default translucent frosted-glass pill
//   surface    → translucent grey, page-background friendly (Details)
//   emphasized → white-on-dark (used by Play in card + details)
//
// `withLabel` turns the button into a pill with "Play" / "Download" /
// etc. text next to the icon, matching the GameDetails Play CTA.
import { RIcon, RMenu, RMenuDivider, RMenuItem, RMenuPanel } from "@v2/lib";
import { computed, ref, toRef } from "vue";
import type { RomUserStatus } from "@/__generated__";
import type { SimpleRom } from "@/stores/roms";
import { romStatusMap } from "@/utils";
import GameActionsList from "@/v2/components/GameActions/GameActionsList.vue";
import { useGameActions } from "@/v2/composables/useGameActions";

defineOptions({ inheritAttrs: false });

export type GameAction =
  | "play"
  | "download"
  | "favorite"
  | "collection"
  | "status"
  | "more";

interface Props {
  rom: SimpleRom;
  action: GameAction;
  size?: "sm" | "md" | "lg";
  /**
   * `glass` — dark scrim, designed to read on top of cover art
   *           (GameCard hover overlay).
   * `surface` — translucent grey surface, matches RTag tokens
   *             (GameDetails header where the buttons sit on the
   *             page background, not over a cover).
   * `emphasized` — primary white-on-dark CTA (Play).
   */
  variant?: "glass" | "surface" | "emphasized";
  withLabel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: "md",
  variant: "glass",
  withLabel: false,
});

const romRef = toRef(props, "rom");
const actions = useGameActions(() => romRef.value);

// Icon map for the status action — local so v1 (which still consumes
// `romStatusMap`'s emoji) stays untouched. `mdi-progress-helper` is
// the dashed-circle "no status set yet" placeholder.
const STATUS_ICONS: Record<RomUserStatus, string> = {
  incomplete: "mdi-progress-clock",
  finished: "mdi-flag-checkered",
  completed_100: "mdi-trophy-outline",
  retired: "mdi-flag-off-outline",
  never_playing: "mdi-cancel",
};
const STATUS_EMPTY_ICON = "mdi-progress-helper";
const STATUS_KEYS: RomUserStatus[] = [
  "incomplete",
  "finished",
  "completed_100",
  "retired",
  "never_playing",
];

const currentStatus = computed<RomUserStatus | null>(
  () => props.rom.rom_user?.status ?? null,
);

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
      label: "Manage collections",
      onClick: actions.addToCollection,
      active: false,
    };
  }
  if (props.action === "status") {
    const cs = currentStatus.value;
    return {
      icon: cs ? STATUS_ICONS[cs] : STATUS_EMPTY_ICON,
      activeIcon: null,
      label: cs ? `Status: ${romStatusMap[cs].text}` : "Set status",
      onClick: null, // menu owns the click
      active: Boolean(cs),
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
const statusOpen = ref(false);

function pickStatus(key: RomUserStatus | null) {
  void actions.setStatusEnum(key);
  statusOpen.value = false;
}

// For the play/download links we could render `<router-link>` /
// `<a href>` for right-click-open-in-new-tab support, but keeping
// `<button>` here lets the parent surface own the semantics (the whole
// card is already a link). Both direct actions live in the composable.
function onClick(e: MouseEvent) {
  if (props.action === "more" || props.action === "status") return;
  e.preventDefault();
  e.stopPropagation();
  preset.value.onClick?.();
}
</script>

<template>
  <!-- More — opens the shared GameActionsList dropdown. -->
  <RMenu v-if="action === 'more'" v-model="moreOpen" :offset="[8, 0]">
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

  <!-- Status — enum picker; icon mirrors the current value, dashed
       border when no status is set. Keeps the per-ROM action set in
       one place instead of a parallel widget. -->
  <RMenu
    v-else-if="action === 'status'"
    v-model="statusOpen"
    :offset="[8, 0]"
    :close-on-content-click="false"
  >
    <template #activator="{ props: activatorProps }">
      <button
        v-bind="activatorProps"
        type="button"
        class="r-v2-game-btn"
        :class="[
          `r-v2-game-btn--${size}`,
          `r-v2-game-btn--${variant}`,
          'r-v2-game-btn--action-status',
          {
            'r-v2-game-btn--labelled': withLabel,
            'r-v2-game-btn--active': preset.active,
            'r-v2-game-btn--active-status': preset.active,
          },
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
    <RMenuPanel width="220px">
      <RMenuItem
        v-for="key in STATUS_KEYS"
        :key="key"
        :icon="STATUS_ICONS[key]"
        :variant="currentStatus === key ? 'active' : 'default'"
        @click="pickStatus(key)"
      >
        {{ romStatusMap[key].text }}
      </RMenuItem>
      <template v-if="currentStatus">
        <RMenuDivider />
        <RMenuItem icon="mdi-close" variant="danger" @click="pickStatus(null)">
          Clear status
        </RMenuItem>
      </template>
    </RMenuPanel>
  </RMenu>

  <!-- Plain action — direct click. -->
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
  /* Dark glass so the button still reads when sitting on top of a bright
     or busy cover image in the GameCard overlay. In GameDetails the
     backdrop is already a dark blurred cover so this tone lands neutral
     there too. Overlay tokens never theme-flip — they stay dark over
     any cover artwork. */
  border: 1px solid var(--r-color-overlay-border);
  background: var(--r-color-overlay-scrim-soft);
  color: var(--r-color-overlay-fg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--r-radius-pill);
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  font-weight: var(--r-font-weight-semibold);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out),
    transform var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-game-btn:hover {
  background: var(--r-color-overlay-scrim-strong);
  border-color: var(--r-color-overlay-border-strong);
  color: var(--r-color-overlay-fg);
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

/* Surface — RTag-style translucent grey. Used in the GameDetails
   header where buttons sit on the page background (not over cover
   art) — matches the visual vocabulary of RTag and RSelect there. */
.r-v2-game-btn--surface {
  background: var(--r-color-surface);
  border-color: var(--r-color-border-strong);
  color: var(--r-color-fg-secondary);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.r-v2-game-btn--surface:hover {
  background: var(--r-color-surface-hover);
  border-color: var(--r-color-border-strong);
  color: var(--r-color-fg);
}

/* Emphasized — the primary-action look (white on dark). Used by Play. */
.r-v2-game-btn--emphasized {
  background: var(--r-color-overlay-emphasis-bg) !important;
  border-color: var(--r-color-overlay-emphasis-bg) !important;
  color: var(--r-color-overlay-emphasis-fg) !important;
}
.r-v2-game-btn--emphasized:hover {
  background: var(--r-color-overlay-emphasis-bg-hover) !important;
  transform: translateY(-1px);
}
.r-v2-game-btn--emphasized:active {
  transform: scale(0.96);
}

/* Active-state colour swaps per action. */
.r-v2-game-btn--active-favorite {
  color: var(--r-color-fav) !important;
}

/* Status — dashed border when no status is set, signals "click to
   pick". Once set, the button uses the regular solid border + the
   status icon shows the choice. */
.r-v2-game-btn--action-status:not(.r-v2-game-btn--active-status) {
  border-style: dashed;
}
</style>
