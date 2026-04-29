// useGalleryVirtualItems — turns the live gallery state (mode, total
// count, char_index, loaded windows, columns) into a flat list of
// `GalleryItem`s that an RVirtualScroller can render with one slot per
// kind.
//
// Why a single list:
//   * One scroll surface (no nested scrollbars) — hero, toolbar, content,
//     load-more all flow together.
//   * Virtualisation extends to libraries with thousands of ROMs without
//     view-specific tuning.
//
// Sparse rendering:
//   Rows are built for every position 0..total-1, not only the loaded
//   ROMs. Each row's slots either resolve to a real `SimpleRom` (via
//   `getRomAt`) or fall back to a skeleton placeholder. The view drives
//   window prefetches when a row carrying skeletons becomes visible —
//   that's how scrolling fast or jumping via AlphaStrip stays smooth: the
//   user sees a layout-stable skeleton grid, then cards stream in.
//
// AlphaStrip integration is index-based:
//   `letterToIndex` maps each available letter to the index of its first
//   item in `virtualItems`, fed straight into
//   `RVirtualScroller.scrollToIndex(idx)`. `availableLetters` derives
//   from the server's `charIndex` so every letter that exists in the
//   gallery is clickable, even if its window hasn't been fetched yet.
import { computed, type ComputedRef, type Ref } from "vue";
import type { SimpleRom } from "@/stores/roms";
import type { GroupByMode, LayoutMode } from "../useGalleryMode";
import type { GalleryItem, GallerySlot } from "./types";

export type { GalleryItem, GalleryItemKind, GallerySlot } from "./types";

interface Options {
  /** Render hero (InfoPanel / PageHeader) as the first item. */
  hasHero: Ref<boolean> | ComputedRef<boolean>;
  /** Render the toolbar inline (header dock). */
  toolbarInline: Ref<boolean> | ComputedRef<boolean>;
  layout: Ref<LayoutMode> | ComputedRef<LayoutMode>;
  groupBy: Ref<GroupByMode> | ComputedRef<GroupByMode>;
  /** Total count of ROMs in the active gallery (server-provided). */
  total: Ref<number> | ComputedRef<number>;
  /** Letter → first-position map from the server. Backend ships letters
   * lowercase / digits — `availableLetters` and the row letter sets
   * normalise to AlphaStrip's bucket shape. */
  charIndex: Ref<Record<string, number>> | ComputedRef<Record<string, number>>;
  /** Lookup function — returns null when the position's window hasn't
   * been fetched. */
  getRomAt: (position: number) => SimpleRom | null;
  /** Tracking ref so this composable re-runs when loaded windows change.
   * Pass any reactive value the consumer mutates per fetch (e.g.
   * `store.byPosition` or `store.loadedWindows.size`). */
  loadedTick: Ref<unknown> | ComputedRef<unknown>;
  /** Current column count for grid modes (responsive). */
  columns: Ref<number> | ComputedRef<number>;
  /** True while the very first window is in flight (no `total` yet). */
  loadingInitial: ComputedRef<boolean>;
  /** Empty-state message used when the page resolves with zero results. */
  emptyMessage: Ref<string> | ComputedRef<string>;
  /** "Not found" — overrides every body kind with a single empty row. */
  notFound?: Ref<boolean> | ComputedRef<boolean>;
  /** Override the not-found message (defaults to emptyMessage). */
  notFoundMessage?: Ref<string> | ComputedRef<string>;
  /** Skeleton row count while loading the first window. */
  skeletonRowCount?: number;
}

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#".split("");

function normaliseBackendLetter(raw: string): string {
  if (!raw) return "#";
  const c = raw.charAt(0).toUpperCase();
  return /[A-Z]/.test(c) ? c : "#";
}

interface LetterRange {
  letter: string;
  start: number;
  end: number; // exclusive
}

function buildLetterRanges(
  charIndex: Record<string, number>,
  total: number,
): LetterRange[] {
  const entries = Object.entries(charIndex)
    .map(([letter, off]) => [normaliseBackendLetter(letter), off] as const)
    .sort((a, b) => a[1] - b[1]);
  const ranges: LetterRange[] = [];
  for (let i = 0; i < entries.length; i++) {
    const [letter, start] = entries[i];
    const end = entries[i + 1]?.[1] ?? total;
    // Backend may collapse multiple raw letters into "#" (digits, etc.) —
    // merge into the previous range rather than emit duplicates.
    const last = ranges[ranges.length - 1];
    if (last && last.letter === letter) {
      last.end = end;
      continue;
    }
    ranges.push({ letter, start, end });
  }
  return ranges;
}

function lettersInRange(
  ranges: LetterRange[],
  startPos: number,
  endPos: number,
): string[] {
  const out: string[] = [];
  for (const r of ranges) {
    if (r.end > startPos && r.start < endPos) out.push(r.letter);
  }
  return out;
}

