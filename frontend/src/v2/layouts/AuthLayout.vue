<script setup lang="ts">
import { computed } from "vue";
import { useTheme } from "vuetify";
import storeHeartbeat from "@/stores/heartbeat";
import { V2_THEME_DARK } from "@/v2/theme/vuetify";

const heartbeatStore = storeHeartbeat();
const theme = useTheme();
const themeClass = computed(() =>
  theme.global.name.value === V2_THEME_DARK ? "r-v2-dark" : "r-v2-light",
);
</script>

<template>
  <div class="r-v2 r-v2-auth" :class="themeClass">
    <div class="r-v2-auth__bg" />
    <main class="r-v2-auth__stage">
      <router-view name="v2" />
    </main>
    <span class="r-v2-auth__version">
      {{ heartbeatStore.value.SYSTEM.VERSION }}
    </span>
  </div>
</template>

<style scoped>
.r-v2-auth {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--r-space-6);
  overflow: hidden;
}

.r-v2-auth__bg {
  position: absolute;
  inset: 0;
  background-image: url("/assets/auth_background.svg");
  background-size: cover;
  background-position: center;
  z-index: 0;
}

.r-v2-auth__bg::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(13, 17, 23, 0.5) 0%,
    rgba(13, 17, 23, 0.85) 100%
  );
}

.r-v2-auth.r-v2-light .r-v2-auth__bg::after {
  background: linear-gradient(
    180deg,
    rgba(242, 244, 248, 0.6) 0%,
    rgba(242, 244, 248, 0.9) 100%
  );
}

.r-v2-auth__stage {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
}

.r-v2-auth__version {
  position: absolute;
  right: var(--r-space-4);
  bottom: var(--r-space-3);
  z-index: 1;
  color: var(--r-color-fg-muted);
  font-family: var(--r-font-family-mono);
  font-size: var(--r-font-size-xs);
  letter-spacing: 0.02em;
}
</style>
