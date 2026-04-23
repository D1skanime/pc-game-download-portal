// useGamepad
//
// Universal gamepad support. Translates D-pad / left-stick / face-button
// presses into synthetic KeyboardEvents so the normal DOM focus model and
// Vue click handlers work out of the box on a controller — no bespoke
// spatial-nav engine required.
//
// Mapping (Standard Gamepad):
//   D-pad up / down / left / right → Arrow{Up,Down,Left,Right}
//   Left stick (above threshold)   → Arrow* (with initial delay + repeat)
//   A button (0)                   → Enter
//   B button (1)                   → Escape
//   Start (9)                      → "/" (focus search, per convention)
//   Back / Select (8)              → Escape
//
// Repeat cadence matches the v1 console input: 350ms initial delay, then
// 120ms per repeat. That's slow enough for deliberate navigation, fast
// enough to scrub through long lists.
//
// Dispatch target: `document.activeElement || document.body`. For arrow
// keys we additionally push Tab/Shift-Tab equivalents so native focus
// movement works on sites that don't implement arrow navigation — we
// prioritise arrows because most RomM lists / grids handle them via
// browser-default behaviour (e.g. focused <button>s) or via custom Vue
// handlers. When a view wants true grid spatial nav it adds its own
// keydown handler; this composable just gives a gamepad the same reach
// as a keyboard.
import { onBeforeUnmount } from "vue";
import { useInputModality } from "@/v2/composables/useInputModality";

const INITIAL_DELAY_MS = 350;
const REPEAT_MS = 120;
const AXIS_THRESHOLD = 0.5;

type Binding = { key: string; code?: string };

// Standard gamepad button index → synthetic keyboard event.
const BUTTON_MAP: Record<number, Binding | undefined> = {
  0: { key: "Enter", code: "Enter" }, // A / Cross
  1: { key: "Escape", code: "Escape" }, // B / Circle
  8: { key: "Escape", code: "Escape" }, // Back / Share
  9: { key: "/", code: "Slash" }, // Start / Options — focus search
  12: { key: "ArrowUp", code: "ArrowUp" },
  13: { key: "ArrowDown", code: "ArrowDown" },
  14: { key: "ArrowLeft", code: "ArrowLeft" },
  15: { key: "ArrowRight", code: "ArrowRight" },
};

function dispatchKey(binding: Binding) {
  const target =
    (document.activeElement as HTMLElement | null) ?? document.body;
  const init: KeyboardEventInit = {
    key: binding.key,
    code: binding.code,
    bubbles: true,
    cancelable: true,
  };
  target.dispatchEvent(new KeyboardEvent("keydown", init));
  target.dispatchEvent(new KeyboardEvent("keyup", init));
}

type ButtonState = { pressed: boolean; nextRepeatAt: number };
type PadState = {
  buttons: Record<number, ButtonState>;
  axisNextAt: { x: number; y: number };
};

let installed = false;

export function useGamepad() {
  function install() {
    if (installed) return;
    if (typeof navigator === "undefined" || !navigator.getGamepads) return;
    installed = true;

    const states: Record<string, PadState> = {};
    const { setModality } = useInputModality();
    let rafId = 0;

    const onAnyInput = () => setModality("pad");
    const onConnect = () => setModality("pad");
    window.addEventListener("gamepadconnected", onConnect);

    const loop = () => {
      const pads = navigator.getGamepads?.() ?? [];
      const t = performance.now();

      for (const pad of pads) {
        if (!pad) continue;
        const key = `${pad.index}:${pad.id}`;
        const st = (states[key] ||= {
          buttons: {},
          axisNextAt: { x: 0, y: 0 },
        });

        // Left stick → ArrowKey equivalents.
        const x = pad.axes[0] ?? 0;
        const y = pad.axes[1] ?? 0;
        tickAxis(st, "x", x, t, (dir) =>
          dispatchKey(
            dir < 0
              ? { key: "ArrowLeft", code: "ArrowLeft" }
              : { key: "ArrowRight", code: "ArrowRight" },
          ),
        );
        tickAxis(st, "y", y, t, (dir) =>
          dispatchKey(
            dir < 0
              ? { key: "ArrowUp", code: "ArrowUp" }
              : { key: "ArrowDown", code: "ArrowDown" },
          ),
        );

        // Buttons.
        for (let i = 0; i < pad.buttons.length; i++) {
          const button = pad.buttons[i];
          const binding = BUTTON_MAP[i];
          if (!binding) continue;
          const prev = (st.buttons[i] ||= { pressed: false, nextRepeatAt: 0 });
          if (button.pressed) {
            if (!prev.pressed) {
              dispatchKey(binding);
              onAnyInput();
              prev.pressed = true;
              prev.nextRepeatAt = t + INITIAL_DELAY_MS;
            } else if (t >= prev.nextRepeatAt) {
              dispatchKey(binding);
              prev.nextRepeatAt = t + REPEAT_MS;
            }
          } else {
            prev.pressed = false;
            prev.nextRepeatAt = 0;
          }
        }
      }

      rafId = requestAnimationFrame(loop);
    };

    rafId = requestAnimationFrame(loop);

    onBeforeUnmount(() => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("gamepadconnected", onConnect);
      installed = false;
    });
  }

  return { install };
}

function tickAxis(
  st: PadState,
  axis: "x" | "y",
  value: number,
  now: number,
  fire: (direction: -1 | 1) => void,
) {
  if (Math.abs(value) < AXIS_THRESHOLD) {
    st.axisNextAt[axis] = 0;
    return;
  }
  const dir = value < 0 ? -1 : 1;
  if (st.axisNextAt[axis] === 0) {
    fire(dir);
    st.axisNextAt[axis] = now + INITIAL_DELAY_MS;
  } else if (now >= st.axisNextAt[axis]) {
    fire(dir);
    st.axisNextAt[axis] = now + REPEAT_MS;
  }
}
