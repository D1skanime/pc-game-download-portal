// useGalleryVirtualItems — turns the gallery's structural state (mode,
// total, charIndex, columns) into a flat list of `GalleryItem`s that an
// RVirtualScroller can render with one slot per kind.
//
// Performance contract: this composable is STRUCTURAL — it only depends
// on layout / groupBy / total / charIndex / columns / loadingInitial.
// It does NOT read the loaded ROMs (`byPosition`). Per-row slot data is
// resolved by the view at render time via `store.getRomAt(position)`,
// which scopes Vue's reactivity to the specific row that holds the
// resolved position. A window fetch that lands 72 ROMs only re-renders
// up to ⌈72/cols⌉ rows, not the entire virtualItems array.
//
// AlphaStrip integration is index-based: `letterToIndex` maps each
// available letter to the index of its first item in `virtualItems`,
// fed straight into `RVirtualScroller.scrollToIndex(idx)`.
// `availableLetters` derives from the server's `charIndex` so every
// letter that exists in the gallery is clickable, even if its window
// hasn't been fetched yet.
import { computed, type ComputedRef, type Ref } from "vue";
import type { GroupByMode, LayoutMode } from "../useGalleryMode";
import type { GalleryItem } from "./types";

export type { GalleryItem, GalleryItemKind } from "./types";

// Height table per item kind. Drives the virtualiser's exact-offset
// math, so AlphaStrip jumps land precisely on target rows. Values match
// the rendered geometry in the gallery views' CSS:
//   * row / skeleton-row: 213px cover + 7px gap + 16px label + 18px
//     bottom-padding = 254.
//   * letter-header: 20px top + 16px text + 12px bottom = 48 (rounded
//     up to 56 for breathing room).
//   * hero: InfoPanel ≈ 200px content + 28px top + 28px bottom + 12px
//     bottom margin = 268 (rounded to 280).
//   * toolbar: 56px control row + 8px breathing.
//   * load-more / empty: matches the rendered button / centered text.
//   * list-table: deliberately oversized — it's the only natural-flow
//     item, sits at the bottom of the list, and the inner RTable owns
//     its own paging height. We just need a value > the page's content
//     so subsequent items (none in list mode) don't overlap.
const HEIGHT_BY_KIND: Record<GalleryItem["kind"], number> = {
  hero: 280,
  // Toolbar's reserved offset includes ~32px of breathing space below
  // the rendered toolbar so the grid doesn't sit flush against it.
  // The clip-path while stuck uses this same value so content is
  // hidden from y=0 down to here, keeping the gap consistent in both
  // states.
  toolbar: 88,
  "letter-header": 56,
  row: 254,
  "skeleton-row": 254,
  "list-table": 1200,
  "load-more": 80,
  empty: 240,
};

// Signature matches RVirtualScroller's `getItemHeight` prop (which uses
// `unknown` for items because the primitive is generic). Internally
// narrows back to GalleryItem — the caller is always passing items
// produced by `useGalleryVirtualItems`, so the cast is safe.
export function galleryItemHeight(item: unknown): number {
  return HEIGHT_BY_KIND[(item as GalleryItem).kind];
}

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

export function useGalleryVirtualItems(opts: Options) {
  const skeletonRows = opts.skeletonRowCount ?? 4;

  const letterRanges = computed<LetterRange[]>(() =>
    buildLetterRanges(opts.charIndex.value, opts.total.value),
  );

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
          items.push({
            kind: "row",
            key: `row-${range.letter}-${r}`,
            rowIndex: r,
            startPosition: rowStart,
            endPosition: rowEnd,
            letters: [range.letter],
          });
        }
      }
    } else {
      // Flat — rows are aligned to absolute positions.
      const totalRows = Math.ceil(total / cols);
      for (let r = 0; r < totalRows; r++) {
        const rowStart = r * cols;
        const rowEnd = Math.min(rowStart + cols, total);
        items.push({
          kind: "row",
          key: `row-flat-${r}`,
          rowIndex: r,
          startPosition: rowStart,
          endPosition: rowEnd,
          letters: lettersInRange(ranges, rowStart, rowEnd),
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
