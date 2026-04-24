// useGridNav
//
// 2D arrow-key navigation for a vertical stack of horizontal card rows,
// as used on the Home dashboard (continue playing / recently added /
// favorites / platforms / collections) and anywhere else we compose
// `<CardRow>` stacks.
//
// Mechanics:
//   * Rows are discovered by `.card-row__track` descendants of the given
//     root element. That's the scroll track CardRow owns.
//   * Cells are the direct DOM children of each track.
//   * The focusable target for a cell is the cell itself if it matches a
//     focusable selector, otherwise the first focusable descendant.
//   * ArrowLeft / ArrowRight → prev / next cell in the current row.
//   * ArrowUp / ArrowDown → same column in the prev / next row (clamped).
//   * On autofocus we remember a "preferred column" and restore it when
//     moving up/down through rows of different lengths — common media-UI
//     pattern so row switching doesn't permanently lose horizontal place.
//
// Integration:
//   * Input modality flipping to `"pad"` (gamepad connected / pressed)
//     autofocuses the first cell, so `useGamepad`'s synthetic arrow keys
//     immediately land somewhere useful.
//   * `useGamepad` itself dispatches keydowns — so everything here is
//     plain keyboard code; gamepad users transparently benefit.
import { onBeforeUnmount, onMounted, watch, type Ref } from "vue";
import { useInputModality } from "@/v2/composables/useInputModality";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function useGridNav(rootRef: Ref<HTMLElement | null>) {
  const { modality } = useInputModality();
  let preferredCol = 0;

  function rows(): HTMLElement[] {
    if (!rootRef.value) return [];
    return Array.from(
      rootRef.value.querySelectorAll<HTMLElement>(".card-row__track"),
    );
  }

  function cells(row: HTMLElement): HTMLElement[] {
    return Array.from(row.children).filter(
      (c): c is HTMLElement => c instanceof HTMLElement,
    );
  }

  function focusableIn(el: HTMLElement): HTMLElement {
    if (el.matches(FOCUSABLE_SELECTOR)) return el;
    const inner = el.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
    return inner ?? el;
  }

  function current(): { rowIdx: number; colIdx: number } | null {
    const active = document.activeElement as HTMLElement | null;
    if (!active) return null;
    const rs = rows();
    for (let r = 0; r < rs.length; r++) {
      const row = rs[r];
      if (!row.contains(active) && active !== row) continue;
      const cs = cells(row);
      for (let c = 0; c < cs.length; c++) {
        if (cs[c].contains(active) || cs[c] === active) {
          return { rowIdx: r, colIdx: c };
        }
      }
    }
    return null;
  }

  function focusAt(
    rowIdx: number,
    colIdx: number,
    opts: { verticalJump?: boolean } = {},
  ) {
    const rs = rows();
    const row = rs[rowIdx];
    if (!row) return;
    const cs = cells(row);
    if (cs.length === 0) return;
    const clamped = Math.min(Math.max(colIdx, 0), cs.length - 1);
    const cell = cs[clamped];
    const target = focusableIn(cell);

    // Roving tabindex — only the current cell is a tab stop, every other
    // cell sets tabindex="-1". Lets the user land on the last focused
    // card via Tab from outside the grid, and keeps Shift+Tab escape
    // behaviour clean. Borrowed from the v1 console useRovingDom.
    const previous = rootRef.value?.querySelectorAll<HTMLElement>(
      "[data-grid-nav-cell]",
    );
    previous?.forEach((other) => {
      other.setAttribute("tabindex", "-1");
      other.removeAttribute("data-grid-nav-cell");
    });
    target.setAttribute("data-grid-nav-cell", "");
    target.setAttribute("tabindex", "0");

    target.focus({ preventScroll: true });

    // Jumping rows (up/down): centre the whole section vertically so the
    // focused row reads as the page's centrepiece rather than hugging the
    // top edge. Staying in the same row (left/right): horizontal-only
    // scroll inside the track, and `block: "nearest"` so we don't jitter
    // the page vertically while scrubbing across cards.
    if (opts.verticalJump) {
      const section = cell.closest(".card-row") ?? row;
      section.scrollIntoView({ block: "center", behavior: "smooth" });
    } else {
      target.scrollIntoView({
        block: "nearest",
        inline: "center",
        behavior: "smooth",
      });
    }
  }

  function focusFirst() {
    const rs = rows();
    for (let r = 0; r < rs.length; r++) {
      if (cells(rs[r]).length > 0) {
        preferredCol = 0;
        focusAt(r, 0, { verticalJump: true });
        return;
      }
    }
  }

  function onKey(e: KeyboardEvent) {
    if (
      e.key !== "ArrowLeft" &&
      e.key !== "ArrowRight" &&
      e.key !== "ArrowUp" &&
      e.key !== "ArrowDown"
    ) {
      return;
    }
    if (!rootRef.value) return;
    // Only steer when focus is already inside the grid — don't hijack
    // arrow keys meant for input fields, menus, or other widgets.
    const active = document.activeElement;
    if (!(active instanceof Node) || !rootRef.value.contains(active)) return;

    const cur = current();
    if (!cur) return;

    let { rowIdx, colIdx } = cur;
    const rs = rows();
    const rowCells = cells(rs[rowIdx]);
    let verticalJump = false;

    if (e.key === "ArrowLeft") {
      if (colIdx === 0) return;
      colIdx -= 1;
      preferredCol = colIdx;
    } else if (e.key === "ArrowRight") {
      if (colIdx === rowCells.length - 1) return;
      colIdx += 1;
      preferredCol = colIdx;
    } else if (e.key === "ArrowUp") {
      if (rowIdx === 0) return;
      rowIdx -= 1;
      colIdx = preferredCol;
      verticalJump = true;
    } else if (e.key === "ArrowDown") {
      if (rowIdx === rs.length - 1) return;
      rowIdx += 1;
      colIdx = preferredCol;
      verticalJump = true;
    }

    e.preventDefault();
    focusAt(rowIdx, colIdx, { verticalJump });
  }

  // Watches card rows for late-arriving children (data fetching finishes
  // after mount, skeletons swap to real cards). When the first cell shows
  // up — and the user is in pad modality without focus in the grid — we
  // land focus on it.
  let observer: MutationObserver | null = null;

  function maybeAutofocus() {
    if (modality.value !== "pad") return;
    if (!rootRef.value) return;
    if (rootRef.value.contains(document.activeElement)) return;
    focusFirst();
  }

  onMounted(() => {
    window.addEventListener("keydown", onKey);
    if (rootRef.value) {
      observer = new MutationObserver(() => maybeAutofocus());
      observer.observe(rootRef.value, { childList: true, subtree: true });
    }
    requestAnimationFrame(maybeAutofocus);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("keydown", onKey);
    observer?.disconnect();
    observer = null;
  });

  // Reactively autofocus when modality becomes "pad". Useful when the
  // user picks up a gamepad after loading the page with the mouse.
  watch(modality, (m) => {
    if (m === "pad") maybeAutofocus();
  });

  return { focusFirst, focusAt };
}
