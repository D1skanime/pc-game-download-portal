<script setup lang="ts">
// UserMenu — the avatar pill in the nav that opens the full settings
// dropdown. Items mirror v1's SettingsDrawer (Profile / User interface /
// Library management / Metadata sources / Client API tokens /
// Administration / Server stats / About / Log out) and are gated by the
// same scope/role checks so unauthorised users don't see options they
// can't use.
import {
  RIcon,
  RMenu,
  RMenuDivider,
  RMenuHeader,
  RMenuItem,
  RMenuPanel,
} from "@v2/lib";
import type { Emitter } from "mitt";
import { getActivePinia, storeToRefs, type StateTree } from "pinia";
import { computed, inject, ref } from "vue";
import { useRouter } from "vue-router";
import { ROUTES } from "@/plugins/router";
import { refetchCSRFToken } from "@/services/api";
import identityApi from "@/services/api/identity";
import storeAuth from "@/stores/auth";
import type { Events } from "@/types/emitter";

defineOptions({ inheritAttrs: false });

const router = useRouter();
const authStore = storeAuth();
const emitter = inject<Emitter<Events>>("emitter");
const { user, scopes } = storeToRefs(authStore);

const open = ref(false);

const userInitials = computed(() => {
  const name = user.value?.username ?? "?";
  return name.slice(0, 2).toUpperCase();
});

const isAdmin = computed(() => user.value?.role === "admin");

function showAbout() {
  open.value = false;
  emitter?.emit("showAboutDialog", null);
}

async function onLogout() {
  open.value = false;
  try {
    const { data } = await identityApi.logout();
    const oidcLogoutUrl = (data as { oidc_logout_url?: string })
      ?.oidc_logout_url;
    if (oidcLogoutUrl) {
      window.location.href = oidcLogoutUrl;
      return;
    }
    await refetchCSRFToken();
    emitter?.emit("snackbarShow", {
      msg: "Logged out",
      icon: "mdi-check-bold",
      color: "green",
    });
    await router.push({ name: ROUTES.LOGIN });
    const pinia = getActivePinia() as
      | { _s?: Map<string, { reset?: () => void } & StateTree> }
      | undefined;
    pinia?._s?.forEach((store) => {
      store.reset?.();
    });
  } catch (error) {
    emitter?.emit("snackbarShow", {
      msg: "Could not log out. Please try again.",
      icon: "mdi-close-circle",
      color: "red",
    });
    console.error("Logout error:", error);
  }
}
</script>

<template>
  <RMenu v-model="open" location="bottom end" :offset="[8, 0]">
    <template #activator="{ props: menuProps }">
      <button
        v-bind="menuProps"
        type="button"
        class="r-v2-user"
        data-user-menu-trigger
        :aria-label="`Account menu for ${user?.username ?? 'Guest'}`"
      >
        <span class="r-v2-user__avatar">{{ userInitials }}</span>
        <span class="r-v2-user__name">
          {{ user?.username ?? "Guest" }}
        </span>
        <RIcon icon="mdi-chevron-down" size="16" class="r-v2-user__chevron" />
      </button>
    </template>

    <RMenuPanel width="260px">
      <RMenuHeader
        compact
        :title="user?.username ?? 'Guest'"
        :subtitle="user?.role ?? ''"
      >
        <template #art>
          <span class="r-v2-user__avatar">{{ userInitials }}</span>
        </template>
      </RMenuHeader>

      <RMenuDivider />

      <!-- Profile — gated by me.write scope (matches v1). -->
      <RMenuItem
        v-if="user?.id && scopes.includes('me.write')"
        :to="`/user/${user.id}`"
        icon="mdi-account-outline"
        label="Profile"
        @click="open = false"
      />
      <RMenuItem
        to="/user-interface"
        icon="mdi-palette-outline"
        label="User interface"
        @click="open = false"
      />
      <RMenuItem
        v-if="scopes.includes('platforms.write')"
        to="/library-management"
        icon="mdi-table-cog"
        label="Library management"
        @click="open = false"
      />
      <RMenuItem
        to="/metadata-sources"
        icon="mdi-database-cog-outline"
        label="Metadata sources"
        @click="open = false"
      />
      <RMenuItem
        v-if="scopes.includes('me.write')"
        to="/client-api-tokens"
        icon="mdi-key-variant"
        label="Client API tokens"
        @click="open = false"
      />
      <RMenuItem
        v-if="scopes.includes('users.write')"
        to="/administration"
        icon="mdi-shield-account-outline"
        label="Administration"
        @click="open = false"
      />
      <RMenuItem
        v-if="isAdmin"
        to="/server-stats"
        icon="mdi-server"
        label="Server stats"
        @click="open = false"
      />
      <RMenuItem
        v-if="isAdmin"
        icon="mdi-help-circle-outline"
        label="About"
        @click="showAbout"
      />

      <RMenuDivider />

      <RMenuItem
        to="/controller-debug"
        icon="mdi-controller"
        label="Controller debug"
        @click="open = false"
      />

      <RMenuDivider />

      <RMenuItem
        icon="mdi-logout"
        variant="danger"
        label="Log out"
        @click="onLogout"
      />
    </RMenuPanel>
  </RMenu>
</template>

<style scoped>
.r-v2-user {
  appearance: none;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.11);
  border-radius: var(--r-radius-pill);
  padding: 3px 12px 3px 3px;
  color: var(--r-color-fg);
  text-decoration: none;
  font-family: inherit;
  cursor: pointer;
  transition: background var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-v2-user:hover {
  background: rgba(255, 255, 255, 0.12);
}

.r-v2-user__chevron {
  color: rgba(255, 255, 255, 0.45);
}

.r-v2-user__avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--r-color-avatar-gradient);
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  color: #fff;
  flex-shrink: 0;
}

.r-v2-user__name {
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
}

@media (max-width: 768px) {
  .r-v2-user__name {
    display: none;
  }
}
</style>
