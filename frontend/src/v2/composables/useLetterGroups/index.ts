// useLetterGroups — bucket a flat ROM list into A-Z (+ "#") groups.
//
// Pre-virtualisation this composable also handled scroll-spy and
// scroll-to-letter via DOM refs. Both responsibilities now live in the
// gallery views: scroll-spy via IntersectionObserver on `data-spy-letter`
// elements rendered inside the virtual scroller, and scroll-to-letter via
// `RVirtualScroller.scrollToIndex(letterToIndex.get(letter))` keyed off
// `useGalleryVirtualItems`.
import { computed, type Ref } from "vue";
import type { SimpleRom } from "@/stores/roms";
import { romBucketLetter } from "@/v2/utils/romLetter";

export type LetterGroup = { letter: string; games: SimpleRom[] };

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#".split("");

export function useLetterGroups(allRoms: Ref<SimpleRom[]>) {
  const letterGroups = computed<LetterGroup[]>(() => {
    const map = new Map<string, SimpleRom[]>();
    for (const r of allRoms.value) {
      const l = romBucketLetter(r);
      if (!map.has(l)) map.set(l, []);
      map.get(l)!.push(r);
    }
    return ALPHABET.filter((l) => map.has(l)).map((letter) => ({
      letter,
      games: map.get(letter) ?? [],
    }));
  });

  return { letterGroups };
}
