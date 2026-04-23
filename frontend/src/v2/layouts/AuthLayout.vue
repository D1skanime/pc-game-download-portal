<script setup lang="ts">
// AuthLayout — full-viewport blurred background with a centred card stage
// for the auth flows (Login / Register / ResetPassword / Setup). Bottom
// corners hold the LanguageSelector (left) and VersionTag (right).
import { computed } from "vue";
import { useTheme } from "vuetify";
import LanguageSelector from "@/v2/components/shared/LanguageSelector.vue";
import VersionTag from "@/v2/components/shared/VersionTag.vue";
import { V2_THEME_DARK } from "@/v2/theme/vuetify";

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
    <div class="r-v2-auth__lang">
      <LanguageSelector />
    </div>
    <VersionTag class="r-v2-auth__version" />
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

.r-v2-auth__lang {
  position: absolute;
  left: var(--r-space-4);
  bottom: var(--r-space-3);
  z-index: 1;
}

.r-v2-auth__version {
  position: absolute;
  right: var(--r-space-4);
  bottom: var(--r-space-3);
  z-index: 1;
}
</style>