function buildSlots(
  startPos: number,
  endPos: number,
  getRomAt: (p: number) => SimpleRom | null,
): { slots: GallerySlot[]; hasMissing: boolean } {
  const slots: GallerySlot[] = [];
  let hasMissing = false;
  for (let p = startPos; p < endPos; p++) {
    const rom = getRomAt(p);
    if (rom) {
      slots.push({ kind: "rom", position: p, rom });
    } else {
      slots.push({ kind: "skeleton", position: p });
      hasMissing = true;
    }
  }
  return { slots, hasMissing };
}

export function useGalleryVirtualItems(opts: Options) {
  const skeletonRows = opts.skeletonRowCount ?? 4;

  const letterRanges = computed<LetterRange[]>(() =>
    buildLetterRanges(opts.charIndex.value, opts.total.value),
  );

  const virtualItems = computed<GalleryItem[]>(() => {
    // Reading `loadedTick` forces re-evaluation when windows load.
    void opts.loadedTick.value;

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
    // RTable handles its own paging internally, so no skeleton rows.
    if (opts.layout.value === "list") {
      items.push({ kind: "list-table", key: "list-table" });
      return items;
    }

    // Grid + first-window-loading — show skeleton rows until the server
    // tells us `total` and `charIndex`.
    if (opts.loadingInitial.value && opts.total.value === 0) {
      for (let i = 0; i < skeletonRows; i++) {
        items.push({ kind: "skeleton-row", key: `skel-${i}`, index: i });
      }
      return items;
    }

    if (opts.total.value === 0) {
      items.push({
        kind: "empty",
        key: "empty",
        message: opts.emptyMessage.value,
      });
      return items;
    }

    const cols = Math.max(1, opts.columns.value);
    const total = opts.total.value;
    const ranges = letterRanges.value;

    if (opts.groupBy.value === "letter") {
      // Group by letter — each letter section gets a header followed by
      // its own row chunks (rows always restart at the letter's first
      // position, so a letter never shares a visual row with another).
      for (const range of ranges) {
        items.push({
          kind: "letter-header",
          key: `lh-${range.letter}`,
          letter: range.letter,
        });
        const rowsInGroup = Math.ceil((range.end - range.start) / cols);
        for (let r = 0; r < rowsInGroup; r++) {
          const rowStart = range.start + r * cols;
          const rowEnd = Math.min(rowStart + cols, range.end);
          const { slots, hasMissing } = buildSlots(
            rowStart,
            rowEnd,
            opts.getRomAt,
          );
          items.push({
            kind: "row",
            key: `row-${range.letter}-${r}`,
            rowIndex: r,
            startPosition: rowStart,
            endPosition: rowEnd,
            slots,
            letters: [range.letter],
            hasMissing,
          });
        }
      }
    } else {
      // Flat — rows are aligned to absolute positions.
      const totalRows = Math.ceil(total / cols);
      for (let r = 0; r < totalRows; r++) {
        const rowStart = r * cols;
        const rowEnd = Math.min(rowStart + cols, total);
        const { slots, hasMissing } = buildSlots(
          rowStart,
          rowEnd,
          opts.getRomAt,
        );
        items.push({
          kind: "row",
          key: `row-flat-${r}`,
          rowIndex: r,
          startPosition: rowStart,
          endPosition: rowEnd,
          slots,
          letters: lettersInRange(ranges, rowStart, rowEnd),
          hasMissing,
        });
      }
    }

    return items;
  });

  // AlphaStrip available letters — every letter in the server's charIndex,
  // independent of which windows are currently loaded.
  const availableLetters = computed<Set<string>>(() => {
    const set = new Set<string>();
    for (const r of letterRanges.value) set.add(r.letter);
    return set;
  });

  // letter → index in virtualItems for scroll-to-letter.
  const letterToIndex = computed<Map<string, number>>(() => {
    const map = new Map<string, number>();
    const items = virtualItems.value;

    // Pass 1 — grouped mode: letter-header anchors are exact.
    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (it.kind === "letter-header" && !map.has(it.letter)) {
        map.set(it.letter, i);
      }
    }

    if (opts.groupBy.value !== "letter") {
      // Flat mode — for each letter range, jump to the row that holds
      // its first position.
      let firstRowIdx = -1;
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "row") {
          firstRowIdx = i;
          break;
        }
      }
      if (firstRowIdx >= 0) {
        const cols = Math.max(1, opts.columns.value);
        for (const range of letterRanges.value) {
          if (map.has(range.letter)) continue;
          map.set(range.letter, firstRowIdx + Math.floor(range.start / cols));
        }
      }
    }

    return map;
  });

  return {
    virtualItems,
    letterToIndex,
    availableLetters,
    ALPHABET,
  };
}
