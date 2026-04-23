<script setup lang="ts">
// AppNav — the top navigation. Logo on the left, centred tab pill,
// "switch to classic UI" icon + user menu on the right. Highlighting
// is derived from `route.path` rather than route names so gallery
// subroutes (e.g. /rom/:id) still light up the Home tab.
import { RBtn } from "@v2/lib";
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

type TabId = "home" | "favorites" | "platforms" | "collections" | "search";
const tabs: { id: TabId; label: string; to: string }[] = [
  { id: "home", label: "Home", to: "/" },
  { id: "favorites", label: "Favorites", to: "/collection/favorites" },
  { id: "platforms", label: "Platforms", to: "/platforms" },
  { id: "collections", label: "Collections", to: "/collections" },
  { id: "search", label: "Search", to: "/search" },
];

const activeTab = computed<TabId | null>(() => {
  const path = route.path;
  if (path === "/" || path.startsWith("/rom") || path === "/home")
    return "home";
  if (path.startsWith("/platform")) return "platforms";
  if (path.startsWith("/collection")) return "collections";
  if (path.startsWith("/search")) return "search";
  return null;
});
</script>

<template>
  <nav class="r-v2-nav">
    <router-link to="/" class="r-v2-nav__logo" aria-label="Home">
      <img src="/assets/isotipo.svg" alt="RomM" />
      <span class="r-v2-nav__wordmark">RomM</span>
    </router-link>

    <div class="r-v2-nav__center">
      <div class="r-v2-nav__pill">
        <router-link
          v-for="tab in tabs"
          :key="tab.id"
          :to="tab.to"
          class="r-v2-nav__tab"
          :class="{ 'r-v2-nav__tab--active': activeTab === tab.id }"
        >
          {{ tab.label }}
        </router-link>
      </div>
    </div>

    <div class="r-v2-nav__right">
      <RBtn
        icon="mdi-backup-restore"
        size="small"
        variant="text"
        class="r-v2-nav__classic"
        aria-label="Switch to classic UI"
        title="Classic UI"
        @click="switchToV1"
      />

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
}

.r-v2-nav__logo img {
  width: 32px;
  height: 32px;
  display: block;
}

.r-v2-nav__wordmark {
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
  letter-spacing: 0.02em;
}

.r-v2-nav__center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.r-v2-nav__pill {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--r-radius-pill);
  padding: 4px;
  gap: 2px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

:global(.r-v2.r-v2-light) .r-v2-nav__pill {
  background: rgba(17, 17, 23, 0.06);
  border-color: rgba(17, 17, 23, 0.1);
}

.r-v2-nav__tab {
  padding: 7px 22px;
  border-radius: var(--r-radius-pill);
  font-size: 13.5px;
  font-weight: var(--r-font-weight-medium);
  color: rgba(255, 255, 255, 0.62);
  text-decoration: none;
  transition:
    color var(--r-motion-fast) var(--r-motion-ease-out),
    background var(--r-motion-fast) var(--r-motion-ease-out);
}

:global(.r-v2.r-v2-light) .r-v2-nav__tab {
  color: rgba(17, 17, 23, 0.62);
}

.r-v2-nav__tab:hover {
  color: var(--r-color-fg);
  background: rgba(255, 255, 255, 0.09);
}

:global(.r-v2.r-v2-light) .r-v2-nav__tab:hover {
  background: rgba(17, 17, 23, 0.09);
}

.r-v2-nav__tab--active {
  color: #111 !important;
  background: #fff;
  font-weight: var(--r-font-weight-semibold);
}

:global(.r-v2.r-v2-light) .r-v2-nav__tab--active {
  color: #fff !important;
  background: #111;
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

  .r-v2-nav__wordmark {
    display: none;
  }

  .r-v2-nav__center {
    display: none;
  }
}
</style>
