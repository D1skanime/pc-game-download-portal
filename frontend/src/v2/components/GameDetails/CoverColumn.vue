<script setup lang="ts">
// CoverColumn — fixed-width left column with the ROM cover (or a placeholder
// if none resolves). Sized via --r-cover-w and top-aligned so tall right-
// column content doesn't stretch the image.

defineOptions({ inheritAttrs: false });

defineProps<{
  src: string | null | undefined;
  alt: string;
}>();
</script>

<template>
  <div class="r-v2-det-cover">
    <img v-if="src" :src="src" :alt="alt" />
    <div v-else class="r-v2-det-cover__placeholder">
      {{ alt }}
    </div>
  </div>
</template>

<style scoped>
.r-v2-det-cover {
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 24px;
  width: var(--r-cover-w);
  filter: drop-shadow(0 24px 48px rgba(0, 0, 0, 0.8));
}

.r-v2-det-cover img {
  width: 100%;
  border-radius: var(--r-radius-lg);
  display: block;
}

.r-v2-det-cover__placeholder {
  width: var(--r-cover-w);
  height: 320px;
  border-radius: var(--r-radius-lg);
  background: #1a1a2e;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 24px;
  color: rgba(255, 255, 255, 0.25);
  font-size: 13px;
}

@media (max-width: 768px) {
  .r-v2-det-cover {
    width: 100px;
    margin-top: 0;
  }
  .r-v2-det-cover__placeholder {
    width: 100px;
    height: 134px;
  }
}
</style>
