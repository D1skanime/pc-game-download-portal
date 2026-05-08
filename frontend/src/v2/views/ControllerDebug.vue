<script setup lang="ts">
// ControllerDebug — live inspector for gamepad input + modality tracking.
//
// Polls `navigator.getGamepads()` each frame (matches `useGamepad`'s cadence)
// and displays:
//   * every connected pad's id / index / mapping
//   * per-button pressed state + analog value
//   * left and right stick axis values with a deadzone ring visualisation
//   * live `html[data-input]` modality attribute
//   * a scrolling log of synthetic keydown events we emit app-wide
//
// Handy for:
//   - verifying the gamepad is connected in the expected slot
//   - checking button numbering against Standard Gamepad mapping
//   - confirming the synthetic-key bridge from `useGamepad` actually fires
//
// Polling is independent of `useGamepad` — this view is its own read path;
// the real input loop keeps running in the background.
import { RBtn, RIcon } from "@v2/lib";
import { onBeforeUnmount, onMounted, ref } from "vue";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";
import { useInputModality } from "@/v2/composables/useInputModality";

defineOptions({ inheritAttrs: false });

const { modality } = useInputModality();

// Standard Gamepad button labels matching the W3C Gamepad API numbering.
const BUTTON_LABELS: Record<number, string> = {
  0: "A / ✕",
  1: "B / ○",
  2: "X / □",
  3: "Y / △",
  4: "LB / L1",
  5: "RB / R1",
  6: "LT / L2",
  7: "RT / R2",
  8: "Back / Share",
  9: "Start / Options",
  10: "L-stick click",
  11: "R-stick click",
  12: "D-pad Up",
  13: "D-pad Down",
  14: "D-pad Left",
  15: "D-pad Right",
  16: "Home / PS",
};

// useGamepad's mapping legend — keep in sync with the composable.
const KEYBIND_LEGEND: { button: string; key: string }[] = [
  { button: "D-pad Up", key: "ArrowUp" },
  { button: "D-pad Down", key: "ArrowDown" },
  { button: "D-pad Left", key: "ArrowLeft" },
  { button: "D-pad Right", key: "ArrowRight" },
  { button: "Left stick", key: "Arrow{Up,Down,Left,Right}" },
  { button: "A / ✕", key: "activate focused (click)" },
  { button: "B / ○", key: "back (or close open modal)" },
  { button: "Back / Share", key: "back (or close open modal)" },
  { button: "Start / Options", key: "open user menu" },
  { button: "LB / L1", key: "← prev AppNav section" },
  { button: "RB / R1", key: "→ next AppNav section" },
];

type GamepadSnapshot = {
  key: string;
  index: number;
  id: string;
  mapping: string;
  connected: boolean;
  buttons: { pressed: boolean; value: number }[];
  axes: number[];
};

const pads = ref<GamepadSnapshot[]>([]);
const rafId = ref<number>(0);

// Keyboard-event feed — tracks every key dispatch so we can see the
// gamepad→keyboard bridge firing in real time. Keydown only, capped list.
type LogEntry = {
  id: number;
  at: number;
  key: string;
  from: "real" | "synthetic";
};
const keyLog = ref<LogEntry[]>([]);
const LOG_CAP = 30;
let logCounter = 1;

function tick() {
  const list = navigator.getGamepads?.() ?? [];
  pads.value = list
    .filter((p): p is Gamepad => !!p)
    .map((p) => ({
      key: `${p.index}:${p.id}`,
      index: p.index,
      id: p.id,
      mapping: p.mapping || "—",
      connected: p.connected,
      buttons: p.buttons.map((b) => ({ pressed: b.pressed, value: b.value })),
      axes: [...p.axes],
    }));
  rafId.value = requestAnimationFrame(tick);
}

function onKeydown(e: KeyboardEvent) {
  // `isTrusted` is false for KeyboardEvents constructed via `new` and
  // `dispatchEvent` — which is how `useGamepad` fires synthetic keys.
  const from: LogEntry["from"] = e.isTrusted ? "real" : "synthetic";
  keyLog.value = [
    { id: logCounter++, at: Date.now(), key: e.key, from },
    ...keyLog.value,
  ].slice(0, LOG_CAP);
}

