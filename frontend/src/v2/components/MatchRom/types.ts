// Shared types + helpers for the MatchRom body variants (grid /
// list). The dialog shell owns search state and API calls; each body
// variant renders results and the per-match cover picker in
// its own visual language.
import type { SearchRom } from "@/v2/data/adapters/legacy/stores/roms";

export type PcMatchableComponentKind =
  "base" | "update" | "dlc" | "hotfix" | "language_pack" | "extra";

export type PcMatchTarget =
  | { kind: "rom"; romId: number; label: string }
  | {
      kind: "component";
      romId: number;
      componentId: number;
      componentKind: PcMatchableComponentKind;
      label: string;
    };

export function isPcMatchTarget(value: unknown): value is PcMatchTarget {
  if (!value || typeof value !== "object" || !("kind" in value)) return false;
  return value.kind === "rom" || value.kind === "component";
}

export type MatchSearchRom = SearchRom & {
  steam_url_cover?: string;
};

export type PcMatchProvider =
  | "igdb"
  | "steam"
  | "moby"
  | "sgdb"
  | "launchbox"
  | "screenscraper"
  | "flashpoint"
  | "libretro";

export type PcMatchCoverField =
  | "igdb_url_cover"
  | "steam_url_cover"
  | "moby_url_cover"
  | "sgdb_url_cover"
  | "launchbox_url_cover"
  | "ss_url_cover"
  | "flashpoint_url_cover"
  | "libretro_url_cover";

export interface PcCandidateMedia {
  kind: string;
  url: string;
}

export interface PcCandidateCover {
  field: PcMatchCoverField;
  url: string;
}

const PC_MATCH_COVER_FIELDS: Readonly<
  Record<PcMatchProvider, PcMatchCoverField>
> = {
  igdb: "igdb_url_cover",
  steam: "steam_url_cover",
  moby: "moby_url_cover",
  sgdb: "sgdb_url_cover",
  launchbox: "launchbox_url_cover",
  screenscraper: "ss_url_cover",
  flashpoint: "flashpoint_url_cover",
  libretro: "libretro_url_cover",
};

function isPcMatchProvider(value: string): value is PcMatchProvider {
  return Object.hasOwn(PC_MATCH_COVER_FIELDS, value);
}

export function getPcCandidateCover(candidate: {
  provider: string;
  media: readonly PcCandidateMedia[];
}): PcCandidateCover | null {
  if (!isPcMatchProvider(candidate.provider)) return null;
  const url = candidate.media.find((media) => media.kind === "cover")?.url;
  if (!url) return null;
  return { field: PC_MATCH_COVER_FIELDS[candidate.provider], url };
}

export type SourceName =
  | "IGDB"
  | "Steam"
  | "Mobygames"
  | "Screenscraper"
  | "Flashpoint"
  | "Launchbox"
  | "Libretro"
  | "SteamGridDB";

export interface MatchedSource {
  url_cover: string;
  name: SourceName;
  logo_path: string;
}

interface SourceDef {
  urlKey: keyof MatchSearchRom;
  name: SourceName;
  logo: string;
}

const SOURCE_DEFS: readonly SourceDef[] = [
  {
    urlKey: "igdb_url_cover",
    name: "IGDB",
    logo: "/assets/scrappers/igdb.png",
  },
  {
    urlKey: "steam_url_cover",
    name: "Steam",
    logo: "/assets/scrappers/steam.svg",
  },
  {
    urlKey: "moby_url_cover",
    name: "Mobygames",
    logo: "/assets/scrappers/moby.png",
  },
  {
    urlKey: "ss_url_cover",
    name: "Screenscraper",
    logo: "/assets/scrappers/ss.png",
  },
  {
    urlKey: "sgdb_url_cover",
    name: "SteamGridDB",
    logo: "/assets/scrappers/sgdb.png",
  },
  {
    urlKey: "flashpoint_url_cover",
    name: "Flashpoint",
    logo: "/assets/scrappers/flashpoint.png",
  },
  {
    urlKey: "launchbox_url_cover",
    name: "Launchbox",
    logo: "/assets/scrappers/launchbox.png",
  },
  {
    urlKey: "libretro_url_cover",
    name: "Libretro",
    logo: "/assets/scrappers/libretro.png",
  },
];

export function getMatchSources(matchedRom: MatchSearchRom): MatchedSource[] {
  const out: MatchedSource[] = [];
  for (const def of SOURCE_DEFS) {
    const url = matchedRom[def.urlKey] as string | undefined | null;
    if (url) {
      out.push({ url_cover: url, name: def.name, logo_path: def.logo });
    }
  }
  return out;
}

export function matchKey(rom: MatchSearchRom): string {
  return `${rom.igdb_id ?? "_"}-${rom.moby_id ?? "_"}-${rom.ss_id ?? "_"}-${rom.name}`;
}

// Default cover URL for a search result — used when rendering the
// match as a card. SearchRom carries only `*_url_cover` per provider
// (no `path_cover_*` / `url_cover` like SimpleRom), so cards fed to
// GameCard need `cover-src` set explicitly. First available provider
// cover wins; null means no provider has a cover at all (placeholder).
// Uses a truthy filter (not `??`) because the backend sometimes returns
// empty strings for absent providers — `??` would treat "" as "present"
// and short-circuit before reaching the actually-populated provider.
export function firstAvailableCover(r: MatchSearchRom): string | null {
  const candidates: Array<string | undefined> = [
    r.igdb_url_cover,
    r.steam_url_cover,
    r.moby_url_cover,
    r.ss_url_cover,
    r.sgdb_url_cover,
    r.flashpoint_url_cover,
    r.launchbox_url_cover,
    r.libretro_url_cover,
  ];
  return candidates.find((c): c is string => Boolean(c)) ?? null;
}

export interface ConfirmPayload {
  matchedRom: MatchSearchRom;
  cover: MatchedSource | undefined;
}

export type MatchVariant = "list" | "grid";
