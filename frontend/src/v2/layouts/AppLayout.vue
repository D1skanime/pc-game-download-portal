<script setup lang="ts">
import {
  RAvatar,
  RBtn,
  RIcon,
  RList,
  RListItem,
  RMenu,
  RTooltip,
} from "@v2/lib";
import { useLocalStorage } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import { useTheme } from "vuetify";
import { useDisplay } from "vuetify";
import { useUiVersion } from "@/composables/useUiVersion";
import storeAuth from "@/stores/auth";
import { useInputModality } from "@/v2/composables/useInputModality";
import { V2_THEME_DARK } from "@/v2/theme/vuetify";

const theme = useTheme();
const { mdAndDown } = useDisplay();
const authStore = storeAuth();
const { user } = storeToRefs(authStore);

const themeClass = computed(() =>
  theme.global.name.value === V2_THEME_DARK ? "r-v2-dark" : "r-v2-light",
);

// Drawer state — persistent on desktop via localStorage, off-canvas on mobile.
const drawerOpen = useLocalStorage("settings.v2.drawerOpen", true);
const isMobile = computed(() => mdAndDown.value);
const drawerVisible = computed(() =>
  isMobile.value ? drawerOpen.value : drawerOpen.value !== false,
);
const backdropVisible = computed(
  () => isMobile.value && drawerOpen.value === true,
);

function toggleDrawer() {
  drawerOpen.value = !drawerOpen.value;
}

function closeDrawerOnMobile() {
  if (isMobile.value) drawerOpen.value = false;
}

const uiVersion = useUiVersion();
function switchToV1() {
  uiVersion.value = "v1";
}

// Top-level nav. Routes that don't have a v2 implementation yet will render
// NotReady.vue — still useful for proving navigation works end-to-end.
const navItems = computed(() => [
  { title: "Home", icon: "mdi-home", to: "/" },
  { title: "Search", icon: "mdi-magnify", to: "/search" },
  { title: "Scan", icon: "mdi-magnify-scan", to: "/scan" },
  { title: "Patcher", icon: "mdi-bandage", to: "/patcher" },
]);

const settingsItems = computed(() => [
  {
    title: "User profile",
    icon: "mdi-account",
    to: `/user/${user.value?.id ?? ""}`,
  },
  { title: "Interface", icon: "mdi-palette", to: "/user-interface" },
  { title: "Library", icon: "mdi-folder-multiple", to: "/library-management" },
  { title: "Metadata sources", icon: "mdi-database", to: "/metadata-sources" },
  { title: "Server stats", icon: "mdi-chart-line", to: "/server-stats" },
]);

const { install: installInputModality } = useInputModality();

onMounted(() => {
  installInputModality();
});
</script>

<template>
  <div class="r-v2 r-v2-shell" :class="themeClass">
    <header class="r-v2-shell__bar">
      <div class="r-v2-shell__bar-left">
        <RBtn
          variant="text"
          size="small"
          icon
          :aria-label="drawerOpen ? 'Close navigation' : 'Open navigation'"
          @click="toggleDrawer"
        >
          <RIcon :icon="drawerOpen ? 'mdi-menu-open' : 'mdi-menu'" />
        </RBtn>
        <router-link to="/" class="r-v2-shell__brand">
          <img
            src="/assets/isotipo.svg"
            alt=""
            class="r-v2-shell__brand-mark"
          />
          <span class="r-v2-shell__brand-name">RomM</span>
          <span class="r-v2-shell__brand-chip">v2 preview</span>
        </router-link>
      </div>

      <div class="r-v2-shell__bar-spacer" />

      <div class="r-v2-shell__bar-right">
        <RTooltip text="Switch to classic UI">
          <template #activator="{ props: tipProps }">
            <RBtn
              v-bind="tipProps"
              variant="text"
              size="small"
              prepend-icon="mdi-arrow-u-left-top"
              @click="switchToV1"
            >
              Classic
            </RBtn>
          </template>
        </RTooltip>

        <RMenu>
          <template #activator="{ props: menuProps }">
            <button
              v-bind="menuProps"
              type="button"
              class="r-v2-shell__user-btn"
              :aria-label="`Account menu (${user?.username ?? 'signed out'})`"
            >
              <RAvatar
                :size="36"
                color="primary"
                :image="
                  user?.avatar_path
                    ? `/assets/romm/assets${user.avatar_path}`
                    : undefined
                "
              >
                <template v-if="!user?.avatar_path">
                  {{ (user?.username ?? "?").charAt(0).toUpperCase() }}
                </template>
              </RAvatar>
            </button>
          </template>
          <div class="r-v2-shell__user-menu">
            <div class="r-v2-shell__user-info">
              <RAvatar :size="40" color="primary">
                {{ (user?.username ?? "?").charAt(0).toUpperCase() }}
              </RAvatar>
              <div>
                <div class="r-v2-shell__user-name">
                  {{ user?.username ?? "Signed out" }}
                </div>
                <div class="r-v2-shell__user-role">
                  {{ user?.role ?? "" }}
                </div>
              </div>
            </div>
            <RList nav density="compact">
              <RListItem
                prepend-icon="mdi-account"
                title="Profile"
                :to="`/user/${user?.id ?? ''}`"
              />
              <RListItem
                prepend-icon="mdi-palette"
                title="Interface"
                to="/user-interface"
              />
              <RListItem prepend-icon="mdi-logout" title="Log out" />
            </RList>
          </div>
        </RMenu>
      </div>
    </header>

    <aside
      class="r-v2-shell__drawer"
      :class="{
        'r-v2-shell__drawer--closed': !drawerVisible,
        'r-v2-shell__drawer--mobile': isMobile,
      }"
    >
      <RList nav density="comfortable">
        <RListItem
          v-for="item in navItems"
          :key="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          :to="item.to"
          @click="closeDrawerOnMobile"
        />
      </RList>
      <div class="r-v2-shell__drawer-divider" />
      <div class="r-v2-shell__drawer-section">Settings</div>
      <RList nav density="comfortable">
        <RListItem
          v-for="item in settingsItems"
          :key="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          :to="item.to"
          @click="closeDrawerOnMobile"
        />
      </RList>
    </aside>

    <div
      v-if="backdropVisible"
      class="r-v2-shell__backdrop"
      :aria-hidden="true"
      @click="toggleDrawer"
    />

    <main
      class="r-v2-shell__main"
      :class="{ 'r-v2-shell__main--full': !drawerVisible || isMobile }"
    >
      <router-view name="v2" />
    </main>
  </div>
