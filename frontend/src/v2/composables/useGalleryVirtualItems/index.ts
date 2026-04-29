// useGalleryVirtualItems — turns the live gallery state (mode, ROMs,
// pagination, columns) into a flat list of `GalleryItem`s that an
// RVirtualScroller can render with one slot per kind.
//
// Why a single list:
//   * One scroll surface (no nested scrollbars) — hero, toolbar, content,
//     load-more all flow together.
//   * Virtualisation extends to libraries with thousands of ROMs without
//     view-specific tuning.
//
// AlphaStrip integration is index-based: `letterToIndex` maps each
// available letter to the index of its first item in `virtualItems`, which
// the view feeds straight into RVirtualScroller's `scrollToIndex(idx)`.
import { computed, type ComputedRef, type Ref } from "vue";
import type { SimpleRom } from "@/stores/roms";
import { romBucketLetter } from "@/v2/utils/romLetter";
import type { GroupByMode, LayoutMode } from "../useGalleryMode";
import type { LetterGroup } from "../useLetterGroups";
import type { GalleryItem } from "./types";

export type { GalleryItem, GalleryItemKind } from "./types";

interface Options {
  /** Render hero (InfoPanel / PageHeader) as the first item. */
  hasHero: Ref<boolean> | ComputedRef<boolean>;
  /** Render the toolbar inline (header dock). */
  toolbarInline: Ref<boolean> | ComputedRef<boolean>;
  layout: Ref<LayoutMode> | ComputedRef<LayoutMode>;
  groupBy: Ref<GroupByMode> | ComputedRef<GroupByMode>;
  /** Loaded ROMs (current page). */
  roms: Ref<SimpleRom[]> | ComputedRef<SimpleRom[]>;
  /** Letter groups (only consulted when groupBy === 'letter'). */
  letterGroups: ComputedRef<LetterGroup[]>;
  /** Current column count for grid modes (responsive). */
  columns: Ref<number> | ComputedRef<number>;
  /** True while the first page is loading and there is nothing to show. */
  loadingInitial: ComputedRef<boolean>;
  /** True if more pages remain on the server. */
  hasMore: ComputedRef<boolean>;
  /** Remaining count from the server (drives the load-more label). */
  remaining: ComputedRef<number>;
  /** True while a load-more fetch is in flight. */
  fetchingMore: ComputedRef<boolean>;
  /** Empty-state message used when the page resolves with zero results. */
  emptyMessage: Ref<string> | ComputedRef<string>;
  /** "Not found" — overrides every body kind with a single empty row. */
  notFound?: Ref<boolean> | ComputedRef<boolean>;
  /** Override the not-found message (defaults to emptyMessage). */
  notFoundMessage?: Ref<string> | ComputedRef<string>;
  /** Skeleton row count while loading the first page. */
  skeletonRowCount?: number;
}

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#".split("");

