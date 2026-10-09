// useReducedMotion — the single "reduce motion / effects" control.
//
// Uses a per-device user override for one reactive enabled boolean, plus a toggle().
// Animations are enabled by default, and an explicit user choice wins from then on.
//
// It drives everything motion- and GPU-effect-related: the `r-v2-reduced-motion`
// root class (background blur + the global animation/transition neutralize in
// global.css, cover blur-up in GameCover), plus the JS-driven motion gates that
// CSS can't reach (the cover CD-spin in useCoverAnimation, view-transition
// morphs, RExpandTransition, RBox3D's idle drift). One hook, one Settings
// toggle, one source of truth.
//
// Per-device (localStorage, not backend-synced): whether motion/effects are
// too heavy depends on the machine RomM is viewed on, not the account. Same
// singleton rationale as useBreakpoint: every consumer shares the reactive refs.
import { useLocalStorage } from "@vueuse/core";
import { computed, type ComputedRef } from "vue";

// false keeps animations enabled for first-time users. The explicit serializer
// prevents persisted booleans from being read back as strings.
const override = useLocalStorage<boolean>("settings.v2.reducedMotion", false, {
  serializer: {
    read: (v) => v === "true",
    write: (v) => String(v),
  },
});

const enabled = computed<boolean>({
  get: () => override.value,
  set: (value) => {
    override.value = value;
  },
});

export function useReducedMotion(): {
  enabled: ComputedRef<boolean>;
  toggle: () => boolean;
} {
  /** Flip reduced-motion mode and return the new state (true = now on).
   * Writing through `enabled` records an explicit override. */
  function toggle(): boolean {
    enabled.value = !enabled.value;
    return enabled.value;
  }

  return { enabled: enabled as ComputedRef<boolean>, toggle };
}
