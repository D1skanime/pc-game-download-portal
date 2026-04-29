<script setup lang="ts">
// CardRow — horizontal-scrolling section used on the Home dashboard to
// group "Continue playing / Recently added / Favorites / Platforms /
// Collections". Feature composite; Home is the only caller today.
//
// Renders: header (icon + title + count), the default slot as a
// horizontal track, and gradient left/right arrow buttons that appear
// only when the track actually overflows in that direction.
//
// The icon slot sizes to its content — whatever size the caller's inner
// RIcon renders at drives the layout, and the title always stays
// vertically centred with it (flex align-items:center on the head).
import { RIcon } from "@v2/lib";
import { computed } from "vue";
import { onMounted, ref } from "vue";

defineOptions({ inheritAttrs: false });

interface Props {
  title?: string;
  count?: number | string;
  /** Horizontal gap between children in the scroll track. */
  gap?: string;
  /** Title font size — defaults to 14.5px. Accepts any CSS length. */
  titleSize?: string | number;
  /**
   * Title font weight — defaults to semibold. Accepts the named weights
   * used elsewhere (regular / medium / semibold / bold) or a raw number.
   */
  titleWeight?: "regular" | "medium" | "semibold" | "bold" | number;
  /** Space between icon and title. Grows naturally as icons get bigger. */
  iconGap?: string;
  /** Icon opacity — default 0.6 keeps it subdued against the title. Set
   *  to 1 when you want the icon to read as prominent as the title. */
  iconOpacity?: number;
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  count: undefined,
  gap: "12px",
  titleSize: "14.5px",
  titleWeight: "semibold",
  iconGap: "10px",
  iconOpacity: 0.6,
});

const resolvedTitleSize = computed(() =>
  typeof props.titleSize === "number"
    ? `${props.titleSize}px`
    : props.titleSize,
);

const WEIGHT_MAP = {
  regular: "var(--r-font-weight-regular)",
  medium: "var(--r-font-weight-medium)",
  semibold: "var(--r-font-weight-semibold)",
  bold: "var(--r-font-weight-bold)",
} as const;

const resolvedTitleWeight = computed(() =>
  typeof props.titleWeight === "number"
    ? `${props.titleWeight}`
    : WEIGHT_MAP[props.titleWeight],
);

const scrollEl = ref<HTMLElement | null>(null);
const canLeft = ref(false);
const canRight = ref(false);

function updateScroll() {
  const el = scrollEl.value;
  if (!el) return;
  canLeft.value = el.scrollLeft > 8;
  canRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 8;
}

function scrollBy(dir: -1 | 1) {
  const el = scrollEl.value;
  if (!el) return;
  el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: "smooth" });
}

onMounted(() => {
  requestAnimationFrame(updateScroll);
});
</script>

<template>
  <section class="card-row">
    <header
      v-if="title || $slots.icon || $slots.title"
      class="card-row__head"
      :style="{
        gap: iconGap,
        '--card-row-title-size': resolvedTitleSize,
        '--card-row-title-weight': resolvedTitleWeight,
        '--card-row-icon-opacity': iconOpacity,
      }"
    >
      <span v-if="$slots.icon" class="card-row__icon">
        <slot name="icon" />
      </span>
      <h2 class="card-row__title">
        <slot name="title">
          {{ title }}
        </slot>
      </h2>
      <span v-if="count != null" class="card-row__count">{{ count }}</span>
      <slot name="title-append" />
    </header>

    <div class="card-row__wrap">
      <button
        v-if="canLeft"
        type="button"
        class="card-row__arrow card-row__arrow--left"
        aria-label="Scroll left"
        @click="scrollBy(-1)"
      >
        <RIcon icon="mdi-chevron-left" size="22" />
      </button>
      <button
        v-if="canRight"
        type="button"
        class="card-row__arrow card-row__arrow--right"
        aria-label="Scroll right"
        @click="scrollBy(1)"
      >
        <RIcon icon="mdi-chevron-right" size="22" />
      </button>

      <div
        ref="scrollEl"
        class="card-row__track r-v2-scroll-hidden"
        :style="{ gap }"
        @scroll="updateScroll"
      >
        <slot />
      </div>
    </div>
  </section>
</template>

<style scoped>
.card-row {
  margin-bottom: 22px;
}

.card-row__head {
  display: flex;
  align-items: center;
  /* gap is driven inline via the --card-row icon gap prop. */
  padding: 0 var(--r-row-pad);
  margin-bottom: 12px;
  color: var(--r-color-fg-secondary);
}

/* Icon slot — sizes to its content so the caller's RIcon `size` drives
   the layout. Flex align-items:center on the head keeps it vertically
   centred with the title at any icon size. */
.card-row__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: var(--card-row-icon-opacity, 0.6);
  flex-shrink: 0;
  line-height: 0;
}

.card-row__title {
  font-size: var(--card-row-title-size, 14.5px);
  font-weight: var(--card-row-title-weight, var(--r-font-weight-semibold));
  letter-spacing: 0.01em;
  line-height: 1.2;
  margin: 0;
}

.card-row__count {
  font-size: 12px;
  font-weight: var(--r-font-weight-regular);
  color: var(--r-color-fg-faint);
  margin-left: 4px;
}

.card-row__wrap {
  position: relative;
}

.card-row__track {
  display: flex;
  padding: 16px var(--r-row-pad) 20px;
  overflow-x: auto;
  overflow-y: visible;
  scroll-behavior: smooth;
}

.card-row__arrow {
  appearance: none;
  border: 0;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  width: 40px;
  height: 72px;
  display: grid;
  place-items: center;
  cursor: pointer;
  color: var(--r-color-fg-secondary);
  transition:
    color 0.2s,
    opacity 0.2s;
}

.card-row__arrow--left {
  left: 0;
  background: linear-gradient(to right, var(--r-color-bg), transparent);
  border-radius: 0 6px 6px 0;
}
.card-row__arrow--right {
  right: 0;
  background: linear-gradient(to left, var(--r-color-bg), transparent);
  border-radius: 6px 0 0 6px;
}

.card-row__arrow :deep(.mdi) {
  filter: drop-shadow(0 1px 4px color-mix(in srgb, black 60%, transparent));
}

.card-row__arrow:hover {
  color: var(--r-color-fg);
}

@media (max-width: 768px) {
  .card-row__track {
    padding: 8px 14px 16px;
  }
  .card-row__arrow {
    display: none;
  }
  .card-row__head {
    padding: 0 14px;
  }
}
</style>
