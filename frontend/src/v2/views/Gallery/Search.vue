<script setup lang="ts">
// Search — global ROM search with the same single-virtualiser, sparse-
// loading architecture as Platform / Collection.
import { RChip, RVirtualScroller } from "@v2/lib";
import { storeToRefs } from "pinia";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { onBeforeRouteLeave, useRoute } from "vue-router";
import storeGalleryFilter from "@/stores/galleryFilter";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import { GameCard, GameCardSkeleton } from "@/v2/components/Gallery/GameCard";
import GameList from "@/v2/components/Gallery/GameList.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";
import { useGalleryFilterUrl } from "@/v2/composables/useGalleryFilterUrl";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import {
  useGalleryVirtualItems,
  type GalleryItem,
  type GallerySlot,
} from "@/v2/composables/useGalleryVirtualItems";
import { useResponsiveColumns } from "@/v2/composables/useResponsiveColumns";
import { useWebpSupport } from "@/v2/composables/useWebpSupport";
import storeGalleryRoms from "@/v2/stores/galleryRoms";
import storeScrollRestoration from "@/v2/stores/scrollRestoration";

const route = useRoute();
const galleryRoms = storeGalleryRoms();
const galleryFilterStore = storeGalleryFilter();
const scrollRestoration = storeScrollRestoration();
useGalleryFilterUrl();
const { supportsWebp } = useWebpSupport();

const { total, charIndex, byPosition, initialFetching } =
  storeToRefs(galleryRoms);
const { searchTerm } = storeToRefs(galleryFilterStore);
const { groupBy, layout, toolbarPosition } = useGalleryMode();

const initialSearch = ref(false);

const searchInput = ref(searchTerm.value ?? "");
let searchDebounce: ReturnType<typeof setTimeout> | null = null;

const sectionEl = ref<HTMLElement | null>(null);
const { columns } = useResponsiveColumns(sectionEl, {
  cardWidth: 158,
  gap: 12,
  inset: 108,
});

const loadingInitial = computed(
  () => initialFetching.value && total.value === 0,
);

const { virtualItems, letterToIndex, availableLetters } =
  useGalleryVirtualItems({
    hasHero: ref(true),
    toolbarInline: computed(() => toolbarPosition.value === "header"),
    layout,
    groupBy,
    total,
    charIndex,
    getRomAt: (p) => galleryRoms.getRomAt(p),
    loadedTick: byPosition,
    columns,
    loadingInitial,
    emptyMessage: computed(() =>
      searchTerm.value
        ? `No games match "${searchTerm.value}".`
        : "No games match your search.",
    ),
    skeletonRowCount: 4,
  });

const visibleLettersSet = ref<Set<string>>(new Set());
const currentLetter = ref<string>("");
const scrollerRef = ref<InstanceType<typeof RVirtualScroller> | null>(null);
let intersectionObserver: IntersectionObserver | null = null;
let mutationObserver: MutationObserver | null = null;
let observed = new WeakSet<Element>();

function recomputeVisible(root: HTMLElement) {
  const visibles: Array<{ letters: string[]; top: number }> = [];
  root
    .querySelectorAll<HTMLElement>("[data-spy-letters][data-spy-active='1']")
    .forEach((target) => {
      const raw = target.dataset.spyLetters;
      if (!raw) return;
      const letters = raw.split(",").filter(Boolean);
      if (!letters.length) return;
      visibles.push({ letters, top: target.getBoundingClientRect().top });
    });
  visibles.sort((a, b) => a.top - b.top);
  const set = new Set<string>();
  for (const v of visibles) for (const l of v.letters) set.add(l);
  visibleLettersSet.value = set;
  currentLetter.value = visibles[0]?.letters[0] ?? currentLetter.value;
}

function prefetchVisibleSkeletonRows(root: HTMLElement) {
  root
    .querySelectorAll<HTMLElement>(
      "[data-spy-active='1'][data-prefetch-position]",
    )
    .forEach((target) => {
      const pos = Number(target.dataset.prefetchPosition);
      if (!Number.isFinite(pos)) return;
      void galleryRoms.fetchWindowAt(pos);
    });
}

