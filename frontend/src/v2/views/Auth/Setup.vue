<script setup lang="ts">
import { RBtn, RIcon, RSpinner, RSteps } from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { ROUTES } from "@/plugins/router";
import setupApi from "@/services/api/setup";
import type {
  SetupFolderDiscovery,
  SetupFolderDraft,
} from "@/services/api/setup";
import SetupStepAdmin from "@/v2/components/Auth/SetupStepAdmin.vue";
import type { AdminUserDraft } from "@/v2/components/Auth/SetupStepAdmin.vue";
import SetupStepMetadata from "@/v2/components/Auth/SetupStepMetadata.vue";
import SetupStepPlatforms from "@/v2/components/Auth/SetupStepPlatforms.vue";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import { refetchCSRFToken } from "@/v2/data/adapters/legacy/services/api";
import identityApi from "@/v2/data/adapters/legacy/services/api/identity";
import userApi from "@/v2/data/adapters/legacy/services/api/user";
import storeAuth from "@/v2/data/adapters/legacy/stores/auth";
import storeHeartbeat from "@/v2/data/adapters/legacy/stores/heartbeat";

const { t } = useI18n();
const router = useRouter();
const auth = storeAuth();
const heartbeat = storeHeartbeat();
const snackbar = useSnackbar();
const TOTAL_STEPS = 3;
const step = ref<1 | 2 | 3>(1);
const stepDirection = ref<"forward" | "back">("forward");
const discovery = ref<SetupFolderDiscovery | null>(null);
const folderDraft = ref<SetupFolderDraft>({});
const loadingDiscovery = ref(true);
const discoveryError = ref<string | null>(null);
const adminUser = ref<AdminUserDraft>({
  username: "",
  email: "",
  password: "",
  repeatPassword: "",
});
const adminFormValid = ref(false);
const submitting = ref(false);
const createdUserId = ref<number | null>(null);

const stepTitle = computed(
  () =>
    [
      t("setup.folders-title"),
      t("setup.admin-user-step"),
      t("setup.check-metadata-step"),
    ][step.value - 1],
);
const assignments = computed(
  () =>
    discovery.value?.folders
      .map((folder) => ({
        folder_name: folder.name,
        platform_slug: folderDraft.value[folder.name],
      }))
      .filter(
        (item): item is { folder_name: string; platform_slug: string } =>
          typeof item.platform_slug === "string" &&
          item.platform_slug.length > 0,
      ) ?? [],
);
const allFoldersAssigned = computed(() =>
  Boolean(
    discovery.value &&
    assignments.value.length === discovery.value.folders.length,
  ),
);
const canProceed = computed(() => {
  if (step.value === 1)
    return (
      !loadingDiscovery.value &&
      !discoveryError.value &&
      allFoldersAssigned.value
    );
  if (step.value === 2)
    return (
      adminFormValid.value &&
      adminUser.value.username.length > 0 &&
      adminUser.value.password === adminUser.value.repeatPassword
    );
  return true;
});
const isFirstStep = computed(() => step.value === 1);
const isLastStep = computed(() => step.value === TOTAL_STEPS);

async function loadDiscovery() {
  loadingDiscovery.value = true;
  discoveryError.value = null;
  try {
    const { data } = await setupApi.discoverFolders();
    discovery.value = data;
    folderDraft.value = Object.fromEntries(
      data.folders.map((folder) => [folder.name, folder.suggested_platform]),
    );
  } catch (error) {
    console.error("Failed to discover setup folders:", error);
    discoveryError.value = t("setup.loading-folders-failed");
  } finally {
    loadingDiscovery.value = false;
  }
}
function updateDraft(next: SetupFolderDraft) {
  folderDraft.value = next;
}
function prev() {
  if (step.value > 1) {
    stepDirection.value = "back";
    step.value = (step.value - 1) as 1 | 2 | 3;
  }
}
function next() {
  if (!canProceed.value) return;
  if (step.value < TOTAL_STEPS) {
    stepDirection.value = "forward";
    step.value = (step.value + 1) as 1 | 2 | 3;
  } else {
    void finishWizard();
  }
}
async function finishWizard() {
  if (!allFoldersAssigned.value) return;
  submitting.value = true;
  try {
    if (createdUserId.value === null) {
      const { data } = await userApi.createUser({
        username: adminUser.value.username,
        email: adminUser.value.email,
        password: adminUser.value.password,
        role: "admin",
      });
      createdUserId.value = data.id;
    }
    await identityApi.login(adminUser.value.username, adminUser.value.password);
    await refetchCSRFToken();
    await auth.fetchCurrentUser();
    await heartbeat.fetchHeartbeat();
    const { data } = await setupApi.assignFolders(assignments.value);
    if (!data.ready) {
      throw new Error(t("setup.folders-not-ready"));
    }
    await router.push({ name: ROUTES.HOME });
  } catch (error) {
    const detail =
      (error as { response?: { data?: { detail?: string } }; message?: string })
        .response?.data?.detail ?? (error as { message?: string }).message;
    snackbar.error(
      [t("setup.saving-folders-failed"), detail].filter(Boolean).join(": "),
      { icon: "mdi-close-circle" },
    );
  } finally {
    submitting.value = false;
  }
}
onMounted(loadDiscovery);
</script>

