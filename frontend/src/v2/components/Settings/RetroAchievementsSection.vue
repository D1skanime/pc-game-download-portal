<script setup lang="ts">
// RetroAchievementsSection — v2-native rebuild of the v1
// `Settings/UserProfile/RetroAchievements.vue`. Lets the user link/edit
// their RA username and trigger an incremental re-sync. Uses the mock's
// section pattern (header bar + bordered body + button row).
import { RBtn, RTextField } from "@v2/lib";
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import userApi from "@/services/api/user";
import storeAuth from "@/stores/auth";
import SettingsSection from "@/v2/components/Settings/SettingsSection.vue";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const auth = storeAuth();
const snackbar = useSnackbar();

const username = ref(auth.user?.ra_username ?? "");
const syncing = ref(false);
const submitting = ref(false);

watch(
  () => auth.user?.ra_username,
  (next) => {
    username.value = next ?? "";
  },
);

async function refreshRetroAchievements(incremental = true) {
  if (!auth.user) return;
  syncing.value = true;
  try {
    await userApi.refreshRetroAchievements({
      id: auth.user.id,
      incremental,
    });
    snackbar.success("RetroAchievements profile synced", {
      icon: "mdi-check-bold",
    });
  } catch (error) {
    console.error(error);
    snackbar.error("Unable to sync your RetroAchievements profile.", {
      icon: "mdi-close-circle",
    });
  } finally {
    syncing.value = false;
  }
}

async function submitRACredentials() {
  if (!auth.user) return;
  submitting.value = true;
  try {
    await userApi.updateUser({
      id: auth.user.id,
      ra_username: username.value,
    });
    snackbar.success("Updated RetroAchievements settings", {
      icon: "mdi-check-bold",
    });
    // Best-effort full sync of the newly linked profile.
    void refreshRetroAchievements(false);
  } catch (error) {
    console.error(error);
    snackbar.error("Unable to update your RetroAchievements settings.", {
      icon: "mdi-close-circle",
    });
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <SettingsSection title="RetroAchievements" icon="mdi-trophy">
    <div class="r-v2-ra__field">
      <RTextField
        v-model="username"
        variant="outlined"
        :label="t('settings.username')"
        prepend-inner-icon="mdi-account"
        hide-details
      />
    </div>
    <div class="r-v2-ra__actions">
      <RBtn
        variant="flat"
        color="primary"
        :loading="submitting"
        :disabled="!username || syncing"
        prepend-icon="mdi-check"
        @click="submitRACredentials"
      >
        {{ t("common.apply") }}
      </RBtn>
      <RBtn
        variant="text"
        :loading="syncing"
        :disabled="!auth.user?.ra_username"
        prepend-icon="mdi-sync"
        @click="refreshRetroAchievements(true)"
      >
        {{ t("common.sync") }}
      </RBtn>
    </div>
  </SettingsSection>
</template>

<style scoped>
.r-v2-ra__field {
  padding: 14px 16px;
}

.r-v2-ra__actions {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--r-color-border);
}
</style>
