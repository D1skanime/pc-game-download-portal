<script setup lang="ts">
// StatusBadge — quick game-status picker for GameCard.
//
// Top-left badge that mirrors v1's Personal-tab status controls without
// having to open the detail panel:
//   * No status   → dashed-circle ghost button, fades in on hover
//   * Status set  → frosted-glass pill showing the status emoji
// Click opens an RMenu listing all 8 statuses; selection routes through
// `useGameActions.setStatus` so toggle semantics match v1.
import { RMenu, RMenuDivider, RMenuItem, RMenuPanel } from "@v2/lib";
import { computed, ref, toRef } from "vue";
import type { SimpleRom } from "@/stores/roms";
import type { PlayingStatus } from "@/utils";
import { romStatusMap } from "@/utils";
import { useGameActions } from "@/v2/composables/useGameActions";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ rom: SimpleRom }>();

const romRef = toRef(props, "rom");
const actions = useGameActions(() => romRef.value);

const open = ref(false);

const current = computed(() => actions.currentStatusKey.value);
const currentDisplay = computed(() =>
  current.value ? romStatusMap[current.value] : null,
);

// Booleans live alongside the enum on `rom_user`, so each row's "is
// active" check has to look at the right field. The picker shows every
// option as toggleable — re-clicking the active one clears it.
function isActive(key: PlayingStatus): boolean {
  const ru = props.rom.rom_user;
  if (!ru) return false;
  if (key === "now_playing") return Boolean(ru.now_playing);
  if (key === "backlogged") return Boolean(ru.backlogged);
  if (key === "hidden") return Boolean(ru.hidden);
  return ru.status === key;
}

const enumStatuses: PlayingStatus[] = [
  "incomplete",
  "finished",
  "completed_100",
  "retired",
  "never_playing",
];

function pick(key: PlayingStatus | null) {
  void actions.setStatus(key);
  open.value = false;
}

function onActivatorClick(e: MouseEvent) {
  // The whole GameCard is a router-link; without this the menu activator
  // click would also navigate to the detail page.
  e.preventDefault();
  e.stopPropagation();
}
</script>

<template>
  <RMenu
    v-model="open"
    :offset="[8, 0]"
    location="bottom start"
    :close-on-content-click="false"
  >
    <template #activator="{ props: activatorProps }">
      <button
        v-bind="activatorProps"
        type="button"
        class="r-gc-status"
        :class="{
          'r-gc-status--set': current,
          'r-gc-status--open': open,
        }"
        :aria-label="
          currentDisplay ? `Status: ${currentDisplay.text}` : 'Set status'
        "
        @click="onActivatorClick"
      >
        <span v-if="currentDisplay" class="r-gc-status__emoji">{{
          currentDisplay.emoji
        }}</span>
        <i v-else class="mdi mdi-list-status r-gc-status__icon" />
      </button>
    </template>
    <RMenuPanel width="220px">
      <RMenuItem
        :variant="isActive('now_playing') ? 'active' : 'default'"
        @click="pick('now_playing')"
      >
        <template #icon>
          <span class="r-gc-status__row-emoji">{{
            romStatusMap.now_playing.emoji
          }}</span>
        </template>
        {{ romStatusMap.now_playing.text }}
      </RMenuItem>
      <RMenuItem
        :variant="isActive('backlogged') ? 'active' : 'default'"
        @click="pick('backlogged')"
      >
        <template #icon>
          <span class="r-gc-status__row-emoji">{{
            romStatusMap.backlogged.emoji
          }}</span>
        </template>
        {{ romStatusMap.backlogged.text }}
      </RMenuItem>

      <RMenuDivider />

      <RMenuItem
        v-for="key in enumStatuses"
        :key="key"
        :variant="isActive(key) ? 'active' : 'default'"
        @click="pick(key)"
      >
        <template #icon>
          <span class="r-gc-status__row-emoji">{{
            romStatusMap[key].emoji
          }}</span>
        </template>
        {{ romStatusMap[key].text }}
      </RMenuItem>

      <RMenuDivider />

      <RMenuItem
        :variant="isActive('hidden') ? 'active' : 'default'"
        @click="pick('hidden')"
      >
        <template #icon>
          <span class="r-gc-status__row-emoji">{{
            romStatusMap.hidden.emoji
          }}</span>
        </template>
        {{ romStatusMap.hidden.text }}
      </RMenuItem>

      <RMenuItem
        v-if="current"
        icon="mdi-close"
        variant="danger"
        @click="pick(null)"
      >
        Clear status
      </RMenuItem>
    </RMenuPanel>
  </RMenu>
</template>

<style scoped>
/* Top-left of the cover, mirroring the rating badge's top-right slot.
   Sized + spaced to match the rating badge so the two corners read as
   a pair. */
.r-gc-status {
  position: absolute;
  top: 7px;
  left: 7px;
  appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  background: rgba(0, 0, 0, 0.55);
  border: 1px dashed rgba(255, 255, 255, 0.45);
  color: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  opacity: 0;
  transition:
    opacity 0.12s ease,
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out),
    transform var(--r-motion-fast) var(--r-motion-ease-out);
  z-index: 2;
}

.r-gc-status:hover,
.r-gc-status--open {
  opacity: 1;
  background: rgba(0, 0, 0, 0.75);
  border-color: rgba(255, 255, 255, 0.85);
  color: #fff;
  transform: scale(1.05);
}

/* When a status is set the badge is solid (no dashed ring) and always
   visible — even when the card overlay isn't. Matches the platform
   badge / rating pattern. */
.r-gc-status--set {
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(0, 0, 0, 0.78);
  opacity: 1;
}

.r-gc-status__emoji {
  font-size: 13px;
  line-height: 1;
}
.r-gc-status__icon {
  font-size: 14px;
  line-height: 1;
}

.r-gc-status__row-emoji {
  font-size: 15px;
  line-height: 1;
  display: inline-block;
}
</style>
