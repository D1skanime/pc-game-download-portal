<script setup lang="ts">
// CardRow — horizontal-scrolling section used on the Home dashboard to
// group "Continue playing / Recently added / Favorites / Platforms /
// Collections". Feature composite; Home is the only caller today.
//
// Renders: header (icon + title + count), the default slot as a
// horizontal track, and gradient left/right arrow buttons that appear
// only when the track actually overflows in that direction.
import { RIcon } from "@v2/lib";
import { onMounted, ref } from "vue";

defineOptions({ inheritAttrs: false });

interface Props {
  title?: string;
  count?: number | string;
  /** Extra horizontal gap between children, e.g. "12px" (default) or "16px". */
  gap?: string;
}

withDefaults(defineProps<Props>(), {
  title: undefined,
  count: undefined,
  gap: "12px",
});

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
    <header v-if="title || $slots.icon || $slots.title" class="card-row__head">
      <span v-if="$slots.icon" class="card-row__icon">
        <slot name="icon" />
      </span>
      <h2 class="card-row__title">
        <slot name="title">{{ title }}</slot>
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
  gap: 8px;
  padding: 0 var(--r-row-pad);
  margin-bottom: 12px;
  color: rgba(255, 255, 255, 0.88);
}
:global(.r-v2.r-v2-light) .card-row__head {
  color: rgba(17, 17, 23, 0.88);
}

.card-row__icon {
  width: 14px;
  height: 14px;
  display: inline-grid;
  place-items: center;
  opacity: 0.5;
  flex-shrink: 0;
}

.card-row__icon :deep(.mdi) {
  font-size: 14px;
}

.card-row__title {
  font-size: 14.5px;
  font-weight: var(--r-font-weight-semibold);
  letter-spacing: 0.01em;
  margin: 0;
}

.card-row__count {
  font-size: 12px;
  font-weight: var(--r-font-weight-regular);
  color: rgba(255, 255, 255, 0.3);
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
  color: rgba(255, 255, 255, 0.85);
  transition:
    color 0.2s,
    opacity 0.2s;
}

.card-row__arrow--left {
  left: 0;
  background: linear-gradient(to right, rgba(7, 7, 15, 0.9), transparent);
  border-radius: 0 6px 6px 0;
}
.card-row__arrow--right {
  right: 0;
  background: linear-gradient(to left, rgba(7, 7, 15, 0.9), transparent);
  border-radius: 6px 0 0 6px;
}

.card-row__arrow :deep(.mdi) {
  filter: drop-shadow(0 1px 4px rgba(0, 0, 0, 0.6));
}

.card-row__arrow:hover {
  color: #fff;
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
