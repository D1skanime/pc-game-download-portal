<script setup lang="ts">
// GameListRow — single row of the list-mode gallery.
//
// Owns:
//   * Per-row lazy fetch — onMount fires `fetchRomAt(position)`; the
//     store dedupes against in-flight + already-loaded. onUnmount aborts
//     the fetch via `cancelFetchAt(position)` so a fast scroll past
//     mid-flight doesn't keep server work queued for invisible rows.
//     Mirror of the per-card flow in grid mode — same "row mount =
//     entered viewport" contract via the shell's RVirtualScroller
//     overscan window.
//
//   * Skeleton ↔ real swap — when `getRomAt(position)` returns null the
//     row paints skeleton placeholders in every column; once the fetch
//     resolves it flips to the real cells. Same row height in both
//     states (no scroll reflow on hydration).
//
//   * Click → game-details navigation. Cover-thumb view transition mirrors
//     `GameCard`'s morph so navigating from list / grid into the detail
//     page lands on the same visual anchor.
import { RChip, RIcon, RSkeletonBlock } from "@v2/lib";
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import { formatBytes } from "@/utils";
import MoreMenu from "@/v2/components/GameActions/MoreMenu.vue";
import {
  pendingMorphName,
  useViewTransition,
} from "@/v2/composables/useViewTransition";
import storeGalleryRoms, { type SimpleRom } from "@/v2/stores/galleryRoms";
import { LIST_GRID_TEMPLATE } from "./listColumns";

defineOptions({ inheritAttrs: false });

interface Props {
  /** Absolute position in the active gallery (0-indexed). Drives the
   * row's per-row fetch + serves as the lookup key into the store's
   * `byPosition` map. */
  position: number;
  /** Cover variant — when the browser supports webp the thumb URL is
   * rewritten to .webp before the request. Wired from the shell so the
   * choice is decided once per gallery render, not per row. */
  webp?: boolean;
}

const props = withDefaults(defineProps<Props>(), { webp: false });

const router = useRouter();
const galleryRoms = storeGalleryRoms();
const { morphTransition } = useViewTransition();

const rom = computed<SimpleRom | null>(() =>
  galleryRoms.getRomAt(props.position),
);

const gridStyle = { gridTemplateColumns: LIST_GRID_TEMPLATE };

function coverUrl(item: SimpleRom): string | null {
  const path = item.path_cover_small ?? item.path_cover_large ?? null;
  if (!path) return item.url_cover ?? null;
  return props.webp ? path.replace(/\.(png|jpg|jpeg)$/i, ".webp") : path;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString();
  } catch {
    return "—";
  }
}

function releaseYear(item: SimpleRom): string {
  const ts = item.metadatum?.first_release_date;
  if (!ts) return "—";
  return new Date(ts * 1000).getFullYear().toString();
}

function ratingValue(item: SimpleRom): string {
  const r = item.metadatum?.average_rating;
  if (typeof r !== "number" || r <= 0) return "—";
  return r.toFixed(1);
}

function morphStyleFor(item: SimpleRom) {
  const name = `rom-cover-${item.id}`;
  return pendingMorphName.value === name
    ? { viewTransitionName: name }
    : undefined;
}

function onRowClick(e: MouseEvent) {
  const item = rom.value;
  if (!item) return;
  const navigate = async () => {
    await router.push(`/rom/${item.id}`);
  };
  // Modifier keys / non-primary buttons fall through to a plain
  // navigation so "open in new tab" still works.
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) {
    void navigate();
    return;
  }
  const thumb = (
    e.currentTarget as HTMLElement | null
  )?.querySelector<HTMLElement>(".game-list-row__thumb");
  if (!thumb) {
    void navigate();
    return;
  }
  morphTransition({ el: thumb, name: `rom-cover-${item.id}` }, navigate);
}

onMounted(() => {
  // Entered the overscan window — kick the per-row fetch. Store dedupes
  // against in-flight + already-loaded.
  void galleryRoms.fetchRomAt(props.position);
});

onBeforeUnmount(() => {
  // Left the overscan window before the fetch resolved — abort so the
  // server doesn't keep building a row the user already scrolled past.
  // Idempotent if nothing was in flight.
  if (!galleryRoms.byPosition.has(props.position)) {
    galleryRoms.cancelFetchAt(props.position);
  }
});
</script>