function chunk<T>(arr: T[], size: number): T[][] {
  if (size <= 0) return [arr];
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

function lettersOf(roms: SimpleRom[]): string[] {
  const set = new Set<string>();
  for (const r of roms) set.add(romBucketLetter(r));
  return [...set];
}

export function useGalleryVirtualItems(opts: Options) {
  const skeletonRows = opts.skeletonRowCount ?? 4;

  const virtualItems = computed<GalleryItem[]>(() => {
    const items: GalleryItem[] = [];

    if (opts.hasHero.value) items.push({ kind: "hero", key: "hero" });
    if (opts.toolbarInline.value)
      items.push({ kind: "toolbar", key: "toolbar" });

    if (opts.notFound?.value) {
      items.push({
        kind: "empty",
        key: "not-found",
        message: opts.notFoundMessage?.value ?? opts.emptyMessage.value,
      });
      return items;
    }

    // List layout — the entire RTable lives in a single virtual item.
    // RTable handles its own paging/scroll internally.
    if (opts.layout.value === "list") {
      items.push({ kind: "list-table", key: "list-table" });
      if (opts.hasMore.value) {
        items.push({
          kind: "load-more",
          key: "load-more",
          remaining: opts.remaining.value,
          loading: opts.fetchingMore.value,
        });
      }
      return items;
    }

    // Grid — initial loading skeleton.
    if (opts.loadingInitial.value) {
      for (let i = 0; i < skeletonRows; i++) {
        items.push({ kind: "skeleton-row", key: `skel-${i}`, index: i });
      }
      return items;
    }

    if (opts.roms.value.length === 0) {
      items.push({
        kind: "empty",
        key: "empty",
        message: opts.emptyMessage.value,
      });
      return items;
    }

    const cols = Math.max(1, opts.columns.value);

    if (opts.groupBy.value === "letter") {
      for (const group of opts.letterGroups.value) {
        items.push({
          kind: "letter-header",
          key: `lh-${group.letter}`,
          letter: group.letter,
        });
        const rows = chunk(group.games, cols);
        rows.forEach((roms, rowIndex) => {
          items.push({
            kind: "row",
            key: `row-${group.letter}-${rowIndex}`,
            rowIndex,
            roms,
            firstLetter: roms[0] ? romBucketLetter(roms[0]) : group.letter,
            // In grouped mode every ROM in the row is the same letter,
            // but compute defensively so the spy logic stays uniform.
            letters: lettersOf(roms),
          });
        });
      }
    } else {
      const rows = chunk(opts.roms.value, cols);
      rows.forEach((roms, rowIndex) => {
        items.push({
          kind: "row",
          key: `row-flat-${rowIndex}`,
          rowIndex,
          roms,
          firstLetter: roms[0] ? romBucketLetter(roms[0]) : "#",
          letters: lettersOf(roms),
        });
      });
    }

    if (opts.hasMore.value) {
      items.push({
        kind: "load-more",
        key: "load-more",
        remaining: opts.remaining.value,
        loading: opts.fetchingMore.value,
      });
    }
    return items;
  });

  // Every letter present in the loaded ROMs — drives AlphaStrip's
  // "available" highlight regardless of whether the letter happens to
  // start a row in flat mode.
  const availableLetters = computed<Set<string>>(() => {
    const set = new Set<string>();
    for (const r of opts.roms.value) set.add(romBucketLetter(r));
    return set;
  });

  // letter → index in virtualItems for scroll-to-letter.
  //   * grouped: the letter-header item is the natural anchor.
  //   * flat:    the row that contains the FIRST ROM of that letter
  //              (may not match the row's `firstLetter` when the letter
  //              starts mid-row).
  const letterToIndex = computed<Map<string, number>>(() => {
    const map = new Map<string, number>();
    const items = virtualItems.value;

    // Pass 1 — grouped mode: pick up letter-header anchors.
    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (it.kind === "letter-header" && !map.has(it.letter)) {
        map.set(it.letter, i);
      }
    }

    // Pass 2 — flat mode: walk the ROMs (already sorted alphabetically)
    // and map each letter's first occurrence to its enclosing row.
    if (opts.groupBy.value !== "letter") {
      let firstRowIdx = -1;
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "row") {
          firstRowIdx = i;
          break;
        }
      }
      if (firstRowIdx >= 0) {
        const cols = Math.max(1, opts.columns.value);
        opts.roms.value.forEach((r, romIdx) => {
          const l = romBucketLetter(r);
          if (map.has(l)) return;
          map.set(l, firstRowIdx + Math.floor(romIdx / cols));
        });
      }
    }

    return map;
  });

  function letterAtIndex(index: number): string | null {
    // Walk back from `index` until we hit a letter-header or row, then
    // report its associated letter. Used by the scroll-spy to derive the
    // currently-visible letter from the first-visible item index.
    const items = virtualItems.value;
    for (let i = Math.min(index, items.length - 1); i >= 0; i--) {
      const it = items[i];
      if (it.kind === "letter-header") return it.letter;
      if (it.kind === "row") return it.firstLetter;
    }
    return null;
  }

  return {
    virtualItems,
    letterToIndex,
    availableLetters,
    letterAtIndex,
    ALPHABET,
  };
}