<template>
  <div class="r-v2-setup">
    <header class="r-v2-setup__header">
      <RSteps :current="step" :total="TOTAL_STEPS" :direction="stepDirection" />
      <div class="r-v2-setup__title">
        <span>{{
          t("setup.step-of", { current: step, total: TOTAL_STEPS })
        }}</span>
        <h2>{{ stepTitle }}</h2>
      </div>
    </header>
    <div class="r-v2-setup__body">
      <div v-if="loadingDiscovery && step === 1" class="r-v2-setup__loading">
        <RSpinner /><span>{{ t("setup.loading-folders") }}</span>
      </div>
      <div
        v-else-if="discoveryError && step === 1"
        class="r-v2-setup__error"
        role="alert"
      >
        <RIcon icon="mdi-alert-circle-outline" :size="32" /><span>{{
          discoveryError
        }}</span
        ><RBtn
          variant="flat"
          color="primary"
          prepend-icon="mdi-refresh"
          @click="loadDiscovery"
          >{{ t("common.try-again") }}</RBtn
        >
      </div>
      <Transition
        v-else
        mode="out-in"
        :name="
          stepDirection === 'forward'
            ? 'r-v2-setup-step-forward'
            : 'r-v2-setup-step-back'
        "
      >
        <SetupStepPlatforms
          v-if="step === 1 && discovery"
          key="step-1"
          :discovery="discovery"
          :draft="folderDraft"
          :disabled="submitting"
          :submitting="submitting"
          @update:draft="updateDraft"
        />
        <SetupStepAdmin
          v-else-if="step === 2"
          key="step-2"
          v-model="adminUser"
          v-model:valid="adminFormValid"
          @submit="next"
        />
        <SetupStepMetadata v-else key="step-3" />
      </Transition>
    </div>
    <footer class="r-v2-setup__footer">
      <RBtn
        v-if="!isFirstStep"
        variant="text"
        :disabled="submitting"
        prepend-icon="mdi-chevron-left"
        @click="prev"
        >{{ t("setup.previous") }}</RBtn
      >
      <span />
      <RBtn
        variant="flat"
        color="primary"
        :append-icon="isLastStep ? 'mdi-check' : 'mdi-chevron-right'"
        :loading="submitting"
        :disabled="!canProceed || submitting"
        @click="next"
        >{{ isLastStep ? t("setup.finish") : t("setup.next") }}</RBtn
      >
    </footer>
  </div>
</template>

<style scoped>
.r-v2-setup {
  width: 100%;
  max-width: 1080px;
  min-width: 0;
  height: min(86dvh, 880px);
  display: flex;
  flex-direction: column;
  background: var(--r-color-canvas-bg-deep);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  box-shadow: var(--r-elev-4);
  overflow: hidden;
}
.r-v2-setup__header {
  display: grid;
  gap: var(--r-space-4);
  padding: var(--r-space-5) var(--r-space-6) var(--r-space-4);
  border-bottom: 1px solid var(--r-color-border);
}
.r-v2-setup__title {
  text-align: center;
}
.r-v2-setup__title h2 {
  margin: var(--r-space-1) 0 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
}
.r-v2-setup__title span {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
}
.r-v2-setup__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: var(--r-space-5) var(--r-space-6);
}
.r-v2-setup__loading,
.r-v2-setup__error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--r-space-4);
  color: var(--r-color-fg-secondary);
}
.r-v2-setup__footer {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
  padding: var(--r-space-4) var(--r-space-6);
  border-top: 1px solid var(--r-color-border);
}
.r-v2-setup__footer > span {
  flex: 1;
}
</style>
