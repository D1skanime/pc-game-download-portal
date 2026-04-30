// Discriminated union describing every kind of row that can live inside a
// virtualised gallery scroller. The view turns this list into a single
// RVirtualScroller and renders per kind via a template switch.
//
// IMPORTANT — performance contract: row items are STRUCTURAL only. They
// know which positions they cover but they do NOT carry the actual ROM /
// skeleton data. The view template iterates positions inline and calls
// `store.getRomAt(p)` per slot. That keeps Vue's per-key reactivity
// granular: when a window resolves and a single position transitions
// from skeleton to ROM, only the affected row component re-renders —
// not the entire `virtualItems` array (which would be O(total/cols)
// rebuild and was the source of the scroll-freeze in earlier passes).

export type GalleryItem =
  | { kind: "hero"; key: string }
  | { kind: "toolbar"; key: string }
  | { kind: "letter-header"; key: string; letter: string }
  | {
      kind: "row";
      key: string;
      rowIndex: number;
      startPosition: number;
      endPosition: number; // exclusive
      /** Letters covered by this row's position range (from server's
       * charIndex). Drives AlphaStrip spy highlight even when the row's
       * cards aren't loaded yet. */
      letters: readonly string[];
    }
  | { kind: "list-table"; key: string }
  | { kind: "load-more"; key: string; remaining: number; loading: boolean }
  | { kind: "empty"; key: string; message: string }
  | { kind: "skeleton-row"; key: string; index: number };

export type GalleryItemKind = GalleryItem["kind"];
