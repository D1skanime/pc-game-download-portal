// List-mode column config shared between `GameListHeader` (sortable
// column titles) and `GameListRow` (real + skeleton bodies).
//
// CSS grid template lives here so both components pick up the same
// column geometry — change column widths in one place and the header
// stays aligned with every row underneath. The fr units in the title
// column let the row stretch to fill remaining width while the metric
// columns hold fixed pixel widths so numbers align cleanly.
import type { SimpleRom } from "@/stores/roms";

export type ListSortKey = Extract<
  keyof SimpleRom,
  | "name"
  | "fs_size_bytes"
  | "created_at"
  | "first_release_date"
  | "average_rating"
>;

export interface ListColumn {
  /** Sort key (matches `galleryRoms.orderBy`). `null` for non-sortable
   * display-only columns (icon labels, action menus). */
  key: ListSortKey | "languages" | "regions" | "actions";
  /** Column header label. Empty string renders no text (used for the
   * trailing actions column). */
  label: string;
  /** Whether the column header is clickable to toggle sort. */
  sortable: boolean;
  align?: "start" | "end";
}

export const LIST_COLUMNS: readonly ListColumn[] = [
  { key: "name", label: "Title", sortable: true, align: "start" },
  { key: "fs_size_bytes", label: "Size", sortable: true, align: "start" },
  { key: "created_at", label: "Added", sortable: true, align: "start" },
  {
    key: "first_release_date",
    label: "Released",
    sortable: true,
    align: "start",
  },
  { key: "average_rating", label: "⭐", sortable: true, align: "start" },
  { key: "languages", label: "🔠", sortable: false, align: "start" },
  { key: "regions", label: "🌎", sortable: false, align: "start" },
  { key: "actions", label: "", sortable: false, align: "end" },
];

/** Single grid template applied to both the header row and every body
 * row so columns line up vertically across the whole list. */
export const LIST_GRID_TEMPLATE =
  "minmax(0, 1.6fr) 88px 96px 84px 56px 110px 110px 56px";
