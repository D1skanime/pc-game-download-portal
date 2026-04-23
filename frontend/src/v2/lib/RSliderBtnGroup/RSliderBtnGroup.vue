<script setup lang="ts" generic="T extends string | number">
// RSliderBtnGroup — segmented/tab control with a sliding pill indicator.
// One active id at a time; the indicator transitions from the previous button
// to the new one on modelValue change.
//
// Variants:
//   * "segmented" — 28×28 icon-only buttons (used by GalleryToolbar).
//   * "tab"       — text-padded tabs (used by AppNav).
//
// Items with `to` render as <router-link> (navigation); items without render
// as <RBtn> and emit update:modelValue on click. Active id is always driven
// externally — the consumer decides it from route, prop, or store.
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import RBtn from "../RBtn/RBtn.vue";
import RIcon from "../RIcon/RIcon.vue";
import RTooltip from "../RTooltip/RTooltip.vue";
import type { SliderBtnGroupItem } from "./types";

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    modelValue: T | null;
    items: SliderBtnGroupItem<T>[];
    variant?: "segmented" | "tab";
    ariaLabel?: string;
    /** Disable the whole cluster — dims the container and blocks clicks on
     *  every item, regardless of per-item `disabled`. */
    disabled?: boolean;
  }>(),
  {
    variant: "segmented",
    ariaLabel: undefined,
    disabled: false,
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: T): void;
}>();

const groupEl = ref<HTMLElement | null>(null);
const btnEls = new Map<T, HTMLElement | null>();
const rect = ref({ left: 0, width: 0, visible: false });
const animate = ref(false);

function setBtnEl(id: T, inst: unknown) {
  if (!inst) {
    btnEls.set(id, null);
    return;
  }
  const el =
    inst instanceof HTMLElement
      ? inst
      : ((inst as { $el?: HTMLElement }).$el ?? null);
  btnEls.set(id, el);
}

function update() {
  const g = groupEl.value;
  if (!g) {
    rect.value = { ...rect.value, visible: false };
    return;
  }
  const active = props.modelValue;
  if (active == null) {
    rect.value = { ...rect.value, visible: false };
    return;
  }
  const el = btnEls.get(active as T);
  if (!el) {
    rect.value = { ...rect.value, visible: false };
    return;
  }
  const gRect = g.getBoundingClientRect();
  const eRect = el.getBoundingClientRect();
  rect.value = {
    left: eRect.left - gRect.left,
    width: eRect.width,
    visible: true,
  };
}

watch(
  () => props.modelValue,
  () => nextTick(update),
);
// `items` can change (e.g. responsive label swap); reposition if so.
watch(
  () => props.items,
  () => nextTick(update),
  { deep: true },
);

onMounted(async () => {
  await nextTick();
  update();
  requestAnimationFrame(() => {
    animate.value = true;
  });
  window.addEventListener("resize", update);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", update);
});
</script>

<template>
  <div
    ref="groupEl"
    class="r-slider-btn-group"
    :class="[
      `r-slider-btn-group--${variant}`,
      { 'r-slider-btn-group--disabled': disabled },
    ]"
    :aria-label="ariaLabel"
    :aria-disabled="disabled || undefined"
    :role="ariaLabel ? 'group' : undefined"
  >
    <span
      class="r-slider-btn-group__indicator"
      :class="{ 'r-slider-btn-group__indicator--animate': animate }"
      :style="{
        transform: `translateX(${rect.left}px)`,
        width: `${rect.width}px`,
        opacity: rect.visible ? 1 : 0,
      }"
      aria-hidden="true"
    />
    <template v-for="item in items" :key="item.id">
      <router-link
        v-if="item.to"
        :ref="(el) => setBtnEl(item.id, el)"
        :to="item.to"
        class="r-slider-btn-group__btn"
        :class="{ 'r-slider-btn-group__btn--active': item.id === modelValue }"
        :aria-label="item.ariaLabel"
      >
        <RTooltip
          v-if="item.title"
          activator="parent"
          :text="item.title"
          location="bottom"
        />
        <slot name="item" :item="item" :active="item.id === modelValue">
          <RIcon v-if="item.icon" :icon="item.icon" size="16" />
          <span v-if="item.label" class="r-slider-btn-group__label">
            {{ item.label }}
          </span>
        </slot>
      </router-link>
      <RBtn
        v-else
        :ref="(el) => setBtnEl(item.id, el)"
        variant="text"
        density="compact"
        size="x-small"
        class="r-slider-btn-group__btn"
        :class="{ 'r-slider-btn-group__btn--active': item.id === modelValue }"
        :aria-label="item.ariaLabel"
        :aria-pressed="item.id === modelValue"
        :disabled="disabled || item.disabled"
        @click="emit('update:modelValue', item.id)"
      >
        <RTooltip
          v-if="item.title"
          activator="parent"
          :text="item.title"
          location="bottom"
        />
        <slot name="item" :item="item" :active="item.id === modelValue">
          <RIcon v-if="item.icon" :icon="item.icon" size="16" />
          <span v-if="item.label" class="r-slider-btn-group__label">
            {{ item.label }}
          </span>
        </slot>
      </RBtn>
    </template>
  </div>
</template>

<style scoped>
.r-slider-btn-group {
  position: relative;
  display: inline-flex;
  align-items: center;
  border-radius: var(--r-radius-pill);
}

