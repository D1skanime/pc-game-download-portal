// useInputModality
//
// Tracks the user's last-used input device and exposes it as a reactive ref.
// Writes `data-input` on <html> so CSS can adapt focus rings, hit targets,
// and hint visibility per modality. A single shared instance is enough —
// install() from the root layout mounts listeners once.
import { onBeforeUnmount, readonly, ref } from "vue";

export type InputModality = "mouse" | "touch" | "key" | "pad";

const modality = ref<InputModality>("mouse");
let installed = false;

function applyAttribute(next: InputModality) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.input = next;
}

function setModality(next: InputModality) {
  if (modality.value === next) return;
  modality.value = next;
  applyAttribute(next);
}

export function useInputModality() {
  function install() {
    if (installed) return;
    installed = true;

    applyAttribute(modality.value);

    const onMouse = () => setModality("mouse");
    const onTouch = () => setModality("touch");
    const onKey = (e: KeyboardEvent) => {
      // Ignore modifier-only presses and clicks that happen to be keyboard-
      // triggered — what we care about is real navigational keys.
      if (
        e.key === "Tab" ||
        e.key.startsWith("Arrow") ||
        e.key === "Enter" ||
        e.key === " " ||
        e.key === "Escape"
      ) {
        setModality("key");
      }
    };
    // A gamepad connection is a strong signal the user is on a pad. Real
    // per-button detection happens when we port the console input bus; until
    // then we flip to "pad" on connect and stay there until another input
    // type takes over.
    const onGamepad = () => setModality("pad");

    window.addEventListener("mousemove", onMouse, { passive: true });
    window.addEventListener("mousedown", onMouse, { passive: true });
    window.addEventListener("wheel", onMouse, { passive: true });
    window.addEventListener("touchstart", onTouch, { passive: true });
    window.addEventListener("keydown", onKey);
    window.addEventListener("gamepadconnected", onGamepad);

    onBeforeUnmount(() => {
      window.removeEventListener("mousemove", onMouse);
      window.removeEventListener("mousedown", onMouse);
      window.removeEventListener("wheel", onMouse);
      window.removeEventListener("touchstart", onTouch);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("gamepadconnected", onGamepad);
      installed = false;
    });
  }

  return {
    modality: readonly(modality),
    install,
    setModality,
  };
}
