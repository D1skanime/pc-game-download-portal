import api from "@/services/api";
import type { Platform } from "@/stores/platforms";

export interface SetupFolder {
  name: string;
  relative_path: string;
  association: "known" | "unknown";
  suggested_platform: string | null;
}
export interface SetupPlatformOption {
  slug: string;
  display_name: string;
}
export interface SetupFolderDiscovery {
  root_label: string;
  folders: SetupFolder[];
  platform_options: SetupPlatformOption[];
}
export type SetupFolderDraft = Record<string, string | null>;
export interface SetupFolderAssignment {
  folder_name: string;
  platform_slug: string;
}
export interface SetupFolderAssignmentResponse {
  mappings: Array<{
    folder_name: string;
    platform_slug: string;
    mapping_id: number;
    relative_path: string;
  }>;
  ready: boolean;
  root_health: {
    reachable: boolean;
    readable: boolean;
    non_writable: boolean | null;
  };
}
export interface ExistingPlatform {
  fs_slug: string;
  rom_count: number;
}
export interface SetupLibraryInfo {
  detected_structure: "struct_a" | "struct_b" | null;
  existing_platforms: ExistingPlatform[];
  supported_platforms: Platform[];
}
function discoverFolders() {
  return api.get<SetupFolderDiscovery>("/setup/folders");
}
function assignFolders(assignments: SetupFolderAssignment[]) {
  return api.post<SetupFolderAssignmentResponse>("/setup/folders/assign", {
    assignments,
  });
}
function getLibraryInfo() {
  return api.get<SetupLibraryInfo>("/setup/library");
}
export default { discoverFolders, assignFolders, getLibraryInfo };