function setupSpy() {
  const root = scrollerRef.value?.containerEl;
  if (!root) return;
  teardownSpy();

  intersectionObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        (entry.target as HTMLElement).dataset.spyActive = entry.isIntersecting
          ? "1"
          : "0";
      }
      recomputeVisible(root);
      prefetchVisibleSkeletonRows(root);
    },
    { root, threshold: 0 },
  );

  const observeAll = () => {
    root.querySelectorAll<HTMLElement>("[data-spy-letters]").forEach((el) => {
      if (observed.has(el)) return;
      observed.add(el);
      intersectionObserver?.observe(el);
    });
  };
  observeAll();
  mutationObserver = new MutationObserver(observeAll);
  mutationObserver.observe(root, { childList: true, subtree: true });
}

function teardownSpy() {
  intersectionObserver?.disconnect();
  intersectionObserver = null;
  mutationObserver?.disconnect();
  mutationObserver = null;
  observed = new WeakSet<Element>();
}

function scrollToLetter(letter: string) {
  const idx = letterToIndex.value.get(letter);
  if (idx == null) return;
  scrollerRef.value?.scrollToIndex(idx, { smooth: true });
  currentLetter.value = letter;
  const item = virtualItems.value[idx];
  if (item?.kind === "row") void galleryRoms.fetchWindowAt(item.startPosition);
  else if (item?.kind === "letter-header") {
    const next = virtualItems.value[idx + 1];
    if (next?.kind === "row")
      void galleryRoms.fetchWindowAt(next.startPosition);
  }
}

function setSearch(value: string) {
  searchInput.value = value;
  if (searchDebounce) clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    const normalized = value.trim();
    if (normalized === (searchTerm.value ?? "")) return;
    searchTerm.value = normalized || null;
    galleryRoms.invalidateWindows();
    initialSearch.value = true;
    void galleryRoms.fetchWindowAt(0);
  }, 300);
}

type SortEntry = {
  key: keyof import("@/stores/roms").SimpleRom;
  order: "asc" | "desc";
};
function onListOptions(options: { sortBy: SortEntry[]; page?: number }) {
  const first = options.sortBy?.[0];
  if (first) {
    galleryRoms.setOrderBy(first.key);
    galleryRoms.setOrderDir(first.order);
    galleryRoms.invalidateWindows();
    void galleryRoms.fetchWindowAt(0);
    return;
  }
  if (options.page !== undefined) {
    void galleryRoms.fetchWindowAt((options.page - 1) * 72);
  }
}

const loadedRoms = computed(() => {
  const entries = [...byPosition.value.entries()].sort((a, b) => a[0] - b[0]);
  return entries.map(([, rom]) => rom);
});

watch(virtualItems, () => nextTick().then(setupSpy));

async function applyRestoredScroll() {
  const saved = scrollRestoration.restore(route.fullPath);
  if (saved == null) return;
  const root = scrollerRef.value?.containerEl;
  if (!root) return;
  await nextTick();
  root.scrollTop = saved;
}

onMounted(async () => {
  // Global search — drop ALL gallery scoping from previous views.
  galleryRoms.resetGallery();
  await galleryRoms.fetchWindowAt(0);
  initialSearch.value = true;
  await nextTick();
  setupSpy();
  applyRestoredScroll();
});

onBeforeRouteLeave((_to, from) => {
  const root = scrollerRef.value?.containerEl;
  if (root) scrollRestoration.save(from.fullPath, root.scrollTop);
});

onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
  teardownSpy();
});

function spyLetters(item: GalleryItem): string | undefined {
  if (item.kind === "letter-header") return item.letter;
  if (item.kind === "row") return item.letters.join(",");
  return undefined;
}

function prefetchPosition(item: GalleryItem): number | undefined {
  if (item.kind !== "row" || !item.hasMissing) return undefined;
  const skel = item.slots.find((s) => s.kind === "skeleton") as
    | Extract<GallerySlot, { kind: "skeleton" }>
    | undefined;
  return skel?.position;
}

type RowItem = Extract<GalleryItem, { kind: "row" }>;
type LetterHeaderItem = Extract<GalleryItem, { kind: "letter-header" }>;
type EmptyItem = Extract<GalleryItem, { kind: "empty" }>;
const asRow = (i: GalleryItem) => i as RowItem;
const asLetterHeader = (i: GalleryItem) => i as LetterHeaderItem;
const asEmpty = (i: GalleryItem) => i as EmptyItem;
const itemKind = (i: GalleryItem) => i.kind;

const rowGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(1, columns.value)}, minmax(var(--r-card-art-w), 1fr))`,
}));

const showStandaloneEmpty = computed(
  () => !initialFetching.value && total.value === 0 && !!searchTerm.value,
);
</script>

<template>
  <section ref="sectionEl" class="r-v2-search">
    <RVirtualScroller
      ref="scrollerRef"
      :items="virtualItems"
      class="r-v2-search__scroller r-v2-scroll-hidden"
    >
      <template #default="{ item }">
        <div
          class="r-v2-search__item"
          :data-spy-letters="spyLetters(item as GalleryItem)"
          :data-prefetch-position="prefetchPosition(item as GalleryItem)"
        >
          <template v-if="itemKind(item as GalleryItem) === 'hero'">
            <PageHeader title="Search">
              <template #count>
                <RChip
                  v-if="initialSearch && !initialFetching"
                  size="small"
                  variant="tonal"
                >
                  {{ total }} results
                </RChip>
              </template>
            </PageHeader>
          </template>

          <GalleryToolbar
            v-else-if="itemKind(item as GalleryItem) === 'toolbar'"
            :group-by="groupBy"
            :layout="layout"
            :position="toolbarPosition"
            show-search
            :search="searchInput"
            search-placeholder="Search by name, filename, hash…"
            @update:group-by="groupBy = $event"
            @update:layout="layout = $event"
            @update:search="setSearch"
          />

          <div
            v-else-if="itemKind(item as GalleryItem) === 'letter-header'"
            class="r-v2-search__letter-heading"
          >
            {{ asLetterHeader(item as GalleryItem).letter }}
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'row'"
            class="r-v2-search__row"
            :style="rowGridStyle"
          >
            <template
              v-for="(slot, slotIdx) in asRow(item as GalleryItem).slots"
              :key="slot.position"
            >
              <GameCard
                v-if="slot.kind === 'rom'"
                class="r-v2-search__card-fade"
                :style="{ '--card-fade-i': slotIdx }"
                :rom="slot.rom"
                :webp="supportsWebp"
              />
              <GameCardSkeleton v-else />
            </template>
          </div>

          <GameList
            v-else-if="itemKind(item as GalleryItem) === 'list-table'"
            :roms="loadedRoms"
            :total-roms="total"
            :loading="loadingInitial"
            :webp="supportsWebp"
            @update:options="onListOptions"
          />

          <div
            v-else-if="itemKind(item as GalleryItem) === 'empty'"
            class="r-v2-search__empty-row"
          >
            <EmptyState
              v-if="showStandaloneEmpty"
              variant="boxed"
              icon="mdi-emoticon-confused-outline"
              :message="asEmpty(item as GalleryItem).message"
            />
            <span v-else>{{ asEmpty(item as GalleryItem).message }}</span>
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'skeleton-row'"
            class="r-v2-search__row"
            :style="rowGridStyle"
          >
            <GameCardSkeleton
              v-for="n in Math.max(1, columns)"
              :key="`sk-${n}`"
            />
          </div>
        </div>
      </template>
    </RVirtualScroller>

    <AlphaStrip
      v-if="availableLetters.size > 0"
      :available="availableLetters"
      :current="currentLetter"
      :visible="visibleLettersSet"
      @pick="scrollToLetter"
    />

    <GalleryToolbar
      v-if="toolbarPosition === 'floating'"
      :group-by="groupBy"
      :layout="layout"
      :position="toolbarPosition"
      @update:group-by="groupBy = $event"
      @update:layout="layout = $event"
    />
  </section>
</template>

<style scoped>
.r-v2-search {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-search__scroller {
  flex: 1;
  height: 100%;
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-search__item {
  width: 100%;
}

.r-v2-search__letter-heading {
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
  padding: 20px 0 12px;
}

.r-v2-search__row {
  display: grid;
  gap: 18px 12px;
  padding-bottom: 18px;
}

.r-v2-search__card-fade {
  animation: r-v2-search-card-fade 280ms ease-out both;
  animation-delay: calc(var(--card-fade-i, 0) * 30ms);
}
@keyframes r-v2-search-card-fade {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.r-v2-search__empty-row {
  padding: 40px 0;
  color: var(--r-color-fg-faint);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 768px) {
  .r-v2-search__scroller {
    padding: 16px 14px 80px;
  }
  .r-v2-search__row {
    gap: 12px 10px;
  }
}
</style>
