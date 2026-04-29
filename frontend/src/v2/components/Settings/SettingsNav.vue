<script setup lang="ts">
// SettingsNav — secondary pill nav for the Settings suite. Each item is
// scope-gated using the same matrix as the v1 SettingsDrawer so users see
// exactly the sections they have permission to open. Mirrored across all
// /user-* /library-management /metadata-sources /administration etc.
// views via the shared <SettingsShell>.
import { RIcon } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { ROUTES } from "@/plugins/router";
import storeAuth from "@/stores/auth";
import { useCan } from "@/v2/composables/useCan";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const auth = storeAuth();
const { user, scopes } = storeToRefs(auth);
const canSeeServerStats = useCan("app.admin");

type Entry = {
  icon: string;
  label: string;
  to: { name: string; params?: Record<string, string | number> };
  visible: boolean;
};

const entries = computed<Entry[]>(() => [
  {
    icon: "mdi-account-circle",
    label: t("common.user-profile"),
    to: { name: ROUTES.USER_PROFILE, params: { user: user.value?.id ?? "" } },
    visible: scopes.value.includes("me.write"),
  },
  {
    icon: "mdi-palette",
    label: t("common.user-interface"),
    to: { name: ROUTES.USER_INTERFACE },
    visible: true,
  },
  {
    icon: "mdi-folder-cog",
    label: t("common.library-management"),
    to: { name: ROUTES.LIBRARY_MANAGEMENT },
    visible: scopes.value.includes("platforms.write"),
  },
  {
    icon: "mdi-database-search",
    label: t("scan.metadata-sources"),
    to: { name: ROUTES.METADATA_SOURCES },
    visible: scopes.value.includes("me.write"),
  },
  {
    icon: "mdi-key-variant",
    label: t("settings.client-api-tokens"),
    to: { name: ROUTES.CLIENT_API_TOKENS },
    visible: scopes.value.includes("me.write"),
  },
  {
    icon: "mdi-security",
    label: t("common.administration"),
    to: { name: ROUTES.ADMINISTRATION },
    visible: scopes.value.includes("users.write"),
  },
  {
    icon: "mdi-chart-bar",
    label: t("common.server-stats"),
    to: { name: ROUTES.SERVER_STATS },
    visible: canSeeServerStats.value,
  },
]);
</script>

<template>
  <nav class="r-v2-settings-nav" aria-label="Settings sections">
    <template v-for="entry in entries" :key="entry.to.name">
      <router-link
        v-if="entry.visible"
        :to="entry.to"
        class="r-v2-settings-nav__link"
        active-class="r-v2-settings-nav__link--active"
      >
        <RIcon :icon="entry.icon" size="16" />
        <span>{{ entry.label }}</span>
      </router-link>
    </template>
  </nav>
</template>

<style scoped>
.r-v2-settings-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.r-v2-settings-nav__link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: var(--r-radius-pill);
  text-decoration: none;
  color: var(--r-color-fg-secondary);
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
  white-space: nowrap;
}
.r-v2-settings-nav__link:hover {
  background: var(--r-color-surface);
  color: var(--r-color-fg);
}
.r-v2-settings-nav__link--active {
  background: color-mix(in srgb, var(--r-color-brand-primary) 18%, transparent);
  color: var(--r-color-brand-primary);
}
</style>
