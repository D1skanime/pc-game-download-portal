<script setup lang="ts">
// Shared auth frame for login, registration, password reset and setup.
import { RCard } from "@v2/lib";
import ProjectBrand from "@/v2/components/shared/ProjectBrand.vue";

defineOptions({ inheritAttrs: false });
</script>

<template>
  <RCard v-bind="$attrs" class="auth-card" variant="elevated" elevation="4">
    <div class="auth-card__inner">
      <ProjectBrand variant="auth" class="auth-card__brand" />
      <slot />
    </div>
  </RCard>
</template>

<style scoped>
.auth-card {
  width: 100%;
  max-width: 440px;
  /* Allow the centered frame to shrink on narrow phones. */
  min-width: 0;
  border-radius: var(--r-radius-lg) !important;
  box-shadow: var(--r-elev-4) !important;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--r-color-canvas-bg-deep) 65%, transparent) 0%,
    color-mix(in srgb, var(--r-color-canvas-bg-deep) 65%, transparent) 100%
  );
}

.auth-card__inner {
  padding: var(--r-space-8) var(--r-space-6);
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.auth-card__brand {
  margin: 0 auto var(--r-space-2);
}
</style>
