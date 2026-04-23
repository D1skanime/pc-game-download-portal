<script setup lang="ts">
// ClientApiTokens — v2 chrome around the v1 ClientTokensTable. The table
// itself handles creation, rotation, and revocation flows via its own
// dialogs; we just provide the settings page chrome.
import { useI18n } from "vue-i18n";
import ClientTokensTable from "@/components/Settings/ClientApiTokens/ClientTokensTable.vue";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";

const { t } = useI18n();
</script>

<template>
  <SettingsShell
    :title="t('settings.client-api-tokens')"
    subtitle="Tokens paired with external devices (handhelds, emulators). Rotate or revoke at any time."
    icon="mdi-key-variant"
    bare
  >
    <ClientTokensTable />
  </SettingsShell>
</template>
