import type { SetBackgroundArt } from "@/v2/composables/useBackgroundArt";
import type { BackgroundAudioTrack } from "@/v2/composables/useBackgroundAudio";

export const BACKGROUND_ROTATION_MS = 10_000;

type BackgroundAudioRom = {
  id: number;
  files: Array<{ id: number; category?: string | null; file_name: string }>;
  local_background_audio_file_ids?: number[];
  owned_background_audio_media_ids?: number[];
  owned_media?: Array<{
    id: number;
    role: string;
    state: string;
  }>;
};

export function selectedBackgroundAudioTracks(
  rom: BackgroundAudioRom,
): BackgroundAudioTrack[] {
  const selectedLocalIds = new Set(rom.local_background_audio_file_ids ?? []);
  const selectedOwnedIds = new Set(rom.owned_background_audio_media_ids ?? []);
  const localTracks = rom.files
    .filter(
      (file) => selectedLocalIds.has(file.id) && file.category === "soundtrack",
    )
    .map((file) => ({
      id: file.id,
      url: `/api/roms/${file.id}/files/content/${encodeURIComponent(file.file_name)}`,
    }));
  const ownedTracks = (rom.owned_media ?? [])
    .filter(
      (media) =>
        selectedOwnedIds.has(media.id) &&
        media.role === "soundtrack" &&
        media.state === "active",
    )
    .map((media) => ({
      id: media.id,
      url: `/api/roms/${rom.id}/media/${media.id}/content`,
    }));
  return [...localTracks, ...ownedTracks];
}

export function scheduleBackgroundRotation(
  backgrounds: string[],
  fallback: string | null,
  shouldRotate: boolean,
  setBackground: SetBackgroundArt,
): () => void {
  setBackground(backgrounds[0] ?? fallback);
  if (!shouldRotate || backgrounds.length < 2) return () => undefined;

  let index = 0;
  const interval = setInterval(() => {
    index = (index + 1) % backgrounds.length;
    setBackground(backgrounds[index]);
  }, BACKGROUND_ROTATION_MS);
  return () => clearInterval(interval);
}
