import { storeToRefs } from "pinia";
import setupApi, { type SetupLibraryInfo } from "@/services/api/setup";
import storeCollections from "@/stores/collections";
import storePlatforms from "@/stores/platforms";
import storeRoms, { type SimpleRom } from "@/stores/roms";

export type { SetupLibraryInfo, SimpleRom };

export function useHomeData() {
  const romsStore = storeRoms();
  const platformsStore = storePlatforms();
  const collectionsStore = storeCollections();
  return {
    setupApi,
    romsStore,
    platformsStore,
    collectionsStore,
    refs: {
      roms: storeToRefs(romsStore),
      platforms: storeToRefs(platformsStore),
      collections: storeToRefs(collectionsStore),
    },
  };
}
