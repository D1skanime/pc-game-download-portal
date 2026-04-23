<script setup lang="ts">
// AuthCard — the translucent card frame used by every auth view
// (Login / Register / ResetPassword / Setup). Wraps RCard, the logo,
// and the padded inner column. Views drop their form content into the
// default slot.
import { RCard, RImg } from "@v2/lib";

defineOptions({ inheritAttrs: false });
</script>

<template>
  <RCard v-bind="$attrs" class="auth-card" variant="elevated" elevation="4">
    <div class="auth-card__inner">
      <RImg
        src="/assets/isotipo.svg"
        :width="80"
        class="auth-card__logo"
        alt="RomM"
      />
      <slot />
    </div>
  </RCard>
</template>

<style scoped>
.auth-card {
  width: 100%;
  max-width: 440px;
  border-radius: var(--r-radius-lg) !important;
  box-shadow: var(--r-elev-4) !important;
  background: linear-gradient(
    180deg,
    rgba(13, 17, 23, 0.65) 0%,
    rgba(13, 17, 23, 0.65) 100%
  );
}

.auth-card__inner {
  padding: var(--r-space-8) var(--r-space-6);
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.auth-card__logo {
  margin: 0 auto var(--r-space-2);
  filter: drop-shadow(0 0 16px rgba(139, 116, 232, 0.3));
}
</style>
