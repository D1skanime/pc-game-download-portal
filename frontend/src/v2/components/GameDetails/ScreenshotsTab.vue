<script setup lang="ts">
// ScreenshotsTab — responsive grid of 16:9 screenshot thumbnails.
// Clicking opens the full image in a new tab (polish pass will add a
// proper lightbox).

defineOptions({ inheritAttrs: false });

defineProps<{ urls: string[] }>();
</script>

<template>
  <section class="r-v2-det-shots">
    <a
      v-for="(src, i) in urls"
      :key="src"
      :href="src"
      target="_blank"
      rel="noopener"
      class="r-v2-det-shots__item"
    >
      <img :src="src" :alt="`Screenshot ${i + 1}`" loading="lazy" />
    </a>
  </section>
</template>

<style scoped>
.r-v2-det-shots {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.r-v2-det-shots__item {
  aspect-ratio: 16 / 9;
  border-radius: 6px;
  overflow: hidden;
  background: var(--r-color-cover-placeholder);
  transition: transform 0.2s;
}
.r-v2-det-shots__item:hover {
  transform: scale(1.02);
}
.r-v2-det-shots__item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>
