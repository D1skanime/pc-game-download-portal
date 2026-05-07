// Platforms list-mode column geometry. Shared between PlatformListHeader
// and PlatformListRow so the title row and every body row line up.
//
// Two columns: name (stretches) + game count (fixed pixel width,
// right-aligned). Kept narrow on purpose — the platforms index is a
// "pick a platform" surface, not a metadata browser.
export const PLATFORM_LIST_GRID_TEMPLATE = "minmax(0, 1fr) 96px";
