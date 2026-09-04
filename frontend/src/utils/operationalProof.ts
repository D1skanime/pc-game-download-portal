export interface StorageProofPlatform {
  id: number;
}

export function pickStoragePlatform<T extends StorageProofPlatform>(
  platforms: T[],
): T | undefined {
  return platforms.find((platform) => platform.id > 0);
}