/* Segmented — thin 28×28 icon cluster (toolbar-style). */
.r-slider-btn-group--segmented {
  padding: 2px;
  gap: 2px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Tab — text-padded cluster (top-nav style). */
.r-slider-btn-group--tab {
  padding: 4px;
  gap: 2px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.r-slider-btn-group__indicator {
  position: absolute;
  left: 0;
  background: #fff;
  border-radius: var(--r-radius-pill);
  pointer-events: none;
  will-change: transform, width;
  opacity: 0;
}

.r-slider-btn-group--segmented .r-slider-btn-group__indicator {
  top: 2px;
  bottom: 2px;
}
.r-slider-btn-group--tab .r-slider-btn-group__indicator {
  top: 4px;
  bottom: 4px;
}

.r-slider-btn-group__indicator--animate {
  transition:
    transform var(--r-motion-med) var(--r-motion-ease-out),
    width var(--r-motion-med) var(--r-motion-ease-out),
    opacity var(--r-motion-fast) var(--r-motion-ease-out);
}

/* Whole-cluster disabled — dim everything and block clicks. Router-link
   items don't honour a `disabled` prop, so pointer-events:none is the
   reliable escape hatch. */
.r-slider-btn-group--disabled {
  opacity: 0.4;
  pointer-events: none;
}

/* Button — common. Indicator owns the active background; buttons stay
   transparent so the slide reads cleanly behind them. `transform` + extra
   transitions give the hover/press animation parity with RBtn, where
   Vuetify's v-btn ships an overlay + slight lift by default. */
.r-slider-btn-group__btn {
  position: relative;
  z-index: 1;
  border-radius: var(--r-radius-pill) !important;
  text-decoration: none;
  transition:
    color var(--r-motion-fast) var(--r-motion-ease-out),
    background-color var(--r-motion-fast) var(--r-motion-ease-out),
    transform var(--r-motion-fast) var(--r-motion-ease-out);
}
/* Press feedback: subtle scale-down, skipping the active pill so its
   content doesn't pulse during a drag/repeat. */
.r-slider-btn-group__btn:active:not(.r-slider-btn-group__btn--active) {
  transform: scale(0.94);
}

/* Segmented sizing + colors. RBtn wraps v-btn which applies `color="primary"`
   as a `.text-primary` utility with !important — to get a neutral grey by
   default we need equal-or-greater specificity + !important. */
.r-slider-btn-group--segmented .r-slider-btn-group__btn {
  min-width: 28px !important;
  min-height: 28px !important;
  width: 28px !important;
  height: 28px !important;
  padding: 0 !important;
  background: transparent !important;
  color: rgba(255, 255, 255, 0.55) !important;
  display: inline-grid;
  place-items: center;
}
.r-slider-btn-group--segmented .r-slider-btn-group__btn :deep(.v-btn__content) {
  min-width: 0;
}
.r-slider-btn-group--segmented
  .r-slider-btn-group__btn:hover:not(.r-slider-btn-group__btn--active) {
  color: rgba(255, 255, 255, 0.9) !important;
  background: rgba(255, 255, 255, 0.08) !important;
  transform: scale(1.08);
}
.r-slider-btn-group--segmented .r-slider-btn-group__btn--active,
.r-slider-btn-group--segmented .r-slider-btn-group__btn--active:hover {
  color: #111 !important;
}

/* Tab sizing + colors. */
.r-slider-btn-group--tab .r-slider-btn-group__btn {
  padding: 7px 22px;
  font-size: 13.5px;
  font-weight: var(--r-font-weight-medium);
  color: rgba(255, 255, 255, 0.62) !important;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.r-slider-btn-group--tab
  .r-slider-btn-group__btn:hover:not(.r-slider-btn-group__btn--active) {
  color: var(--r-color-fg) !important;
  background: rgba(255, 255, 255, 0.09);
}
.r-slider-btn-group--tab .r-slider-btn-group__btn--active,
.r-slider-btn-group--tab .r-slider-btn-group__btn--active:hover {
  color: #111 !important;
  background: transparent !important;
  font-weight: var(--r-font-weight-semibold);
}

/* Light theme. */
:global(.r-v2.r-v2-light) .r-slider-btn-group--segmented {
  background: rgba(17, 17, 23, 0.05);
  border-color: rgba(17, 17, 23, 0.08);
}
:global(.r-v2.r-v2-light) .r-slider-btn-group--tab {
  background: rgba(17, 17, 23, 0.06);
  border-color: rgba(17, 17, 23, 0.1);
}
:global(.r-v2.r-v2-light) .r-slider-btn-group__indicator {
  background: #111;
}
:global(.r-v2.r-v2-light)
  .r-slider-btn-group--segmented
  .r-slider-btn-group__btn {
  color: rgba(17, 17, 23, 0.55) !important;
}
:global(.r-v2.r-v2-light)
  .r-slider-btn-group--segmented
  .r-slider-btn-group__btn:hover:not(.r-slider-btn-group__btn--active) {
  color: rgba(17, 17, 23, 0.9) !important;
  background: rgba(17, 17, 23, 0.06) !important;
}
:global(.r-v2.r-v2-light)
  .r-slider-btn-group--segmented
  .r-slider-btn-group__btn--active,
:global(.r-v2.r-v2-light)
  .r-slider-btn-group--segmented
  .r-slider-btn-group__btn--active:hover {
  color: #fff !important;
}
:global(.r-v2.r-v2-light) .r-slider-btn-group--tab .r-slider-btn-group__btn {
  color: rgba(17, 17, 23, 0.62) !important;
}
:global(.r-v2.r-v2-light)
  .r-slider-btn-group--tab
  .r-slider-btn-group__btn:hover:not(.r-slider-btn-group__btn--active) {
  background: rgba(17, 17, 23, 0.09);
}
:global(.r-v2.r-v2-light)
  .r-slider-btn-group--tab
  .r-slider-btn-group__btn--active,
:global(.r-v2.r-v2-light)
  .r-slider-btn-group--tab
  .r-slider-btn-group__btn--active:hover {
  color: #fff !important;
  background: transparent !important;
}
</style>
