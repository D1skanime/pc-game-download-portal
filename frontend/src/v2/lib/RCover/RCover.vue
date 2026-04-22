<script setup lang="ts">
import { computed, ref, watch } from "vue";

defineOptions({ inheritAttrs: false });

// RCover — smart cover image.
//
// Pass the ROM-level cover paths (`path_cover_small` / `path_cover_large`
// from SimpleRom) and an optional external url fallback (`url_cover`). The
// component renders the best available source, flipping to webp when the
// server supports it, and falls through to a procedural SVG placeholder
// when nothing resolves.

interface Props {
  src?: string | null;
  fallbackSrc?: string | null;
  alt?: string;
  aspectRatio?: string;
  rounded?: string;
  webp?: boolean;
  placeholder?: string; // Base64 SVG or text to render on full failure
}

const props = withDefaults(defineProps<Props>(), {
  src: null,
  fallbackSrc: null,
  alt: "",
  aspectRatio: "2 / 3",
  rounded: "md",
  webp: false,
  placeholder: undefined,
});

const EXTENSION_REGEX = /\.(png|jpg|jpeg)$/i;

const resolvedSrc = computed(() => {
  if (!props.src) return props.fallbackSrc ?? null;
  if (props.webp) return props.src.replace(EXTENSION_REGEX, ".webp");
  return props.src;
});

const errored = ref(false);
watch(resolvedSrc, () => {
  errored.value = false;
});

const showImage = computed(() => !!resolvedSrc.value && !errored.value);
const showFallback = computed(
  () => !showImage.value && !!props.fallbackSrc && !errored.value,
);

function onError() {
  errored.value = true;
}
</script>

<template>
  <div
    class="r-cover"
    :class="[`r-cover--rounded-${rounded}`]"
    :style="{ aspectRatio }"
  >
    <img
      v-if="showImage"
      :src="resolvedSrc ?? undefined"
      :alt="alt"
      loading="lazy"
      class="r-cover__img"
      @error="onError"
    />
    <img
      v-else-if="showFallback"
      :src="fallbackSrc ?? undefined"
      :alt="alt"
      loading="lazy"
      class="r-cover__img"
      @error="() => (errored = true)"
    />
    <div v-else class="r-cover__placeholder">
      <slot name="placeholder">
        <span class="r-cover__placeholder-text">
          {{ placeholder ?? alt ?? "" }}
        </span>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.r-cover {
  position: relative;
  width: 100%;
  overflow: hidden;
  background: linear-gradient(
    135deg,
    var(--r-color-surface),
    var(--r-color-bg)
  );
  border: 1px solid var(--r-color-border);
}

.r-cover--rounded-sm {
  border-radius: var(--r-radius-sm);
}
.r-cover--rounded-md {
  border-radius: var(--r-radius-md);
}
.r-cover--rounded-lg {
  border-radius: var(--r-radius-lg);
}

.r-cover__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.r-cover__placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: var(--r-space-3);
  color: var(--r-color-fg-muted);
  font-family: var(--r-font-family-display);
  font-weight: var(--r-font-weight-semibold);
  text-align: center;
  font-size: var(--r-font-size-sm);
  overflow: hidden;
}

.r-cover__placeholder-text {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
