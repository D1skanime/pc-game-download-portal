<script setup lang="ts">
import { computed, ref, watch } from "vue";

defineOptions({ inheritAttrs: false });

// RPlatformIcon — renders the platform's .ico served from /assets/platforms
// and falls back to a generic controller glyph if the platform icon 404s.
// Accepts either a platform name (preferred, matches v1's /assets/platforms
// filenames) or an explicit src.
interface Props {
  name?: string;
  src?: string;
  size?: number | string;
  alt?: string;
  title?: string;
}

const props = withDefaults(defineProps<Props>(), {
  name: undefined,
  src: undefined,
  size: 28,
  alt: "",
  title: undefined,
});

const resolvedSrc = computed(() => {
  if (props.src) return props.src;
  if (props.name) return `/assets/platforms/${props.name.toLowerCase()}.ico`;
  return null;
});

const errored = ref(false);
watch(resolvedSrc, () => {
  errored.value = false;
});

const resolvedSize = computed(() =>
  typeof props.size === "number" ? `${props.size}px` : props.size,
);
</script>

<template>
  <span
    class="r-platform-icon"
    :style="{ width: resolvedSize, height: resolvedSize }"
    :title="title ?? alt ?? name"
  >
    <img
      v-if="resolvedSrc && !errored"
      :src="resolvedSrc"
      :alt="alt ?? name ?? ''"
      class="r-platform-icon__img"
      @error="errored = true"
    />
    <svg
      v-else
      class="r-platform-icon__fallback"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        fill="currentColor"
        d="M7.5 6A5.5 5.5 0 0 0 2 11.5v1A5.5 5.5 0 0 0 7.5 18a4.48 4.48 0 0 0 3.8-2.1l.7-1.1L12.7 16c.3.5.8 1.3 1.8 1.7a5 5 0 0 0 2 .3a5.5 5.5 0 0 0 5.5-5.5v-1A5.5 5.5 0 0 0 16.5 6h-9Zm1 3h1v1.5H11v1H9.5V13h-1v-1.5H7v-1h1.5V9Zm7 1.5a1 1 0 1 1 0 2a1 1 0 0 1 0-2Zm3 0a1 1 0 1 1 0 2a1 1 0 0 1 0-2Z"
      />
    </svg>
  </span>
</template>

<style scoped>
.r-platform-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--r-color-fg-muted);
}

.r-platform-icon__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
}

.r-platform-icon__fallback {
  width: 100%;
  height: 100%;
}
</style>
