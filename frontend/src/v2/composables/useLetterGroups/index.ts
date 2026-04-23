// useLetterGroups — groups a flat ROM list into A-Z (+ "#") buckets and
// keeps a spy-scroll relationship between the grid and an AlphaStrip.
//
// Shared by Platform.vue and Collection.vue — both render the same
// alphabetical letter grid with a sidebar jump strip.
//
// Usage:
//   const { scrollEl, letterGroups, availableLetters, currentLetter,
//           setLetterRef, scrollToLetter, onGridScroll } =
//     useLetterGroups(allRoms);
//
//   <div :ref="el => scrollEl = el" @scroll="onGridScroll"> … </div>
//   <AlphaStrip :available="availableLetters" :current="currentLetter"
//                @pick="scrollToLetter" />
import { computed, ref, type Ref } from "vue";
import type { SimpleRom } from "@/stores/roms";

export type LetterGroup = { letter: string; games: SimpleRom[] };

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#".split("");

function firstLetter(rom: SimpleRom): string {
  const title = rom.name || rom.fs_name_no_ext || "";
  const first = title.trim().charAt(0).toUpperCase();
  if (!first) return "#";
  return /[A-Z]/.test(first) ? first : "#";
}

export function useLetterGroups(allRoms: Ref<SimpleRom[]>) {
  const scrollEl = ref<HTMLElement | null>(null);
  const letterRefs = ref<Record<string, HTMLElement | null>>({});
  const currentLetter = ref<string>("");

  const letterGroups = computed<LetterGroup[]>(() => {
    const map = new Map<string, SimpleRom[]>();
    for (const r of allRoms.value) {
      const l = firstLetter(r);
      if (!map.has(l)) map.set(l, []);
      map.get(l)!.push(r);
    }
    return ALPHABET.filter((l) => map.has(l)).map((letter) => ({
      letter,
      games: map.get(letter) ?? [],
    }));
  });

  const availableLetters = computed(
    () => new Set(letterGroups.value.map((g) => g.letter)),
  );

  function setLetterRef(letter: string, el: HTMLElement | null) {
    letterRefs.value[letter] = el;
  }

  function scrollToLetter(letter: string) {
    const el = letterRefs.value[letter];
    if (!el || !scrollEl.value) return;
    scrollEl.value.scrollTo({ top: el.offsetTop - 16, behavior: "smooth" });
    currentLetter.value = letter;
  }

  function onGridScroll() {
    const container = scrollEl.value;
    if (!container) return;
    const y = container.scrollTop + 80;
    let active = "";
    for (const { letter } of letterGroups.value) {
      const node = letterRefs.value[letter];
      if (node && node.offsetTop <= y) active = letter;
      else break;
    }
    if (active && active !== currentLetter.value) currentLetter.value = active;
  }

  return {
    scrollEl,
    letterGroups,
    availableLetters,
    currentLetter,
    setLetterRef,
    scrollToLetter,
    onGridScroll,
  };
}