<template>
  <div
    class="game-list-row"
    :class="{ 'game-list-row--clickable': !!rom }"
    :style="gridStyle"
    role="row"
    :data-rom-position="position"
    :data-rom-id="rom?.id"
    @click="onRowClick"
  >
    <!-- Title — cover thumb + name + filename. The thumb stays as a
         skeleton block until the row resolves so the row's left edge
         doesn't shift sideways on hydration. -->
    <div class="game-list-row__cell game-list-row__title">
      <div v-if="rom" class="game-list-row__thumb" :style="morphStyleFor(rom)">
        <img
          v-if="coverUrl(rom)"
          :src="coverUrl(rom) ?? undefined"
          :alt="rom.name ?? rom.fs_name_no_ext"
          loading="lazy"
        />
        <span v-else class="game-list-row__thumb-fallback">
          {{ (rom.name ?? rom.fs_name_no_ext).slice(0, 2).toUpperCase() }}
        </span>
      </div>
      <RSkeletonBlock v-else width="28" height="38" />

      <div class="game-list-row__meta">
        <template v-if="rom">
          <div class="game-list-row__name">
            {{ rom.name ?? rom.fs_name_no_ext }}
          </div>
          <div class="game-list-row__filename">{{ rom.fs_name }}</div>
        </template>
        <template v-else>
          <RSkeletonBlock width="60%" height="12" />
          <RSkeletonBlock width="40%" height="10" />
        </template>
      </div>
    </div>

    <div class="game-list-row__cell">
      <template v-if="rom">
        {{ rom.fs_size_bytes ? formatBytes(rom.fs_size_bytes) : "—" }}
      </template>
      <RSkeletonBlock v-else width="60" height="10" />
    </div>

    <div class="game-list-row__cell">
      <template v-if="rom">{{ formatDate(rom.created_at) }}</template>
      <RSkeletonBlock v-else width="64" height="10" />
    </div>

    <div class="game-list-row__cell">
      <template v-if="rom">{{ releaseYear(rom) }}</template>
      <RSkeletonBlock v-else width="40" height="10" />
    </div>

    <div class="game-list-row__cell">
      <template v-if="rom">{{ ratingValue(rom) }}</template>
      <RSkeletonBlock v-else width="32" height="10" />
    </div>

    <div class="game-list-row__cell">
      <div v-if="rom" class="game-list-row__pills">
        <RChip
          v-for="l in rom.languages?.slice(0, 3) ?? []"
          :key="`lang-${l}`"
          size="x-small"
          variant="tonal"
        >
          {{ l }}
        </RChip>
      </div>
      <RSkeletonBlock v-else width="80" height="10" />
    </div>

    <div class="game-list-row__cell">
      <div v-if="rom" class="game-list-row__pills">
        <RChip
          v-for="r in rom.regions?.slice(0, 3) ?? []"
          :key="`reg-${r}`"
          size="x-small"
          variant="tonal"
        >
          {{ r }}
        </RChip>
      </div>
      <RSkeletonBlock v-else width="80" height="10" />
    </div>

    <div class="game-list-row__cell game-list-row__cell--end">
      <MoreMenu v-if="rom" :rom="rom">
        <template #activator="{ props: activatorProps }">
          <button
            v-bind="activatorProps"
            type="button"
            class="game-list-row__more"
            aria-label="More actions"
            @click.stop
          >
            <RIcon icon="mdi-dots-vertical" size="18" />
          </button>
        </template>
      </MoreMenu>
    </div>
  </div>
</template>

<style scoped>
.game-list-row {
  display: grid;
  align-items: center;
  gap: 0 12px;
  padding: 0 12px;
  height: 56px;
  border-bottom: 1px solid var(--r-color-border);
  font-size: 13px;
  color: var(--r-color-fg-secondary);
  cursor: default;
  transition: background var(--r-motion-fast) var(--r-motion-ease-out);
}

.game-list-row--clickable {
  cursor: pointer;
}
.game-list-row--clickable:hover {
  background: var(--r-color-bg-elevated);
}

.game-list-row__cell {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.game-list-row__cell--end {
  display: flex;
  justify-content: flex-end;
}

.game-list-row__title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.game-list-row__thumb {
  width: 28px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  background: var(--r-color-surface);
  display: grid;
  place-items: center;
}

.game-list-row__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.game-list-row__thumb-fallback {
  font-size: 10px;
  font-weight: var(--r-font-weight-bold);
  color: var(--r-color-fg-muted);
}

.game-list-row__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.game-list-row__name {
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.game-list-row__filename {
  font-size: 11px;
  color: var(--r-color-fg-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.game-list-row__pills {
  display: flex;
  flex-wrap: nowrap;
  gap: 3px;
  overflow: hidden;
}

.game-list-row__more {
  appearance: none;
  background: transparent;
  border: 0;
  padding: 4px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--r-color-fg-muted);
  cursor: pointer;
  transition:
    color var(--r-motion-fast) var(--r-motion-ease-out),
    background var(--r-motion-fast) var(--r-motion-ease-out);
}
.game-list-row__more:hover,
.game-list-row__more:focus-visible {
  color: var(--r-color-fg);
  background: var(--r-color-surface-hover);
}
</style>
