<script setup lang="ts">
// SettingsSidebar — vertical grouped nav rendered alongside every Settings
// view via <SettingsShell>. Replaces the previous horizontal pill nav.
//
// Groups mirror the v2 user-menu IA so the dropdown and the in-page
// navigator share the same mental model:
//   • Account  — profile + UI prefs
//   • Library  — folder mappings, providers, paired devices
//   • System   — admin + server stats
//   • Tools    — controller debug (developer-leaning, kept here so it
//                inherits the same chrome as everything else)
//
// Each entry is a <router-link>; the active state is driven by Vue
// Router's `router-link-active` (we add `--active` via active-class). Items
// that the user can't reach (insufficient scopes/role) are filtered out.
//
// Responsive: at <1024px the sidebar collapses to a horizontal scrollable
// strip. Group labels are hidden in that mode — items still appear in
// group order so sequence is preserved.
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
const isAdmin = useCan("app.admin");

interface Entry {
  icon: string;
  label: string;
  to: { name: string; params?: Record<string, string | number> };
  visible: boolean;
}

interface Group {
  key: "account" | "library" | "system" | "tools";
  label: string;
  entries: Entry[];
}

const groups = computed<Group[]>(() => {
  const all: Group[] = [
    {
      key: "account",
      label: t("settings.group-account"),
      entries: [
        {
          icon: "mdi-account-circle",
          label: t("common.profile"),
          to: {
            name: ROUTES.USER_PROFILE,
            params: { user: user.value?.id ?? "" },
          },
          visible: scopes.value.includes("me.write"),
        },
        {
          icon: "mdi-palette",
          label: t("common.user-interface"),
          to: { name: ROUTES.USER_INTERFACE },
          visible: true,
        },
      ],
    },
    {
      key: "library",
      label: t("settings.group-library"),
      entries: [
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
      ],
    },
    {
      key: "system",
      label: t("settings.group-system"),
      entries: [
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
          visible: isAdmin.value,
        },
      ],
    },
    {
      key: "tools",
      label: t("settings.group-tools"),
      entries: [
        {
          icon: "mdi-controller",
          label: t("settings.controller-debug"),
          to: { name: ROUTES.CONTROLLER_DEBUG },
          visible: true,
        },
      ],
    },
  ];

  return all
    .map((g) => ({ ...g, entries: g.entries.filter((e) => e.visible) }))
    .filter((g) => g.entries.length > 0);
});
</script>

<template>
  <nav class="r-v2-settings-sidebar" aria-label="Settings sections">
    <div
      v-for="group in groups"
      :key="group.key"
      class="r-v2-settings-sidebar__group"
    >
      <div class="r-v2-settings-sidebar__group-label">
        {{ group.label }}
      </div>
      <ul class="r-v2-settings-sidebar__list">
        <li v-for="entry in group.entries" :key="entry.to.name">
          <router-link
            :to="entry.to"
            class="r-v2-settings-sidebar__item"
            active-class="r-v2-settings-sidebar__item--active"
          >
            <RIcon
              :icon="entry.icon"
              size="16"
              class="r-v2-settings-sidebar__icon"
            />
            <span class="r-v2-settings-sidebar__label">{{ entry.label }}</span>
          </router-link>
        </li>
      </ul>
    </div>
  </nav>
</template>

<style scoped>
.r-v2-settings-sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 14px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  align-self: flex-start;
  position: sticky;
  top: calc(var(--r-nav-h) + 16px);
}

.r-v2-settings-sidebar__group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.r-v2-settings-sidebar__group-label {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 10px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg-muted);
  padding: 0 10px 4px;
}

.r-v2-settings-sidebar__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.r-v2-settings-sidebar__item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 10px;
  border-radius: 9px;
  text-decoration: none;
  color: var(--r-color-fg-secondary);
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
  white-space: nowrap;
}

.r-v2-settings-sidebar__icon {
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-v2-settings-sidebar__item:hover {
  background: var(--r-color-surface);
  color: var(--r-color-fg);
}
.r-v2-settings-sidebar__item:hover .r-v2-settings-sidebar__icon {
  opacity: 1;
}

.r-v2-settings-sidebar__item--active,
.r-v2-settings-sidebar__item--active:hover {
  background: color-mix(in srgb, var(--r-color-brand-primary) 16%, transparent);
  color: var(--r-color-brand-primary);
}
.r-v2-settings-sidebar__item--active .r-v2-settings-sidebar__icon {
  opacity: 1;
}

/* Below 1024px: collapse to a flat horizontal scrollable strip — items
   keep their group order, group labels disappear (they'd duplicate the
   already-visible eyebrow on the content side). */
@media (max-width: 1023px) {
  .r-v2-settings-sidebar {
    flex-direction: row;
    align-items: center;
    gap: 6px;
    padding: 6px;
    overflow-x: auto;
    overflow-y: hidden;
    position: static;
    top: auto;
    scrollbar-width: thin;
  }
  .r-v2-settings-sidebar__group {
    flex-direction: row;
    flex-shrink: 0;
    align-items: center;
    gap: 6px;
  }
  .r-v2-settings-sidebar__group + .r-v2-settings-sidebar__group::before {
    content: "";
    width: 1px;
    height: 18px;
    background: var(--r-color-border);
    margin-right: 4px;
    flex-shrink: 0;
  }
  .r-v2-settings-sidebar__group-label {
    display: none;
  }
  .r-v2-settings-sidebar__list {
    flex-direction: row;
    gap: 4px;
  }
  .r-v2-settings-sidebar__item {
    padding: 8px 12px;
    border-radius: var(--r-radius-pill);
  }
  .r-v2-settings-sidebar__label {
    white-space: nowrap;
  }
}
</style>
