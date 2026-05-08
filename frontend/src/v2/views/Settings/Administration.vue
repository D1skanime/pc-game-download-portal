<script setup lang="ts">
// Administration — v2-native rewrite. Composes the three section
// composites (Users + AdminTokens + Tasks) and mounts the v2 user
// dialogs (create / edit / invite). DeleteUser is handled in-line via
// useConfirm in UsersSection — no dedicated dialog file.
import storeAuth from "@/stores/auth";
import AdminTokensSection from "@/v2/components/Settings/AdminTokensSection.vue";
import CreateUserDialog from "@/v2/components/Settings/CreateUserDialog.vue";
import EditUserDialog from "@/v2/components/Settings/EditUserDialog.vue";
import InviteLinkDialog from "@/v2/components/Settings/InviteLinkDialog.vue";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";
import TasksSection from "@/v2/components/Settings/TasksSection.vue";
import UsersSection from "@/v2/components/Settings/UsersSection.vue";

const auth = storeAuth();
</script>

<template>
  <SettingsShell bare>
    <UsersSection />
    <AdminTokensSection v-if="auth.scopes.includes('users.read')" />
    <TasksSection v-if="auth.scopes.includes('tasks.run')" />

    <CreateUserDialog />
    <EditUserDialog />
    <InviteLinkDialog />
  </SettingsShell>
</template>