function clearLog() {
  keyLog.value = [];
}

onMounted(() => {
  tick();
  window.addEventListener("keydown", onKeydown);
});
onBeforeUnmount(() => {
  cancelAnimationFrame(rafId.value);
  window.removeEventListener("keydown", onKeydown);
});

function formatTime(t: number) {
  const d = new Date(t);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}.${d.getMilliseconds().toString().padStart(3, "0")}`;
}

function magnitude(x: number, y: number) {
  return Math.min(1, Math.sqrt(x * x + y * y));
}
</script>

<template>
  <SettingsShell
    title="Controller debug"
    subtitle="Live view of connected gamepads, input modality, and the synthetic key bridge driven by useGamepad."
    eyebrow="Developer tools"
    icon="mdi-bug-outline"
    bare
  >
    <!-- Modality status pill — shown above the panels since the toolbar
         row is owned by SettingsShell now. -->
    <div class="r-v2-ctrl__modality">
      <span class="r-v2-ctrl__modality-label">Modality</span>
      <span
        class="r-v2-ctrl__modality-pill"
        :class="`r-v2-ctrl__modality-pill--${modality}`"
      >
        <RIcon
          :icon="
            modality === 'pad'
              ? 'mdi-controller'
              : modality === 'key'
                ? 'mdi-keyboard-outline'
                : modality === 'touch'
                  ? 'mdi-gesture-tap'
                  : 'mdi-mouse-outline'
          "
          size="14"
        />
        {{ modality }}
      </span>
    </div>

    <!-- No pad — help state -->
    <div v-if="pads.length === 0" class="r-v2-ctrl__panel r-v2-ctrl__empty">
      <RIcon icon="mdi-controller-off" size="40" />
      <p>No gamepads detected.</p>
      <p class="r-v2-ctrl__hint">
        Press any button on your controller to wake it up. On Linux some pads
        require <code>evtest</code> / <code>joydev</code> permissions.
      </p>
    </div>

    <!-- One panel per connected pad -->
    <div
      v-for="pad in pads"
      :key="pad.key"
      class="r-v2-ctrl__panel r-v2-ctrl__pad"
    >
      <header class="r-v2-ctrl__pad-head">
        <div>
          <p class="r-v2-ctrl__pad-id" :title="pad.id">
            <RIcon icon="mdi-controller" size="14" />
            {{ pad.id }}
          </p>
          <p class="r-v2-ctrl__pad-meta">
            Slot {{ pad.index }} · mapping
            <span class="r-v2-ctrl__tag">{{ pad.mapping }}</span>
            ·
            <span :class="pad.connected ? 'r-v2-ctrl__ok' : 'r-v2-ctrl__bad'">
              {{ pad.connected ? "connected" : "disconnected" }}
            </span>
          </p>
        </div>
      </header>

      <div class="r-v2-ctrl__pad-body">
        <!-- Sticks -->
        <div class="r-v2-ctrl__sticks">
          <div
            v-for="stickIdx in [0, 2]"
            :key="stickIdx"
            class="r-v2-ctrl__stick"
          >
            <div class="r-v2-ctrl__stick-ring">
              <div class="r-v2-ctrl__stick-deadzone" />
              <div
                class="r-v2-ctrl__stick-dot"
                :style="{
                  left: `${50 + (pad.axes[stickIdx] ?? 0) * 50}%`,
                  top: `${50 + (pad.axes[stickIdx + 1] ?? 0) * 50}%`,
                  opacity:
                    magnitude(
                      pad.axes[stickIdx] ?? 0,
                      pad.axes[stickIdx + 1] ?? 0,
                    ) > 0.05
                      ? 1
                      : 0.4,
                }"
              />
            </div>
            <p class="r-v2-ctrl__stick-label">
              {{ stickIdx === 0 ? "Left stick" : "Right stick" }}
            </p>
            <p class="r-v2-ctrl__stick-values">
              X {{ (pad.axes[stickIdx] ?? 0).toFixed(2) }} · Y
              {{ (pad.axes[stickIdx + 1] ?? 0).toFixed(2) }}
            </p>
          </div>
        </div>

        <!-- Buttons grid -->
        <div class="r-v2-ctrl__buttons">
          <div
            v-for="(btn, i) in pad.buttons"
            :key="i"
            class="r-v2-ctrl__btn"
            :class="{ 'r-v2-ctrl__btn--pressed': btn.pressed }"
          >
            <span class="r-v2-ctrl__btn-idx">#{{ i }}</span>
            <span class="r-v2-ctrl__btn-label">
              {{ BUTTON_LABELS[i] ?? "—" }}
            </span>
            <span class="r-v2-ctrl__btn-value">
              {{ btn.value.toFixed(2) }}
            </span>
            <div
              class="r-v2-ctrl__btn-fill"
              :style="{ transform: `scaleX(${btn.value})` }"
            />
          </div>
        </div>

        <!-- Raw axes fallback (if >4 axes present) -->
        <div v-if="pad.axes.length > 4" class="r-v2-ctrl__axes">
          <p class="r-v2-ctrl__axes-title">All axes</p>
          <div v-for="(value, i) in pad.axes" :key="i" class="r-v2-ctrl__axis">
            <span class="r-v2-ctrl__axis-idx">Axis {{ i }}</span>
            <div class="r-v2-ctrl__axis-track">
              <div
                class="r-v2-ctrl__axis-fill"
                :style="{
                  left: `${50 - Math.abs(value) * 50 * (value < 0 ? 1 : 0)}%`,
                  width: `${Math.abs(value) * 50}%`,
                }"
              />
            </div>
            <span class="r-v2-ctrl__axis-value">
              {{ value.toFixed(3) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Mapping legend -->
    <div class="r-v2-ctrl__panel r-v2-ctrl__legend">
      <header class="r-v2-ctrl__section-head">
        <RIcon icon="mdi-swap-horizontal" size="16" />
        <h2>Gamepad → keyboard mapping</h2>
      </header>
      <div class="r-v2-ctrl__legend-grid">
        <div
          v-for="bind in KEYBIND_LEGEND"
          :key="bind.button"
          class="r-v2-ctrl__legend-row"
        >
          <span>{{ bind.button }}</span>
          <RIcon icon="mdi-arrow-right-thin" size="12" />
          <code>{{ bind.key }}</code>
        </div>
      </div>
    </div>

    <!-- Keydown log -->
    <div class="r-v2-ctrl__panel r-v2-ctrl__log">
      <header class="r-v2-ctrl__section-head">
        <RIcon icon="mdi-console-line" size="16" />
        <h2>Keyboard event feed</h2>
        <RBtn
          size="small"
          variant="text"
          prepend-icon="mdi-delete-outline"
          @click="clearLog"
        >
          Clear
        </RBtn>
      </header>
      <p class="r-v2-ctrl__log-hint">
        <strong>synthetic</strong> = dispatched by <code>useGamepad</code>.
        <strong>real</strong> = physical keyboard.
      </p>
      <ul v-if="keyLog.length" class="r-v2-ctrl__log-list">
        <li
          v-for="entry in keyLog"
          :key="entry.id"
          class="r-v2-ctrl__log-row"
          :class="`r-v2-ctrl__log-row--${entry.from}`"
        >
          <span class="r-v2-ctrl__log-time">{{ formatTime(entry.at) }}</span>
          <span class="r-v2-ctrl__log-tag">{{ entry.from }}</span>
          <code class="r-v2-ctrl__log-key">{{ entry.key }}</code>
        </li>
      </ul>
      <div v-else class="r-v2-ctrl__log-empty">
        Press any key or gamepad button to see events here.
      </div>
    </div>
  </SettingsShell>
</template>

<style scoped>
.r-v2-ctrl__modality {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
}
.r-v2-ctrl__modality-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--r-color-fg-muted);
}
.r-v2-ctrl__modality-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--r-radius-pill);
  font-size: 12px;
  font-weight: var(--r-font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: color-mix(in srgb, var(--r-color-brand-primary) 14%, transparent);
  color: var(--r-color-brand-primary);
  border: 1px solid
    color-mix(in srgb, var(--r-color-brand-primary) 30%, transparent);
}
.r-v2-ctrl__modality-pill--pad {
  background: color-mix(
    in srgb,
    var(--r-color-status-base-success) 14%,
    transparent
  );
  color: var(--r-color-success);
  border-color: color-mix(
    in srgb,
    var(--r-color-status-base-success) 30%,
    transparent
  );
}

.r-v2-ctrl__panel {
  background: color-mix(
    in srgb,
    var(--r-color-canvas-bg-deep) 70%,
    transparent
  );
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  padding: 16px;
}

.r-v2-ctrl__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 48px 16px;
  color: var(--r-color-fg-muted);
  text-align: center;
}
.r-v2-ctrl__empty :deep(.r-icon) {
  color: var(--r-color-fg-faint);
}
.r-v2-ctrl__empty p {
  margin: 0;
  font-size: 13px;
}
.r-v2-ctrl__hint {
  max-width: 420px;
  color: var(--r-color-fg-muted);
  font-size: 12px;
}
.r-v2-ctrl__hint code {
  padding: 1px 4px;
  background: var(--r-color-surface);
  border-radius: 3px;
  font-family: var(--r-font-family-mono, monospace);
  font-size: 11px;
}

.r-v2-ctrl__pad-head {
  padding-bottom: 12px;
  border-bottom: 1px solid None;
  margin-bottom: 14px;
}
.r-v2-ctrl__pad-id {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 13px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.r-v2-ctrl__pad-meta {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--r-color-fg-muted);
}
.r-v2-ctrl__tag {
  padding: 1px 6px;
  background: var(--r-color-surface);
  border-radius: var(--r-radius-sm);
  font-family: var(--r-font-family-mono, monospace);
  font-size: 10px;
  color: var(--r-color-fg-secondary);
}
.r-v2-ctrl__ok {
  color: var(--r-color-success);
}
.r-v2-ctrl__bad {
  color: var(--r-color-danger-fg);
}

.r-v2-ctrl__pad-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 20px;
  align-items: start;
}

.r-v2-ctrl__sticks {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: center;
}
.r-v2-ctrl__stick {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.r-v2-ctrl__stick-ring {
  position: relative;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
}
.r-v2-ctrl__stick-deadzone {
  position: absolute;
  inset: 35%;
  border-radius: 50%;
  border: 1px dashed var(--r-color-border-strong);
}
.r-v2-ctrl__stick-dot {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--r-color-brand-primary);
  box-shadow: 0 0 12px
    color-mix(in srgb, var(--r-color-brand-primary) 60%, transparent);
  transform: translate(-50%, -50%);
  transition: opacity var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-ctrl__stick-label {
  margin: 6px 0 0;
  font-size: 11px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg-secondary);
}
.r-v2-ctrl__stick-values {
  margin: 0;
  font-size: 10px;
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-fg-muted);
}

.r-v2-ctrl__buttons {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 6px;
  align-self: start;
}
.r-v2-ctrl__btn {
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-sm);
  font-size: 11px;
  overflow: hidden;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-ctrl__btn--pressed {
  background: color-mix(in srgb, var(--r-color-brand-primary) 16%, transparent);
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 50%,
    transparent
  );
}
.r-v2-ctrl__btn-fill {
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--r-color-brand-primary) 12%, transparent);
  transform-origin: left center;
  transform: scaleX(0);
  transition: transform 40ms linear;
  pointer-events: none;
  z-index: 0;
}
.r-v2-ctrl__btn-idx,
.r-v2-ctrl__btn-label,
.r-v2-ctrl__btn-value {
  position: relative;
  z-index: 1;
}
.r-v2-ctrl__btn-idx {
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-fg-faint);
  font-size: 10px;
}
.r-v2-ctrl__btn-label {
  color: var(--r-color-fg);
  font-weight: var(--r-font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.r-v2-ctrl__btn-value {
  font-family: var(--r-font-family-mono, monospace);
  font-size: 10px;
  color: var(--r-color-fg-muted);
}

.r-v2-ctrl__axes {
  grid-column: 1 / -1;
  padding-top: 12px;
  margin-top: 6px;
  border-top: 1px solid None;
}
.r-v2-ctrl__axes-title {
  margin: 0 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--r-color-fg-muted);
}
.r-v2-ctrl__axis {
  display: grid;
  grid-template-columns: 60px 1fr 60px;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  font-size: 11px;
}
.r-v2-ctrl__axis-idx {
  color: var(--r-color-fg-muted);
}
.r-v2-ctrl__axis-track {
  position: relative;
  height: 4px;
  background: var(--r-color-surface);
  border-radius: 2px;
}
.r-v2-ctrl__axis-track::after {
  content: "";
  position: absolute;
  left: 50%;
  top: -2px;
  bottom: -2px;
  width: 1px;
  background: var(--r-color-surface-hover);
}
.r-v2-ctrl__axis-fill {
  position: absolute;
  top: 0;
  bottom: 0;
  background: var(--r-color-brand-primary);
  border-radius: 2px;
}
.r-v2-ctrl__axis-value {
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-fg-secondary);
  text-align: right;
}

.r-v2-ctrl__section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--r-color-fg);
  margin-bottom: 12px;
}
.r-v2-ctrl__section-head h2 {
  margin: 0;
  font-size: 12px;
  font-weight: var(--r-font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex: 1;
}

.r-v2-ctrl__legend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 6px;
}
.r-v2-ctrl__legend-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 8px;
  align-items: center;
  padding: 6px 10px;
  background: var(--r-color-bg-elevated);
  border-radius: var(--r-radius-sm);
  font-size: 12px;
}
.r-v2-ctrl__legend-row span {
  color: var(--r-color-fg);
}
.r-v2-ctrl__legend-row code {
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-brand-primary);
  font-size: 11px;
  text-align: right;
}
.r-v2-ctrl__legend-row :deep(.r-icon) {
  color: var(--r-color-fg-muted);
}

.r-v2-ctrl__log-hint {
  margin: 0 0 10px;
  font-size: 11px;
  color: var(--r-color-fg-muted);
}
.r-v2-ctrl__log-hint code {
  padding: 1px 4px;
  background: var(--r-color-surface);
  border-radius: 3px;
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-fg-secondary);
}
.r-v2-ctrl__log-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 240px;
  overflow-y: auto;
}
.r-v2-ctrl__log-row {
  display: grid;
  grid-template-columns: 100px 70px 1fr;
  gap: 10px;
  align-items: center;
  padding: 4px 10px;
  background: var(--r-color-bg-elevated);
  border-radius: var(--r-radius-sm);
  font-size: 11px;
}
.r-v2-ctrl__log-row--synthetic {
  background: color-mix(in srgb, var(--r-color-brand-primary) 10%, transparent);
}
.r-v2-ctrl__log-time {
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-fg-muted);
}
.r-v2-ctrl__log-tag {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg-muted);
}
.r-v2-ctrl__log-row--synthetic .r-v2-ctrl__log-tag {
  color: var(--r-color-brand-primary);
}
.r-v2-ctrl__log-key {
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-fg);
}
.r-v2-ctrl__log-empty {
  padding: 24px;
  text-align: center;
  color: var(--r-color-fg-muted);
  font-size: 12px;
}

@media (max-width: 720px) {
  .r-v2-ctrl__pad-body {
    grid-template-columns: 1fr;
  }
  .r-v2-ctrl__sticks {
    flex-direction: row;
    justify-content: center;
  }
}
</style>
