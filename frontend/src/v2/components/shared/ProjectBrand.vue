<script setup lang="ts">
// Text identity owns in-app presentation until supplied product artwork is available.
import { PROJECT_NAME, PROJECT_SHORT_NAME } from "@/v2/config/project";

interface Props {
  variant: "auth" | "navigation" | "about";
}

defineProps<Props>();
</script>

<template>
  <span
    class="project-brand d-inline-flex align-center"
    :class="`project-brand--${variant}`"
  >
    <span v-if="variant !== 'auth'" class="project-brand__short">{{
      PROJECT_SHORT_NAME
    }}</span>
    <span v-if="variant !== 'about'" class="project-brand__word">{{
      PROJECT_NAME
    }}</span>
  </span>
</template>

<style scoped>
.project-brand {
  gap: 10px;
  color: var(--r-color-fg);
  font-family: var(--r-font-family-display);
  font-weight: var(--r-font-weight-semibold);
  line-height: var(--r-line-height-tight);
  white-space: nowrap;
}
.project-brand--auth {
  font-size: var(--r-font-size-3xl);
}
.project-brand--navigation .project-brand__short {
  font-size: var(--r-font-size-2xl);
}
.project-brand--navigation .project-brand__word {
  font-size: var(--r-font-size-xl);
}
.project-brand--about {
  font-size: var(--r-font-size-md);
}
html[data-bp~="xs"] .project-brand--navigation .project-brand__word {
  display: none;
}
</style>
