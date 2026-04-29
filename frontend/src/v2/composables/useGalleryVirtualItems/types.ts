// Discriminated union describing every kind of row that can live inside a
// virtualised gallery scroller. The view turns this list into a single
// RVirtualScroller and renders per kind via a template switch.
//
// Heights are approximate — Vuetify's v-virtual-scroll uses them as the
// initial estimate before measuring rendered nodes. Off-by-tens is fine.
//
// Rows are built for the FULL gallery (positions 0..total-1), not just
// the loaded subset. Each row's slots either point to a real `SimpleRom`
// or carry a skeleton placeholder; the view triggers a window fetch on
// the store when a row carrying skeletons becomes visible.
import type { SimpleRom } from "@/stores/roms";

export type GallerySlot =
  | { kind: "rom"; position: number; rom: SimpleRom }
  | { kind: "skeleton"; position: number };

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
      slots: GallerySlot[];
      /** Letters covered by this row's position range (from server's
       * charIndex). Drives AlphaStrip spy highlight even when the row's
       * cards aren't loaded yet. */
      letters: readonly string[];
      /** True when at least one slot is a skeleton — view uses this to
       * decide whether to trigger a window prefetch. */
      hasMissing: boolean;
    }
  | { kind: "list-table"; key: string }
  | { kind: "load-more"; key: string; remaining: number; loading: boolean }
  | { kind: "empty"; key: string; message: string }
  | { kind: "skeleton-row"; key: string; index: number };

export type GalleryItemKind = GalleryItem["kind"];
