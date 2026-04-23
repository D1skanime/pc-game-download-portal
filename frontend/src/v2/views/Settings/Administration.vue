<script setup lang="ts">
// Administration — v2 chrome around the v1 UsersTable / TokensTable /
// Tasks. Scope-gated sections mirror the v1 page verbatim.
import { useI18n } from "vue-i18n";
import Tasks from "@/components/Settings/Administration/Tasks.vue";
import TokensTable from "@/components/Settings/Administration/Tokens/TokensTable.vue";
import UsersTable from "@/components/Settings/Administration/Users/UsersTable.vue";
import storeAuth from "@/stores/auth";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";

const { t } = useI18n();
const auth = storeAuth();
</script>

<template>
  <SettingsShell
    :title="t('common.administration')"
    subtitle="Manage users, API tokens, and server tasks."
    icon="mdi-security"
    bare
  >
    <UsersTable />
    <TokensTable v-if="auth.scopes.includes('users.read')" />
    <Tasks v-if="auth.scopes.includes('tasks.run')" />
  </SettingsShell>
</template>
