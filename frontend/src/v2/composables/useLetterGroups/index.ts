// useLetterGroups — groups a flat ROM list into A-Z (+ "#") buckets and
// keeps a spy-scroll relationship between the grid and an AlphaStrip.
//
// Works in three gallery layouts:
//   * grid + grouped-by-letter  — jumps to the letter section anchor.
//   * grid + flat               — jumps to the first `[data-rom-id]` card.
//   * list                      — same fallback via row `data-rom-id`.
//
// The backend already ships `char_index` (letter → offset in the sorted
// list) and `rom_id_index` (ordered id list) on every `/api/roms` response;
// passing those through `options` makes the index authoritative across
// pagination. Without them, the composable derives letters from the loaded
// pages only.
//
// Usage:
//   const { scrollEl, letterGroups, availableLetters, currentLetter,
//           setLetterRef, scrollToLetter, onGridScroll } =
//     useLetterGroups(allRoms, { characterIndex, romIdIndex });
//
//   <div :ref="el => scrollEl = el" @scroll="onGridScroll"> … </div>
//   <AlphaStrip :available="availableLetters" :current="currentLetter"
//                @pick="scrollToLetter" />
import { computed, ref, type Ref } from "vue";
import type { SimpleRom } from "@/stores/roms";

export type LetterGroup = { letter: string; games: SimpleRom[] };

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#".split("");
const SCROLL_TOP_OFFSET = 16;
const SPY_TOP_OFFSET = 80;

function firstLetter(rom: SimpleRom): string {
  const title = rom.name || rom.fs_name_no_ext || "";
  const first = title.trim().charAt(0).toUpperCase();
  if (!first) return "#";
  return /[A-Z]/.test(first) ? first : "#";
}

// Backend ships lowercase letters (SQL func.lower) and raw digits for names
// that start with a number. Normalise to AlphaStrip's bucket shape: uppercase
// A–Z or "#".
function normalizeBackendLetter(raw: string): string {
  if (!raw) return "#";
  const c = raw.charAt(0).toUpperCase();
  return /[A-Z]/.test(c) ? c : "#";
}

interface Options {
  /** Backend letter→offset map (from `char_index` on the rom response). */
  characterIndex?: Ref<Record<string, number>>;
  /** Backend ordered rom-id list (from `rom_id_index`). */
  romIdIndex?: Ref<number[]>;
}

