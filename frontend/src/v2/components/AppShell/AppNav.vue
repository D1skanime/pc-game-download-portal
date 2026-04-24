<script setup lang="ts">
// AppNav — the top navigation. Logo on the left, centred tab pill,
// "switch to classic UI" icon + user menu on the right. Highlighting
// is derived from `route.path` rather than route names so gallery
// subroutes (e.g. /rom/:id) still light up the Home tab.
import { RBtn, RSliderBtnGroup, RTooltip, RImg } from "@v2/lib";
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useUiVersion } from "@/composables/useUiVersion";
import UserMenu from "@/v2/components/AppShell/UserMenu.vue";

defineOptions({ inheritAttrs: false });

const route = useRoute();
const uiVersion = useUiVersion();

function switchToV1() {
  uiVersion.value = "v1";
}

type TabId = "home" | "platforms" | "collections" | "search";
const tabs = [
  { id: "home" as const, label: "Home", to: "/" },
  { id: "platforms" as const, label: "Platforms", to: "/platforms" },
  { id: "collections" as const, label: "Collections", to: "/collections" },
  { id: "search" as const, label: "Search", to: "/search" },
];

const activeTab = computed<TabId | null>(() => {
  const path = route.path;
  if (path === "/") return "home";
  if (path.startsWith("/platform")) return "platforms";
  if (path.startsWith("/collection")) return "collections";
  if (path.startsWith("/search")) return "search";
  return null;
});
</script>

<template>
  <nav class="r-v2-nav">
    <router-link to="/" class="r-v2-nav__logo" aria-label="Home">
      <RImg
        src="/assets/isotipo.svg"
        alt="RomM isotipo"
        aria-hidden="true"
        class="r-v2-nav__logo-mark"
        :width="32"
      />
      <RImg
        src="/assets/logotipo.svg"
        alt="RomM logotipo"
        aria-hidden="true"
        class="r-v2-nav__logo-word"
        :width="70"
      />
    </router-link>

    <div class="r-v2-nav__center">
      <RSliderBtnGroup
        :model-value="activeTab"
        :items="tabs"
        variant="tab"
        aria-label="Primary navigation"
      />
    </div>

    <div class="r-v2-nav__right">
      <RTooltip text="Switch to classic UI" location="bottom">
        <template #activator="{ props: tooltipProps }">
          <RBtn
            v-bind="tooltipProps"
            prepend-icon="mdi-backup-restore"
            size="small"
            variant="text"
            class="r-v2-nav__classic"
            aria-label="Switch to classic UI"
            @click="switchToV1"
            >Classic UI</RBtn
          >
        </template>
      </RTooltip>

      <UserMenu />
    </div>
  </nav>
</template>

<style scoped>
.r-v2-nav {
  height: var(--r-nav-h);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 var(--r-row-pad);
  gap: 0;
}

.r-v2-nav__logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--r-color-fg);
  flex-shrink: 0;
  /* Both marks transition together so the glow reads as one gesture. */
  transition: filter var(--r-motion-med) var(--r-motion-ease-out);
}
.r-v2-nav__logo:hover,
.r-v2-nav__logo:focus-visible {
  filter: drop-shadow(0 0 6px rgba(139, 116, 232, 0.55));
}
.r-v2-nav__logo:focus-visible {
  outline: none;
}

.r-v2-nav__logo-mark {
  width: 32px;
  height: 32px;
  display: block;
}

.r-v2-nav__logo-word {
  height: 22px;
  width: auto;
  display: block;
}

.r-v2-nav__center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.r-v2-nav__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Ghost-pill styling for the "classic UI" button (matches the old RIconBtn
   ghost variant — translucent glass, subtle border). */
.r-v2-nav__classic {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  color: rgba(255, 255, 255, 0.8) !important;
  opacity: 1;
}
.r-v2-nav__classic:hover {
  background: rgba(255, 255, 255, 0.16) !important;
  color: #fff !important;
}

@media (max-width: 768px) {
  .r-v2-nav {
    padding: 0 14px;
    justify-content: space-between;
  }

  .r-v2-nav__logo-word {
    display: none;
  }

  .r-v2-nav__center {
    display: none;
  }
}
</style>
