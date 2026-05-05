<script setup lang="ts">
// ScoreMenuBtn — score picker shared by the rating and difficulty
// controls on the game-details ribbon. Trigger reuses the same glass
// pill as GameActionBtn (visual coherence with the action row); the
// menu shows the RRating primitive + a Clear action.
//
// Generic: caller supplies the icon pair, accent color, label and
// max scale. No domain knowledge — feature composite because it's only
// consumed by the GameActions feature for now.
import { RIcon, RMenu, RMenuPanel, RRating } from "@v2/lib";
import { ref } from "vue";

defineOptions({ inheritAttrs: false });

interface Props {
  value: number;
  max?: number;
  label: string;
  iconFull: string;
  iconEmpty: string;
  accent: string;
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  max: 10,
  disabled: false,
});

const emit = defineEmits<{
  (e: "update:value", v: number): void;
}>();

const open = ref(false);

function pick(n: number) {
  emit("update:value", n);
  open.value = false;
}

function clear() {
  emit("update:value", 0);
  open.value = false;
}
</script>

<template>
  <RMenu v-model="open" :offset="[8, 0]" :close-on-content-click="false">
    <template #activator="{ props: activatorProps }">
      <button
        v-bind="activatorProps"
        type="button"
        class="r-v2-score-btn"
        :class="{ 'r-v2-score-btn--has-value': value > 0 }"
        :style="{ '--score-accent': `var(--r-color-${accent})` }"
        :disabled="disabled"
        :aria-label="`${label}: ${value > 0 ? value : 'unset'}`"
      >
        <RIcon :icon="value > 0 ? iconFull : iconEmpty" />
        <span class="r-v2-score-btn__value">
          {{ value > 0 ? value : "—" }}
        </span>
      </button>
    </template>

    <RMenuPanel width="auto" padding="10px">
      <div class="r-v2-score-menu">
        <div
          class="r-v2-score-menu__header"
          :style="{ '--score-accent': `var(--r-color-${accent})` }"
        >
          <RIcon :icon="value > 0 ? iconFull : iconEmpty" />
          <span class="r-v2-score-menu__label">{{ label }}</span>
          <span class="r-v2-score-menu__current">
            {{ value > 0 ? value : "—" }}
          </span>
        </div>

        <RRating
          :model-value="value"
          :length="max"
          :empty-icon="iconEmpty"
          :full-icon="iconFull"
          :color="accent"
          :active-color="accent"
          size="small"
          density="compact"
          hover
          ripple
          @update:model-value="pick"
        />

        <button
          type="button"
          class="r-v2-score-menu__clear"
          :disabled="value === 0"
          @click="clear"
        >
          <RIcon icon="mdi-close" size="14" />
          Clear {{ label.toLowerCase() }}
        </button>
      </div>
    </RMenuPanel>
  </RMenu>
</template>

<style scoped>
/* Trigger — parallels .r-v2-game-btn--surface so it sits in the
   action row without visual breaks. Translucent grey RTag-style
   surface, not the dark cover-overlay scrim. */
.r-v2-score-btn {
  appearance: none;
  border: 1px solid var(--r-color-border-strong);
  background: var(--r-color-surface);
  color: var(--r-color-fg-secondary);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  padding: 0 16px;
  border-radius: var(--r-radius-pill);
  cursor: pointer;
  font-family: inherit;
  font-weight: var(--r-font-weight-semibold);
  font-size: 14px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-score-btn :deep(.mdi) {
  font-size: 20px;
}
.r-v2-score-btn:hover:not(:disabled) {
  background: var(--r-color-surface-hover);
  color: var(--r-color-fg);
}
.r-v2-score-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.r-v2-score-btn--has-value {
  color: var(--score-accent);
}
.r-v2-score-btn--has-value:hover:not(:disabled) {
  color: var(--score-accent);
}
.r-v2-score-btn__value {
  font-variant-numeric: tabular-nums;
  min-width: 1ch;
  text-align: center;
}

/* Menu */
.r-v2-score-menu {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.r-v2-score-menu__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
  font-size: 13px;
  font-weight: var(--r-font-weight-semibold);
}
.r-v2-score-menu__header :deep(.mdi) {
  font-size: 16px;
  color: var(--score-accent);
}
.r-v2-score-menu__label {
  flex: 1;
  color: var(--r-color-fg);
}
.r-v2-score-menu__current {
  color: var(--r-color-fg-secondary);
  font-variant-numeric: tabular-nums;
}

.r-v2-score-menu__clear {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--r-color-fg-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px;
  border-radius: var(--r-radius-sm);
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  font-weight: var(--r-font-weight-medium);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-score-menu__clear:hover:not(:disabled) {
  background: var(--r-color-surface);
  color: var(--r-color-fg);
}
.r-v2-score-menu__clear:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