export function useLetterGroups(
  allRoms: Ref<SimpleRom[]>,
  options: Options = {},
) {
  const scrollEl = ref<HTMLElement | null>(null);
  const letterRefs = ref<Record<string, HTMLElement | null>>({});
  // Every letter whose section currently intersects the viewport. In grouped
  // mode this often contains 2+ letters when the first screen shows A, B, C…
  // together. `currentLetter` stays for backward compat; it holds the top-most
  // visible letter (used for the scroll-to-letter explicit highlight).
  const visibleLetters = ref<Set<string>>(new Set());
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

  // Union of backend letters (authoritative across pagination) and
  // loaded-page letters (resilient if the backend omits char_index). Keys
  // are always normalised to AlphaStrip's bucket shape.
  const availableLetters = computed(() => {
    const set = new Set<string>();
    const ci = options.characterIndex?.value;
    if (ci) {
      for (const k of Object.keys(ci)) set.add(normalizeBackendLetter(k));
    }
    for (const g of letterGroups.value) set.add(g.letter);
    return set;
  });

  // letter → id of the first ROM in that letter's bucket (server-sorted).
  // Backend entries are sorted by offset so "first" wins on collision —
  // e.g., names starting with 0–9 all collapse into "#", and we want the
  // earliest one to be the jump target.
  const firstRomIdByLetter = computed(() => {
    const map = new Map<string, number>();
    const ci = options.characterIndex?.value;
    const ri = options.romIdIndex?.value;
    if (ci && ri && ri.length) {
      const entries = Object.entries(ci).sort((a, b) => a[1] - b[1]);
      for (const [rawLetter, offset] of entries) {
        const letter = normalizeBackendLetter(rawLetter);
        if (map.has(letter)) continue;
        const id = ri[offset];
        if (id != null) map.set(letter, id);
      }
    }
    // Fill any gaps from the loaded pages (also covers the no-backend
    // case entirely).
    for (const r of allRoms.value) {
      const l = firstLetter(r);
      if (!map.has(l)) map.set(l, r.id);
    }
    return map;
  });

  function setLetterRef(letter: string, el: HTMLElement | null) {
    letterRefs.value[letter] = el;
  }

  function hasLetterSections(): boolean {
    for (const l in letterRefs.value) {
      if (letterRefs.value[l]) return true;
    }
    return false;
  }

  function scrollToLetter(letter: string) {
    const container = scrollEl.value;
    if (!container) return;

    // Grouped mode — use the letter section anchor for an exact align.
    const sectionEl = letterRefs.value[letter];
    if (sectionEl) {
      container.scrollTo({
        top: sectionEl.offsetTop - SCROLL_TOP_OFFSET,
        behavior: "smooth",
      });
      currentLetter.value = letter;
      return;
    }

    // Flat / list mode — resolve via the first ROM id of that letter.
    const romId = firstRomIdByLetter.value.get(letter);
    if (romId == null) return;
    const romEl = container.querySelector<HTMLElement>(
      `[data-rom-id="${romId}"]`,
    );
    if (!romEl) return;
    // getBoundingClientRect-based delta handles nested positioning (table
    // rows, grid cells) where `offsetTop` wouldn't be relative to the
    // scroll container.
    const cRect = container.getBoundingClientRect();
    const rRect = romEl.getBoundingClientRect();
    const delta =
      rRect.top - cRect.top + container.scrollTop - SCROLL_TOP_OFFSET;
    container.scrollTo({ top: delta, behavior: "smooth" });
    currentLetter.value = letter;
  }

  function setVisible(letters: Iterable<string>, top: string) {
    const next = new Set(letters);
    // Shallow diff — avoid reassigning when nothing changed so reactive
    // watchers don't churn on every scroll frame.
    const cur = visibleLetters.value;
    if (next.size !== cur.size || [...next].some((l) => !cur.has(l))) {
      visibleLetters.value = next;
    }
    if (top && top !== currentLetter.value) currentLetter.value = top;
  }

  function onGridScroll() {
    const container = scrollEl.value;
    if (!container) return;
    const viewTop = container.scrollTop + SPY_TOP_OFFSET;
    const viewBottom = container.scrollTop + container.clientHeight;

    // Grouped mode — section refs are the source of truth. A letter is
    // "visible" if any part of its section overlaps the visible band.
    if (hasLetterSections()) {
      const groups = letterGroups.value;
      const visible: string[] = [];
      let top = "";
      for (let i = 0; i < groups.length; i++) {
        const { letter } = groups[i];
        const node = letterRefs.value[letter];
        if (!node) continue;
        const sectionTop = node.offsetTop;
        const next = groups[i + 1];
        const nextNode = next ? letterRefs.value[next.letter] : null;
        const sectionBottom = nextNode
          ? nextNode.offsetTop
          : sectionTop + node.offsetHeight;
        if (sectionBottom > viewTop && sectionTop < viewBottom) {
          visible.push(letter);
          if (!top) top = letter;
        }
      }
      setVisible(visible, top);
      return;
    }

    // Flat / list mode — scan the ≤27 first-of-letter elements. A letter is
    // visible when its first ROM's row/card is within the viewport band (or
    // when it's the letter "above" the viewport — i.e. we're currently
    // inside its block).
    const cRect = container.getBoundingClientRect();
    const entries: Array<{ letter: string; top: number }> = [];
    for (const [letter, romId] of firstRomIdByLetter.value) {
      const el = container.querySelector<HTMLElement>(
        `[data-rom-id="${romId}"]`,
      );
      if (!el) continue;
      const elTop =
        el.getBoundingClientRect().top - cRect.top + container.scrollTop;
      entries.push({ letter, top: elTop });
    }
    entries.sort((a, b) => a.top - b.top);

    const visible: string[] = [];
    let top = "";
    for (let i = 0; i < entries.length; i++) {
      const { letter, top: sectionTop } = entries[i];
      const sectionBottom = entries[i + 1]?.top ?? Number.POSITIVE_INFINITY;
      if (sectionBottom > viewTop && sectionTop < viewBottom) {
        visible.push(letter);
        if (!top) top = letter;
      }
    }
    setVisible(visible, top);
  }

  return {
    scrollEl,
    letterGroups,
    availableLetters,
    firstRomIdByLetter,
    currentLetter,
    visibleLetters,
    setLetterRef,
    scrollToLetter,
    onGridScroll,
  };
}
