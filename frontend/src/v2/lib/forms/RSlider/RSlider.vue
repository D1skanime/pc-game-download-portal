<script setup lang="ts">
// RSlider — v2-styled wrapper around v-slider.
//
// Adds an integrated value badge with positionable layouts:
//   - 'none'   default; consumer renders the value externally (or hides it)
//   - 'right'  pill to the right of the track
//   - 'left'   pill to the left
//   - 'thumb'  floating pill above the thumb (follows drag)
//
// `#value` slot receives `{ value, percent }` so consumers can render
// custom content (icons, formatted numbers, units, …). Default content
// is `${value}${valueSuffix}`.
import { computed } from "vue";
import { VSlider } from "vuetify/components/VSlider";

defineOptions({ inheritAttrs: false });

interface Props {
  modelValue?: number;
  min?: number;
  max?: number;
  step?: number;
  color?: string;
  trackColor?: string;
  thumbColor?: string;
  size?:
    | "x-small"
    | "small"
    | "default"
    | "large"
    | "x-large"
    | string
    | number;
  density?: "default" | "comfortable" | "compact";
  hideDetails?: boolean | "auto";
  disabled?: boolean;
  readonly?: boolean;
  valuePosition?: "none" | "left" | "right" | "thumb";
  valueSuffix?: string;
  showTicks?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: 0,
  min: 0,
  max: 100,
  step: 1,
  color: "primary",
  trackColor: undefined,
  thumbColor: undefined,
  size: "default",
  density: "default",
  hideDetails: true,
  valuePosition: "none",
  valueSuffix: "",
  showTicks: false,
});

defineEmits<{
  (e: "update:modelValue", value: number): void;
}>();

// Slots:
//   #value="{ value, percent }"        custom value badge content (numbers default)
//   #prepend, #append, #tick-label     forwarded to v-slider unchanged

const percent = computed(() => {
  const range = props.max - props.min || 1;
  return Math.max(
    0,
    Math.min(100, ((props.modelValue - props.min) / range) * 100),
  );
});

const formatted = computed(() => `${props.modelValue}${props.valueSuffix}`);

const showThumbLabel = computed(() => props.valuePosition === "thumb");
</script>

<template>
  <div
    class="r-slider"
    :class="[
      `r-slider--pos-${valuePosition}`,
      { 'r-slider--disabled': disabled, 'r-slider--readonly': readonly },
    ]"
  >
    <span
      v-if="valuePosition === 'left'"
      class="r-slider__badge r-slider__badge--left"
    >
      <slot name="value" :value="modelValue" :percent="percent">
        {{ formatted }}
      </slot>
    </span>

    <VSlider
      v-bind="$attrs"
      class="r-slider__core"
      :model-value="modelValue"
      :min="min"
      :max="max"
      :step="step"
      :color="color"
      :track-color="trackColor"
      :thumb-color="thumbColor"
      :size="size"
      :density="density"
      :hide-details="hideDetails"
      :disabled="disabled"
      :readonly="readonly"
      :thumb-label="showThumbLabel ? 'always' : false"
      :show-ticks="showTicks ? 'always' : false"
      @update:model-value="(v) => $emit('update:modelValue', Number(v))"
    >
      <template v-if="showThumbLabel" #thumb-label>
        <span class="r-slider__bubble">
          <slot name="value" :value="modelValue" :percent="percent">
            {{ formatted }}
          </slot>
        </span>
      </template>
      <template v-for="(_, slot) in $slots" #[slot]="slotProps">
        <slot
          v-if="
            String(slot) !== 'value' &&
            !(String(slot) === 'thumb-label' && showThumbLabel)
          "
          :name="slot"
          v-bind="slotProps || {}"
        />
      </template>
    </VSlider>

    <span
      v-if="valuePosition === 'right'"
      class="r-slider__badge r-slider__badge--right"
    >
      <slot name="value" :value="modelValue" :percent="percent">
        {{ formatted }}
      </slot>
    </span>
  </div>
</template>

