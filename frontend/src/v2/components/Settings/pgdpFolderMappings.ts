import storageApi from "@/services/api/storage";
import type { Platform } from "@/v2/data/adapters/legacy/stores/platforms";

export interface PgdPFolderMappingRow {
  fsSlug: string;
  slug?: string;
  displayName?: string;
  type: "auto";
}

export async function loadPgdPFolderMappings(
  platforms: readonly Platform[],
): Promise<PgdPFolderMappingRow[]> {
  const rows = await Promise.all(
    platforms
      .filter((platform) => platform.id > 0)
      .map(async (platform) => {
        try {
          const { data } = await storageApi.getMapping(platform.id);
          return {
            fsSlug: data.relative_path,
            slug: platform.slug,
            displayName: platform.display_name || platform.name,
            type: "auto" as const,
          };
        } catch {
          return null;
        }
      }),
  );

  return rows
    .filter((row): row is NonNullable<typeof row> => row !== null)
    .sort((a, b) => a.fsSlug.localeCompare(b.fsSlug));
}
