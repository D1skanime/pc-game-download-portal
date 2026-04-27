// useViewTransition — tiny wrapper around the browser View Transitions API
// for shared-element morphs (e.g. game card cover → GameDetails cover).
//
// Usage at the source side (the element you click):
//
//   const { morphTransition } = useViewTransition();
//   function onClick(e: MouseEvent) {
//     e.preventDefault();
//     if (!coverEl.value) return router.push(href);
//     morphTransition(
//       { el: coverEl.value, name: `rom-cover-${rom.id}` },
//       () => router.push(href),
//     );
//   }
//
// At the destination side, just paint a static `view-transition-name` on
// the matching element — the browser pairs it with the source by name.
// One element per name on screen at a time; we tag the source imperatively
// so two visible cards with the same ROM never collide.
//
// Graceful degradation:
//   * `prefers-reduced-motion: reduce` → no transition, just navigate.
//   * Browser without `document.startViewTransition` → just navigate.

export interface MorphSource {
  el: HTMLElement;
  name: string;
}

function isSupported(): boolean {
  return (
    typeof document !== "undefined" &&
    typeof document.startViewTransition === "function"
  );
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function useViewTransition() {
  function morphTransition(
    source: MorphSource,
    navigate: () => void | Promise<void>,
  ): void {
    if (!isSupported() || prefersReducedMotion()) {
      void navigate();
      return;
    }

    // Tag the source element so the browser captures it as a separate
    // transition layer. The destination element carries the same name in
    // its template, so the snapshots get paired automatically.
    source.el.style.viewTransitionName = source.name;

    const transition = document.startViewTransition(async () => {
      await navigate();
    });

    // Clean up the inline style after the transition finishes — the
    // source element usually unmounts during navigate(), but if a route
    // keeps it alive (kept-alive view, error mid-nav, …) we don't want a
    // dangling view-transition-name on the page.
    transition.finished.finally(() => {
      if (source.el.isConnected) {
        source.el.style.viewTransitionName = "";
      }
    });
  }

  return { morphTransition, isSupported };
}