<style scoped>
.r-slider {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.r-slider--pos-none,
.r-slider--pos-thumb {
  display: block;
}

.r-slider__core {
  flex: 1 1 auto;
  min-width: 0;
}

.r-slider--disabled {
  opacity: 0.55;
}

/* ── Track ─────────────────────────────────────────────── */

.r-slider :deep(.v-slider-track__background) {
  background: var(--r-color-bg-elevated) !important;
  border: 1px solid var(--r-color-panel-border);
  height: 5px !important;
  border-radius: var(--r-radius-full);
  opacity: 1 !important;
}

.r-slider :deep(.v-slider-track__fill) {
  background: linear-gradient(
    90deg,
    var(--r-color-brand-primary),
    var(--r-color-brand-primary-hover)
  ) !important;
  height: 5px !important;
  border-radius: var(--r-radius-full);
  box-shadow: 0 0 12px
    color-mix(in srgb, var(--r-color-brand-primary) 35%, transparent);
  transition: box-shadow var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-slider:hover :deep(.v-slider-track__fill),
.r-slider:focus-within :deep(.v-slider-track__fill) {
  box-shadow: 0 0 18px
    color-mix(in srgb, var(--r-color-brand-primary) 55%, transparent);
}

/* ── Tick marks ────────────────────────────────────────── */

.r-slider :deep(.v-slider-track__tick) {
  background: var(--r-color-fg-faint) !important;
  width: 3px !important;
  height: 3px !important;
  border-radius: 50%;
  opacity: 0.7;
}
.r-slider :deep(.v-slider-track__tick--filled) {
  background: color-mix(in srgb, var(--r-color-fg) 70%, transparent) !important;
  opacity: 1;
}

/* ── Thumb ─────────────────────────────────────────────── */

.r-slider :deep(.v-slider-thumb__surface) {
  background: var(--r-color-brand-primary) !important;
  width: 14px !important;
  height: 14px !important;
  border: 2px solid var(--r-color-fg);
  box-shadow: var(--r-elev-1);
  transition:
    transform var(--r-motion-fast) var(--r-motion-ease-out),
    box-shadow var(--r-motion-fast) var(--r-motion-ease-out),
    background var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-slider :deep(.v-slider-thumb:hover .v-slider-thumb__surface),
.r-slider :deep(.v-slider-thumb--focused .v-slider-thumb__surface) {
  transform: scale(1.18);
  box-shadow:
    var(--r-elev-2),
    0 0 0 6px color-mix(in srgb, var(--r-color-brand-primary) 25%, transparent);
}

.r-slider :deep(.v-slider-thumb--pressed .v-slider-thumb__surface) {
  transform: scale(1.28);
  background: var(--r-color-brand-primary-hover) !important;
}

/* Vuetify ripple feels heavy against this thinner thumb — drop it. */
.r-slider :deep(.v-slider-thumb__ripple) {
  display: none !important;
}

/* ── Side badge (left / right) ─────────────────────────── */

.r-slider__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: var(--r-font-weight-semibold);
  font-variant-numeric: tabular-nums;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-panel-border);
  border-radius: var(--r-radius-full);
  color: var(--r-color-fg-secondary);
  flex-shrink: 0;
  transition:
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out),
    background var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-slider:hover .r-slider__badge,
.r-slider:focus-within .r-slider__badge {
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 55%,
    transparent
  );
  color: var(--r-color-fg);
  background: color-mix(
    in srgb,
    var(--r-color-brand-primary) 12%,
    var(--r-color-bg-elevated)
  );
}

.r-slider--disabled .r-slider__badge,
.r-slider--readonly .r-slider__badge {
  /* Reset hover affordance when there's nothing to drag. */
  border-color: var(--r-color-panel-border);
  background: var(--r-color-bg-elevated);
  color: var(--r-color-fg-secondary);
}

/* ── Floating thumb bubble ─────────────────────────────── */

/* Strip Vuetify's default tooltip chrome; we paint our own pill. */
.r-slider :deep(.v-slider-thumb__label) {
  background: transparent !important;
  border: 0 !important;
  padding: 0 !important;
  color: inherit !important;
  box-shadow: none !important;
  min-width: 0 !important;
  height: auto !important;
}

.r-slider :deep(.v-slider-thumb__label::before) {
  display: none !important;
}

.r-slider__bubble {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  padding: 3px 10px;
  font-size: 11.5px;
  font-weight: var(--r-font-weight-semibold);
  font-variant-numeric: tabular-nums;
  color: var(--r-color-fg);
  background: linear-gradient(
    180deg,
    var(--r-color-brand-primary-hover),
    var(--r-color-brand-primary)
  );
  border-radius: var(--r-radius-full);
  box-shadow:
    0 4px 12px color-mix(in srgb, var(--r-color-brand-primary) 50%, transparent),
    inset 0 0 0 1px color-mix(in srgb, var(--r-color-fg) 18%, transparent);
}

/* Tail pointing down toward the thumb. */
.r-slider__bubble::after {
  content: "";
  position: absolute;
  bottom: -3px;
  left: 50%;
  width: 8px;
  height: 8px;
  background: var(--r-color-brand-primary);
  transform: translateX(-50%) rotate(45deg);
  border-bottom-right-radius: 2px;
  z-index: -1;
}
</style>
