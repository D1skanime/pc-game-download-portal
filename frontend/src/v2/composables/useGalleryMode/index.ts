// useGalleryMode — global gallery-view preferences backed by localStorage.
// Two orthogonal axes control how roms render in Platform / Collection /
// Search, plus a toolbar-placement preference that layouts read.
//
//   * groupBy          — "letter" | "none"   (default "none")
//   * layout           — "grid"   | "list"   (default "grid")
//   * toolbarPosition  — "header" | "floating" (default "header")
//
// Persistence is global (one set of prefs across galleries — matches v1).
import { useLocalStorage, type RemovableRef } from "@vueuse/core";

export type GroupByMode = "letter" | "none";
export type LayoutMode = "grid" | "list";
export type ToolbarPosition = "header" | "floating";

const groupBy = useLocalStorage<GroupByMode>("v2.gallery.groupBy", "none");
const layout = useLocalStorage<LayoutMode>("v2.gallery.layout", "grid");
const toolbarPosition = useLocalStorage<ToolbarPosition>(
  "v2.gallery.toolbarPosition",
  "header",
);

export interface GalleryMode {
  groupBy: RemovableRef<GroupByMode>;
  layout: RemovableRef<LayoutMode>;
  toolbarPosition: RemovableRef<ToolbarPosition>;
}

export function useGalleryMode(): GalleryMode {
  return { groupBy, layout, toolbarPosition };
}
