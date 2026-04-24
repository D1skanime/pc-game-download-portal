<script setup lang="ts">
// CollectionPickerRow — one row in the AddRomsToCollectionDialog. Portrait
// thumb + name + rom-count + brand-primary circular tick when checked.
// Click toggles; parent owns the pending/checked state and handles the
// API round-trip.
import { RIcon } from "@v2/lib";
import { computed } from "vue";
import CollectionMosaic from "@/v2/components/Collections/CollectionMosaic.vue";

defineOptions({ inheritAttrs: false });

interface Props {
  name: string;
  count: number;
  covers: string[];
  checked: boolean;
  busy?: boolean;
  // Thumb diameter in px. Drives both the grid first-column width and
  // the CollectionMosaic width so the label column always lines up with
  // the right edge of the thumb.
  tileSize?: number;
}

const props = withDefaults(defineProps<Props>(), {
  busy: false,
  tileSize: 36,
});

defineEmits<{
  (e: "toggle"): void;
}>();

const rowStyle = computed(() => ({
  "--tile-w": `${props.tileSize}px`,
}));
</script>

<template>
  <button
    type="button"
    class="pick-row"
    :class="{
      'pick-row--checked': checked,
      'pick-row--busy': busy,
    }"
    :style="rowStyle"
    :aria-pressed="checked"
    :disabled="busy"
    @click="$emit('toggle')"
  >
    <CollectionMosaic :covers="covers" radius="6px" class="pick-row__thumb" />
    <span class="pick-row__name">{{ name }}</span>
    <span class="pick-row__count">{{ count }}</span>
    <span class="pick-row__tick" aria-hidden="true">
      <RIcon v-if="checked" icon="mdi-check" size="14" />
    </span>
  </button>
</template>

<style scoped>
.pick-row {
  appearance: none;
  width: 100%;
  background: transparent;
  border: 0;
  display: grid;
  grid-template-columns: var(--tile-w, 36px) 1fr auto 26px;
  align-items: center;
  gap: 14px;
  padding: 8px 30px;
  cursor: pointer;
  text-align: left;
  color: inherit;
  font-family: inherit;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    opacity var(--r-motion-fast) var(--r-motion-ease-out);
}
.pick-row:hover {
  background: rgba(255, 255, 255, 0.04);
}
.pick-row--checked {
  background: rgba(139, 116, 232, 0.08);
}
.pick-row--checked:hover {
  background: rgba(139, 116, 232, 0.14);
}
.pick-row--busy {
  opacity: 0.6;
  cursor: progress;
}

/* Portrait thumb — width tracks the configurable tile size; height is
   computed by CollectionMosaic from its 140/188 aspectRatio. */
.pick-row__thumb {
  width: var(--tile-w, 36px);
}

.pick-row__name {
  min-width: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.92);
  font-weight: var(--r-font-weight-semibold);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pick-row__count {
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: rgba(255, 255, 255, 0.4);
  font-weight: var(--r-font-weight-medium);
}

.pick-row__tick {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: transparent;
  background: transparent;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}
.pick-row--checked .pick-row__tick {
  background: var(--r-color-brand-primary);
  border-color: var(--r-color-brand-primary);
  color: #fff;
}

:global(.r-v2.r-v2-light) .pick-row__name {
  color: rgba(17, 17, 23, 0.92);
}
:global(.r-v2.r-v2-light) .pick-row__count {
  color: rgba(17, 17, 23, 0.5);
}
:global(.r-v2.r-v2-light) .pick-row:hover {
  background: rgba(17, 17, 23, 0.05);
}
:global(.r-v2.r-v2-light) .pick-row__tick {
  border-color: rgba(17, 17, 23, 0.15);
}
</style>
