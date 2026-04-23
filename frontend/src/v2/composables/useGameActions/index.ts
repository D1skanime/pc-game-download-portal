// useGameActions — shared action handlers for a ROM. One place for
// play / download / favorite / share / match / refresh / edit / delete /
// add-to-collection. Consumed by every surface that shows per-ROM actions
// (MoreMenu on RGameCard, MoreMenu in GameDetails header, etc.) so the
// action list stays in sync.
//
// Usage:
//   const actions = useGameActions(() => rom.value);
//   actions.play(); actions.toggleFavorite(); …
//   actions.isFavorite     // reactive Ref<boolean>
//   actions.canAddToCollection  // reactive Ref<boolean>
import type { Emitter } from "mitt";
import { computed, inject } from "vue";
import { useRouter } from "vue-router";
import { useFavoriteToggle } from "@/composables/useFavoriteToggle";
import storeCollections from "@/stores/collections";
import type { SimpleRom } from "@/stores/roms";
import type { Events } from "@/types/emitter";
import { getDownloadPath } from "@/utils";

export function useGameActions(getRom: () => SimpleRom | null | undefined) {
  const router = useRouter();
  const emitter = inject<Emitter<Events>>("emitter");
  const collectionsStore = storeCollections();
  const { isFavorite, toggleFavorite } = useFavoriteToggle(emitter);

  const isFavorited = computed(() => {
    const rom = getRom();
    return rom ? Boolean(isFavorite(rom)) : false;
  });

  const canAddToCollection = computed(
    () =>
      collectionsStore.allCollections.length > 0 ||
      Boolean(collectionsStore.favoriteCollection),
  );

  function play() {
    const rom = getRom();
    if (!rom) return;
    router.push(`/rom/${rom.id}/ejs`);
  }

  function download() {
    const rom = getRom();
    if (!rom) return;
    const href = getDownloadPath({ rom });
    const a = document.createElement("a");
    a.href = href;
    a.download = rom.fs_name;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function favorite() {
    const rom = getRom();
    if (!rom) return;
    await toggleFavorite(rom);
  }

  async function share() {
    const rom = getRom();
    if (!rom) return;
    const url = window.location.origin + `/rom/${rom.id}`;
    const title = rom.name ?? rom.fs_name_no_ext ?? "ROM";
    const shareData = { title, text: title, url };
    const nav = navigator as Navigator & {
      share?: (data: typeof shareData) => Promise<void>;
    };
    try {
      if (typeof nav.share === "function") {
        await nav.share(shareData);
        return;
      }
      await navigator.clipboard.writeText(url);
      emitter?.emit("snackbarShow", {
        msg: "Link copied to clipboard",
        icon: "mdi-link-variant",
        color: "green",
      });
    } catch {
      // user cancelled or clipboard denied — nothing to do
    }
  }

  function shareQR() {
    const rom = getRom();
    if (!rom) return;
    emitter?.emit("showQRCodeDialog", rom);
  }

  function addToCollection() {
    const rom = getRom();
    if (!rom) return;
    emitter?.emit("showAddToCollectionDialog", [rom]);
  }

  function refreshMetadata() {
    const rom = getRom();
    if (!rom) return;
    emitter?.emit("showRefreshMetadataDialog", rom);
  }

  function edit() {
    const rom = getRom();
    if (!rom) return;
    emitter?.emit("showEditRomDialog", rom);
  }

  function match() {
    const rom = getRom();
    if (!rom) return;
    emitter?.emit("showMatchRomDialog", rom);
  }

  function remove() {
    const rom = getRom();
    if (!rom) return;
    emitter?.emit("showDeleteRomDialog", [rom]);
  }

  return {
    isFavorited,
    canAddToCollection,
    play,
    download,
    favorite,
    share,
    shareQR,
    addToCollection,
    refreshMetadata,
    edit,
    match,
    remove,
  };
}
