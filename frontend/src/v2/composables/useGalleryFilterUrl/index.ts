// useGalleryFilterUrl — bookmarkable gallery filters via URL query
// params. Round-trips between Vue Router's `route.query` and the v1
// `galleryFilter` Pinia store.
//
// Why: per constitution §VI.D, "active filters / search query / sort"
// are bookmarkable session state — they belong in the URL so anyone
// copying a link reproduces what they see.
//
// Scope today is narrow on purpose: only `searchTerm` round-trips,
// because the v2 surface only exposes the search input. The v2 filter
// drawer is not built yet — when it ships, multi-selects and logic
// operators (genres / franchises / collections / companies / regions /
// languages / age-ratings / player-counts / statuses) plug in here and
// the URL grows with them. Boolean filters (favourites / matched /
// missing / etc.) follow the same pattern.
//
// Direction notes:
//   * URL → store fires on every `route.query.search` change, including
//     browser back/forward and pasted URLs.
//   * Store → URL pushes via `router.replace` (no history entry per
//     keystroke). Skips the push when the URL already matches.
//   * On mount we apply the URL value once so the gallery view reads the
//     right `searchTerm` before its `searchInput = ref(searchTerm.value)`
//     line runs.
//
// The composable does NOT clear `searchTerm` on unmount — the next
// gallery view's mount will sync from its own URL (which usually has no
// `?search=`), so the value naturally clears.
import { storeToRefs } from "pinia";
import { onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import storeGalleryFilter from "@/stores/galleryFilter";

export function useGalleryFilterUrl() {
  const route = useRoute();
  const router = useRouter();
  const filter = storeGalleryFilter();
  const { searchTerm } = storeToRefs(filter);

  function urlSearch(): string | null {
    const q = route.query.search;
    return typeof q === "string" && q.length > 0 ? q : null;
  }

  function applyFromUrl() {
    const v = urlSearch();
    if (v !== searchTerm.value) searchTerm.value = v;
  }

  // Mount: pull whatever the URL currently holds into the store BEFORE
  // the view's setup reads `searchTerm.value` for its input.
  applyFromUrl();
  onMounted(applyFromUrl);

  // URL → store. Covers back/forward / addressbar paste / programmatic
  // route changes. Compares before writing to avoid feedback loops with
  // the store→URL watcher below.
  watch(
    () => route.query.search,
    () => applyFromUrl(),
  );

  // Store → URL. `router.replace` keeps history clean (one entry per
  // gallery view, not one per keystroke).
  watch(searchTerm, (next) => {
    const desired = next && next.length > 0 ? next : undefined;
    const current =
      typeof route.query.search === "string" ? route.query.search : undefined;
    if (desired === current) return;
    const nextQuery = { ...route.query };
    if (desired === undefined) {
      delete nextQuery.search;
    } else {
      nextQuery.search = desired;
    }
    router.replace({ query: nextQuery });
  });
}
