<script setup lang="ts">
// GameList — list-layout for a ROM gallery, built on RTable. Columns
// mirror v1's VirtualTable (Title / Size / Added / Released / Rating /
// Languages / Regions / Actions) and keep sortability. Row-click
// navigates to the game detail; the per-row trailing slot hosts a
// MoreMenu for the action set.
import { RBtn, RChip, RTable } from "@v2/lib";
import { computed } from "vue";
import { useRouter } from "vue-router";
import type { SimpleRom } from "@/stores/roms";
import storeRoms from "@/stores/roms";
import { formatBytes } from "@/utils";
import MoreMenu from "@/v2/components/GameActions/MoreMenu.vue";
import {
  pendingMorphName,
  useViewTransition,
} from "@/v2/composables/useViewTransition";

defineOptions({ inheritAttrs: false });

interface Props {
  roms: SimpleRom[];
  totalRoms?: number;
  loading?: boolean;
  webp?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  totalRoms: 0,
  loading: false,
  webp: false,
});

const emit = defineEmits<{
  (e: "update:options", options: { sortBy: SortEntry[] }): void;
}>();

type SortEntry = { key: keyof SimpleRom; order: "asc" | "desc" };

const router = useRouter();
const romsStore = storeRoms();
const { morphTransition } = useViewTransition();

const headers = [
  { title: "Title", key: "name", align: "start", sortable: true },
  { title: "Size", key: "fs_size_bytes", align: "start", sortable: true },
  { title: "Added", key: "created_at", align: "start", sortable: true },
  {
    title: "Released",
    key: "first_release_date",
    align: "start",
    sortable: true,
  },
  { title: "⭐", key: "average_rating", align: "start", sortable: true },
  { title: "🔠", key: "languages", align: "start", sortable: false },
  { title: "🌎", key: "regions", align: "start", sortable: false },
  { title: "", key: "actions", align: "end", sortable: false, width: 64 },
] as const;

const itemsLength = computed(() =>
  props.totalRoms > 0 ? props.totalRoms : props.roms.length,
);

function coverUrl(rom: SimpleRom): string | null {
  const path = rom.path_cover_small ?? rom.path_cover_large ?? null;
  if (!path) return rom.url_cover ?? null;
  return props.webp ? path.replace(/\.(png|jpg|jpeg)$/i, ".webp") : path;
}

function rowClick(e: Event, row: { item: SimpleRom }) {
  const navigate = async () => {
    await router.push(`/rom/${row.item.id}`);
    romsStore.resetSelection?.();
  };
  // Find the row's thumb so the browser can pair it with the GameDetails
  // cover for the morph. Modifier keys / non-primary buttons fall through
  // to a plain navigation so "open in new tab" still works.
  const me = e as MouseEvent;
  if (me.metaKey || me.ctrlKey || me.shiftKey || me.altKey || me.button !== 0) {
    void navigate();
    return;
  }
  const tr = (e.target as HTMLElement | null)?.closest("tr");
  const thumb = tr?.querySelector<HTMLElement>(".game-list__thumb");
  if (!thumb) {
    void navigate();
    return;
  }
  morphTransition({ el: thumb, name: `rom-cover-${row.item.id}` }, navigate);
}

// Reverse-morph tag: when GameDetails is leaving back into a list, paint
// the matching view-transition-name on the thumb of the row whose name
// matches `pendingMorphName` so the browser can pair the snapshots.
function morphStyleFor(item: SimpleRom) {
  const name = `rom-cover-${item.id}`;
  return pendingMorphName.value === name
    ? { viewTransitionName: name }
    : undefined;
}

function onUpdateOptions(options: { sortBy: SortEntry[] }) {
  emit("update:options", options);
}

// Attach the rom id on every row so AlphaStrip's scroll-to-letter can
// locate the destination via `[data-rom-id="…"]` in any layout.
function rowProps({ item }: { item: SimpleRom }) {
  return { "data-rom-id": String(item.id) };
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString();
  } catch {
    return "—";
  }
}

