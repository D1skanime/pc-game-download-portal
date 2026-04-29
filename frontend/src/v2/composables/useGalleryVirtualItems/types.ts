// Discriminated union describing every kind of row that can live inside a
// virtualised gallery scroller. The view turns this list into a single
// RVirtualScroller and renders per kind via a template switch.
//
// Heights are approximate — Vuetify's v-virtual-scroll uses them as the
// initial estimate before measuring rendered nodes. Off-by-tens is fine.
import type { SimpleRom } from "@/stores/roms";

export type GalleryItem =
  | { kind: "hero"; key: string }
  | { kind: "toolbar"; key: string }
  | { kind: "letter-header"; key: string; letter: string }
  | {
      kind: "row";
      key: string;
      rowIndex: number;
      roms: SimpleRom[];
      firstLetter: string;
      /** Distinct letters covered by this row's ROMs (may span A/B/C in flat mode). */
      letters: readonly string[];
    }
  | { kind: "list-table"; key: string }
  | { kind: "load-more"; key: string; remaining: number; loading: boolean }
  | { kind: "empty"; key: string; message: string }
  | { kind: "skeleton-row"; key: string; index: number };

export type GalleryItemKind = GalleryItem["kind"];
