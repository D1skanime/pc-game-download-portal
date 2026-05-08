// Platforms list-mode column geometry. Shared between PlatformListHeader
// and PlatformListRow so the title row and every body row line up.
//
// Five columns: name (stretches) + family + category + generation +
// game count (right-aligned). The three metadata columns surface the
// same axes the toolbar can group by — so a user reading the list in a
// flat order can still see what would have separated them. They are
// hidden on narrow viewports (see PlatformListRow / PlatformListHeader)
// to keep the row legible without horizontal scroll.
export const PLATFORM_LIST_GRID_TEMPLATE =
  "minmax(0, 1fr) 160px 130px 110px 96px";

// Narrow-viewport template — drops every metadata column. Same name +
// games layout the list shipped with originally, so the mobile view
// stays the "pick a platform" affordance it always was.
export const PLATFORM_LIST_GRID_TEMPLATE_COMPACT = "minmax(0, 1fr) 96px";

// Label helpers shared by the row and the index view's group-by
// computeds, so the two surfaces never disagree on how a category or
// generation should be written.

/** Prettify an IGDB-style snake_case category ("portable_console" →
 *  "Portable console"). Empty string returns empty so the caller can
 *  decide on a placeholder. */
export function prettifyPlatformCategory(raw: string): string {
  return raw
    .split("_")
    .map((part) => (part ? part.charAt(0).toUpperCase() + part.slice(1) : part))
    .join(" ");
}

/** "1st generation" / "2nd generation" / … with English ordinals. */
export function platformGenerationLabel(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  let suffix: string;
  if (mod10 === 1 && mod100 !== 11) suffix = "st";
  else if (mod10 === 2 && mod100 !== 12) suffix = "nd";
  else if (mod10 === 3 && mod100 !== 13) suffix = "rd";
  else suffix = "th";
  return `${n}${suffix} generation`;
}