function releaseDate(rom: SimpleRom): string {
  const ts = rom.metadatum?.first_release_date;
  if (!ts) return "—";
  return new Date(ts * 1000).getFullYear().toString();
}

function ratingValue(rom: SimpleRom): string {
  const r = rom.metadatum?.average_rating;
  if (typeof r !== "number" || r <= 0) return "—";
  return r.toFixed(1);
}
</script>

<template>
  <RTable
    variant="server"
    :items="roms"
    :items-length="itemsLength"
    :headers="headers"
    :loading="loading"
    :items-per-page="72"
    item-value="id"
    hover
    fixed-header
    hide-default-footer
    :row-props="rowProps"
    class="game-list"
    @click:row="rowClick"
    @update:options="onUpdateOptions"
  >
    <!-- Title column — cover thumb + name + filename -->
    <template #item.name="{ item }">
      <div class="game-list__title">
        <div class="game-list__thumb" :style="morphStyleFor(item)">
          <img
            v-if="coverUrl(item)"
            :src="coverUrl(item) ?? undefined"
            :alt="item.name ?? item.fs_name_no_ext"
            loading="lazy"
          />
          <span v-else class="game-list__thumb-fallback">
            {{ (item.name ?? item.fs_name_no_ext).slice(0, 2).toUpperCase() }}
          </span>
        </div>
        <div class="game-list__meta">
          <div class="game-list__name">
            {{ item.name ?? item.fs_name_no_ext }}
          </div>
          <div class="game-list__filename">
            {{ item.fs_name }}
          </div>
        </div>
      </div>
    </template>

    <!-- Size -->
    <template #item.fs_size_bytes="{ item }">
      {{ item.fs_size_bytes ? formatBytes(item.fs_size_bytes) : "—" }}
    </template>

    <!-- Added -->
    <template #item.created_at="{ item }">
      {{ formatDate(item.created_at) }}
    </template>

    <!-- Released -->
    <template #item.first_release_date="{ item }">
      {{ releaseDate(item) }}
    </template>

    <!-- Rating -->
    <template #item.average_rating="{ item }">
      {{ ratingValue(item) }}
    </template>

    <!-- Languages -->
    <template #item.languages="{ item }">
      <div class="game-list__pills">
        <RChip
          v-for="l in item.languages?.slice(0, 3) ?? []"
          :key="`lang-${l}`"
          size="x-small"
          variant="tonal"
        >
          {{ l }}
        </RChip>
      </div>
    </template>

    <!-- Regions -->
    <template #item.regions="{ item }">
      <div class="game-list__pills">
        <RChip
          v-for="r in item.regions?.slice(0, 3) ?? []"
          :key="`reg-${r}`"
          size="x-small"
          variant="tonal"
        >
          {{ r }}
        </RChip>
      </div>
    </template>

    <!-- Actions — MoreMenu -->
    <template #item.actions="{ item }">
      <MoreMenu :rom="item">
        <template #activator="{ props: activatorProps }">
          <RBtn
            v-bind="activatorProps"
            icon="mdi-dots-vertical"
            size="x-small"
            variant="text"
            aria-label="More actions"
            @click.prevent.stop
          />
        </template>
      </MoreMenu>
    </template>

    <!-- Pass through any remaining slots (loading, no-data, etc.) -->
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </RTable>
</template>

<style scoped>
.game-list {
  width: 100%;
}

/* Title column layout — compact thumb + name + filename */
.game-list__title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 42px;
}

.game-list__thumb {
  width: 28px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
  display: grid;
  place-items: center;
}

.game-list__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.game-list__thumb-fallback {
  font-size: 10px;
  font-weight: var(--r-font-weight-bold);
  color: rgba(255, 255, 255, 0.4);
}

.game-list__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.game-list__name {
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: rgba(255, 255, 255, 0.92);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 380px;
}

.game-list__filename {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 380px;
}

.game-list__pills {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}
</style>