</template>

<style scoped>
.r-v2-shell {
  min-height: 100vh;
  background-color: var(--r-color-bg);
  color: var(--r-color-fg);
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: 64px 1fr;
  grid-template-areas:
    "bar bar"
    "drawer main";
}

.r-v2-shell__bar {
  grid-area: bar;
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
  padding: 0 var(--r-space-4);
  background-color: var(--r-color-bg-elevated);
  border-bottom: 1px solid var(--r-color-border);
  height: 64px;
}

.r-v2-shell__bar-left {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
}

.r-v2-shell__brand {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
  color: var(--r-color-fg);
  text-decoration: none;
  border-radius: var(--r-radius-md);
  padding: var(--r-space-1) var(--r-space-2);
}

.r-v2-shell__brand-mark {
  width: 28px;
  height: 28px;
}

.r-v2-shell__brand-name {
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
  letter-spacing: 0.02em;
}

.r-v2-shell__brand-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--r-space-2);
  background-color: var(--r-color-brand-primary);
  color: #fff;
  font-size: var(--r-font-size-xs);
  font-weight: var(--r-font-weight-medium);
  border-radius: var(--r-radius-full);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.r-v2-shell__bar-spacer {
  flex: 1;
}

.r-v2-shell__bar-right {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
}

.r-v2-shell__user-btn {
  appearance: none;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  border-radius: var(--r-radius-full);
}

.r-v2-shell__user-menu {
  min-width: 260px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  padding: var(--r-space-3);
  box-shadow: var(--r-elev-3);
}

.r-v2-shell__user-info {
  display: flex;
  gap: var(--r-space-3);
  align-items: center;
  padding: var(--r-space-2) var(--r-space-2) var(--r-space-3);
  border-bottom: 1px solid var(--r-color-border);
  margin-bottom: var(--r-space-2);
}

.r-v2-shell__user-name {
  font-weight: var(--r-font-weight-semibold);
}

.r-v2-shell__user-role {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.r-v2-shell__drawer {
  grid-area: drawer;
  position: sticky;
  top: 64px;
  align-self: start;
  width: 260px;
  height: calc(100vh - 64px);
  overflow-y: auto;
  padding: var(--r-space-3);
  background-color: var(--r-color-bg-elevated);
  border-right: 1px solid var(--r-color-border);
  transition:
    transform var(--r-motion-med) var(--r-motion-ease-out),
    opacity var(--r-motion-med) var(--r-motion-ease-out);
}

.r-v2-shell__drawer--closed {
  transform: translateX(-110%);
  opacity: 0;
  pointer-events: none;
}

.r-v2-shell__drawer--mobile {
  position: fixed;
  top: 64px;
  left: 0;
  z-index: 4;
  box-shadow: var(--r-elev-4);
}

.r-v2-shell__drawer-divider {
  height: 1px;
  margin: var(--r-space-3) var(--r-space-2);
  background: var(--r-color-border);
}

.r-v2-shell__drawer-section {
  padding: 0 var(--r-space-2) var(--r-space-2);
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: var(--r-font-weight-semibold);
}

.r-v2-shell__backdrop {
  position: fixed;
  inset: 64px 0 0 0;
  z-index: 3;
  background: rgba(0, 0, 0, 0.6);
  animation: r-v2-fade-in var(--r-motion-fast) var(--r-motion-ease-out);
}

@keyframes r-v2-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.r-v2-shell__main {
  grid-area: main;
  padding: var(--r-space-6);
  min-height: calc(100vh - 64px);
}

/* When drawer is closed or on mobile, main spans the full width under the bar. */
.r-v2-shell__main--full {
  grid-column: 1 / -1;
}

@media (max-width: 959px) {
  .r-v2-shell {
    grid-template-columns: 1fr;
    grid-template-areas:
      "bar"
      "main";
  }

  .r-v2-shell__brand-chip {
    display: none;
  }
}
</style>
