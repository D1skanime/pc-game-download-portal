// galleryRoms (v2) — windowed/sparse store for the active gallery list.
//
// Replaces v1's `stores/roms.ts` for the gallery-list responsibility.
// What lives here:
//   - the gallery context (currentPlatform / Collection / Virtual / Smart),
//   - the total ROM count + per-letter offset table from the backend,
//   - a sparse `byPosition` map that holds whatever windows have been
//     fetched so far,
//   - book-keeping for in-flight / loaded / failed windows.
//
// Why a NEW store rather than extending v1:
//   v1 collapses pagination into `fetchRoms()` advancing a single
//   `fetchOffset`. v2 needs random-access window loads (driven by which
//   rows enter the virtualiser's viewport, including skeleton rows for
//   positions we've never touched). Forking lets v2 model that cleanly
//   while v1 stays frozen. Per the constitution, the v1 gallery-list
//   surface is annotated `@deprecated` with a pointer here.
//
// What does NOT live here:
//   - currentRom (lives in v1 `stores/roms`, GameDetails reads it),
//   - recentRoms / continuePlayingRoms (Home consumers stay on v1),
//   - selection state, order-by/order-dir,
//   These are still served by the v1 store; the v2 gallery view doesn't
//   need them.
import { defineStore } from "pinia";
import type { SimpleRomSchema } from "@/__generated__/";
import romApi from "@/services/api/rom";
import {
  type Collection,
  type SmartCollection,
  type VirtualCollection,
} from "@/stores/collections";
import storeGalleryFilter from "@/stores/galleryFilter";
import storePlatforms, { type Platform } from "@/stores/platforms";
import type { ExtractPiniaStoreType } from "@/types";

export type SimpleRom = SimpleRomSchema;

type GalleryFilterStore = ExtractPiniaStoreType<typeof storeGalleryFilter>;

// Default window size — the backend's pagination limit. Smaller windows
// mean more round-trips but finer-grained fills; larger windows mean
// fewer requests but each one downloads more.
const WINDOW_SIZE = 72;

interface State {
  currentPlatform: Platform | null;
  currentCollection: Collection | null;
  currentVirtualCollection: VirtualCollection | null;
  currentSmartCollection: SmartCollection | null;
  total: number;
  charIndex: Record<string, number>;
  romIdIndex: number[];
  byPosition: Map<number, SimpleRom>;
  loadedWindows: Set<number>;
  pendingWindows: Set<number>;
  failedWindows: Set<number>;
  // True until the very first fetchWindow(0) resolves — view shows a
  // skeleton hero/skeleton rows during this phase.
  initialFetching: boolean;
  // Order params — gallery-list scoped (separate from v1's localStorage
  // keys so v1/v2 don't fight over the same value).
  orderBy: keyof SimpleRom;
  orderDir: "asc" | "desc";
}

const defaults = (): State => ({
  currentPlatform: null,
  currentCollection: null,
  currentVirtualCollection: null,
  currentSmartCollection: null,
  total: 0,
  charIndex: {},
  romIdIndex: [],
  byPosition: new Map(),
  loadedWindows: new Set(),
  pendingWindows: new Set(),
  failedWindows: new Set(),
  initialFetching: false,
  orderBy: "name",
  orderDir: "asc",
});

function alignToWindow(offset: number): number {
  return Math.floor(offset / WINDOW_SIZE) * WINDOW_SIZE;
}

export default defineStore("v2GalleryRoms", {
  state: () => defaults(),

  getters: {
    onGalleryView: (state) =>
      !!(
        state.currentPlatform ||
        state.currentCollection ||
        state.currentVirtualCollection ||
        state.currentSmartCollection
      ),
    /** True when at least the first window has loaded. */
    hasInitial: (state) => state.loadedWindows.size > 0,
  },

  actions: {
    setCurrentPlatform(platform: Platform | null) {
      this.currentPlatform = platform;
    },
    setCurrentCollection(collection: Collection | null) {
      this.currentCollection = collection;
    },
    setCurrentVirtualCollection(collection: VirtualCollection | null) {
      this.currentVirtualCollection = collection;
    },
    setCurrentSmartCollection(collection: SmartCollection | null) {
      this.currentSmartCollection = collection;
    },

    setOrderBy(key: keyof SimpleRom) {
      this.orderBy = key;
    },
    setOrderDir(dir: "asc" | "desc") {
      this.orderDir = dir;
    },

    /** Read a ROM at a position, or null if its window hasn't been
     * loaded yet. Returns null without triggering a fetch — fetching is
     * the view's responsibility (driven by row visibility). */
    getRomAt(position: number): SimpleRom | null {
      return this.byPosition.get(position) ?? null;
    },

    /** Drop everything tied to the previous gallery context but keep
     * order-by / order-dir. Call before switching platform / collection
     * or when filters change. */
    resetGallery() {
      this.currentPlatform = null;
      this.currentCollection = null;
      this.currentVirtualCollection = null;
      this.currentSmartCollection = null;
      this.total = 0;
      this.charIndex = {};
      this.romIdIndex = [];
      this.byPosition = new Map();
      this.loadedWindows = new Set();
      this.pendingWindows = new Set();
      this.failedWindows = new Set();
      this.initialFetching = false;
    },

    /** Drop the loaded windows but keep the gallery context — used when
     * search / filter changes within the same gallery and we need to
     * re-fetch from offset 0. */
    invalidateWindows() {
      this.total = 0;
      this.charIndex = {};
      this.romIdIndex = [];
      this.byPosition = new Map();
      this.loadedWindows = new Set();
      this.pendingWindows = new Set();
      this.failedWindows = new Set();
      this.initialFetching = false;
    },

    _shouldGroupRoms(): boolean {
      const raw = localStorage.getItem("settings.groupRoms");
      return raw === null ? true : raw === "true";
    },

    _buildRequestParams(galleryFilter: GalleryFilterStore, offset: number) {
      // Determine platform IDs from the gallery context, falling back to
      // the gallery-filter store's platform multi-select.
      let platformIds: number[] | null = null;
      if (this.currentPlatform) {
        platformIds = [this.currentPlatform.id];
      } else if (galleryFilter.selectedPlatforms.length > 0) {
        platformIds = galleryFilter.selectedPlatforms.map((p) => p.id);
      } else if (galleryFilter.selectedPlatform) {
        platformIds = [galleryFilter.selectedPlatform.id];
      }
      return {
        searchTerm: galleryFilter.searchTerm,
        platformIds,
        collectionId: this.currentCollection?.id ?? null,
        virtualCollectionId: this.currentVirtualCollection?.id ?? null,
        smartCollectionId: this.currentSmartCollection?.id ?? null,
        limit: WINDOW_SIZE,
        offset,
        orderBy: this.orderBy,
        orderDir: this.orderDir,
        groupByMetaId: this._shouldGroupRoms() && this.onGalleryView,
        filterMatched: galleryFilter.filterMatched,
        filterFavorites: galleryFilter.filterFavorites,
        filterDuplicates: galleryFilter.filterDuplicates,
        filterPlayables: galleryFilter.filterPlayables,
        filterRA: galleryFilter.filterRA,
        filterMissing: galleryFilter.filterMissing,
        filterVerified: galleryFilter.filterVerified,
        selectedGenres: galleryFilter.selectedGenres,
        selectedFranchises: galleryFilter.selectedFranchises,
        selectedCollections: galleryFilter.selectedCollections,
        selectedCompanies: galleryFilter.selectedCompanies,
        selectedAgeRatings: galleryFilter.selectedAgeRatings,
        selectedRegions: galleryFilter.selectedRegions,
        selectedLanguages: galleryFilter.selectedLanguages,
        selectedPlayerCounts: galleryFilter.selectedPlayerCounts,
        selectedStatuses: galleryFilter.selectedStatuses,
        genresLogic: galleryFilter.genresLogic,
        franchisesLogic: galleryFilter.franchisesLogic,
        collectionsLogic: galleryFilter.collectionsLogic,
        companiesLogic: galleryFilter.companiesLogic,
        ageRatingsLogic: galleryFilter.ageRatingsLogic,
        regionsLogic: galleryFilter.regionsLogic,
        languagesLogic: galleryFilter.languagesLogic,
        statusesLogic: galleryFilter.statusesLogic,
        playerCountsLogic: galleryFilter.playerCountsLogic,
      };
    },

    /** Fetch the window that contains `position` (rounding down to the
     * window grid). Dedupes against pending / loaded windows. The very
     * first window also seeds `total` and `charIndex`. */
    async fetchWindowAt(position: number): Promise<void> {
      if (position < 0) return;
      const offset = alignToWindow(position);
      // Total is unknown for offset 0; for any non-initial offset, refuse
      // to fetch past total.
      if (this.total > 0 && offset >= this.total) return;
      if (this.loadedWindows.has(offset)) return;
      if (this.pendingWindows.has(offset)) return;

      this.pendingWindows.add(offset);
      this.failedWindows.delete(offset);
      if (offset === 0 && !this.hasInitial) this.initialFetching = true;

      const galleryFilter = storeGalleryFilter();
      const platformsStore = storePlatforms();
      const params = this._buildRequestParams(galleryFilter, offset);

      try {
        const response = await romApi.getRoms(params);
        // Re-check that this window is still relevant — invalidateWindows
        // / resetGallery may have run while we were waiting.
        if (!this.pendingWindows.has(offset)) return;

        const data = response.data;
        if (data.total !== null && data.total !== undefined) {
          this.total = data.total;
        }
        if (data.char_index) this.charIndex = data.char_index;
        if (data.rom_id_index) this.romIdIndex = data.rom_id_index;

        // Place items at their absolute positions (offset .. offset + N).
        data.items.forEach((rom, idx) => {
          this.byPosition.set(offset + idx, rom);
        });
        // Trigger reactivity for consumers using `byPosition` as a Map.
        // Pinia's reactivity tracks Map.set so this should propagate.
        this.byPosition = new Map(this.byPosition);

        this.loadedWindows.add(offset);

        // Fan out gallery-filter side effects exactly once on the first
        // window (matches v1 behaviour for the filter side panels).
        if (offset === 0 && data.filter_values) {
          if (galleryFilter.filterPlatforms.length === 0) {
            galleryFilter.setFilterPlatforms(
              platformsStore.allPlatforms.filter((p) =>
                data.filter_values.platforms.includes(p.id),
              ),
            );
          }
          galleryFilter.setFilterCollections(data.filter_values.collections);
          galleryFilter.setFilterGenres(data.filter_values.genres);
          galleryFilter.setFilterFranchises(data.filter_values.franchises);
          galleryFilter.setFilterCompanies(data.filter_values.companies);
          galleryFilter.setFilterAgeRatings(data.filter_values.age_ratings);
          galleryFilter.setFilterRegions(data.filter_values.regions);
          galleryFilter.setFilterLanguages(data.filter_values.languages);
          galleryFilter.setFilterPlayerCounts(data.filter_values.player_counts);
        }
      } catch (err) {
        this.failedWindows.add(offset);
        // Surface in console; UI keeps the skeletons in place — the
        // window can be retried by re-entering the row.
        console.error("[v2GalleryRoms] window fetch failed", offset, err);
      } finally {
        this.pendingWindows.delete(offset);
        if (offset === 0) this.initialFetching = false;
      }
    },

    /** Apply (in place) an updated ROM to whatever position currently
     * holds it — used by edit / favourite / status flows. */
    update(rom: SimpleRom) {
      let changed = false;
      for (const [pos, existing] of this.byPosition) {
        if (existing.id === rom.id) {
          this.byPosition.set(pos, rom);
          changed = true;
          break;
        }
      }
      if (changed) this.byPosition = new Map(this.byPosition);
    },

    /** Drop ROMs by id (delete flow). Positions become "holes" — kept
     * sparse rather than re-indexed; the next gallery refresh closes the
     * gaps. */
    remove(roms: SimpleRom[]) {
      const ids = new Set(roms.map((r) => r.id));
      let changed = false;
      for (const [pos, existing] of this.byPosition) {
        if (ids.has(existing.id)) {
          this.byPosition.delete(pos);
          changed = true;
        }
      }
      if (changed) this.byPosition = new Map(this.byPosition);
    },
  },
});
