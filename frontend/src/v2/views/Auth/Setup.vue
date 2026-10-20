<script setup lang="ts">
import { RAlert, RBtn, RIcon, RSpinner, RSteps } from "@v2/lib";
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ROUTES } from "@/plugins/router";
import SetupStepAdmin from "@/v2/components/Auth/SetupStepAdmin.vue";
import type { AdminUserDraft } from "@/v2/components/Auth/SetupStepAdmin.vue";
import SetupStepMetadata from "@/v2/components/Auth/SetupStepMetadata.vue";
import SetupStepPlatforms from "@/v2/components/Auth/SetupStepPlatforms.vue";
import { useSetupRecovery } from "@/v2/composables/useSetupRecovery";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import setupApi from "@/v2/data/adapters/legacy/services/api/setup";
import type {
  SetupFolderDiscovery,
  SetupFolderDraft,
} from "@/v2/data/adapters/legacy/services/api/setup";

const { t } = useI18n();
const recovery = useSetupRecovery();
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
const { complete, cause, loginRequired, enrolled } = recovery;
watch(loginRequired, (required) => {
  if (required) {
    adminUser.value.password = "";
    adminUser.value.repeatPassword = "";
  }
});

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
      enrolled.value ||
      (adminFormValid.value &&
        adminUser.value.username.length > 0 &&
        adminUser.value.password === adminUser.value.repeatPassword)
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
    folderDraft.value = recovery.mergeDraft(
      Object.fromEntries(
        data.folders.map((folder) => [
          folder.name,
          folderDraft.value[folder.name] ?? folder.suggested_platform,
        ]),
      ),
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
    step.value = (step.value === 3 && enrolled.value ? 1 : step.value - 1) as
      1 | 2 | 3;
  }
}
function next() {
  if (!canProceed.value) return;
  if (step.value < TOTAL_STEPS) {
    stepDirection.value = "forward";
    step.value = (step.value === 1 && enrolled.value ? 3 : step.value + 1) as
      1 | 2 | 3;
  } else {
    void finishWizard();
  }
}
async function finishWizard() {
  if (!allFoldersAssigned.value || submitting.value) return;
  submitting.value = true;
  try {
    await recovery.finish(adminUser.value, assignments.value);
    folderDraft.value = recovery.mergeDraft(folderDraft.value);
    if (cause.value) snackbar.error(t("setup.recovery-failed"));
  } finally {
    submitting.value = false;
  }
}
async function retryRecovery() {
  await recovery.retryCheck();
  await loadDiscovery();
}
onMounted(async () => {
  await recovery.retryCheck();
  await loadDiscovery();
});
</script>

<template>
  <div class="r-v2-setup">
    <section
      v-if="complete"
      class="pa-6 d-flex flex-column ga-4"
      role="status"
      aria-live="polite"
    >
      <h2>{{ t("setup.recovery-complete") }}</h2>
      <p>{{ t("setup.recovery-read-only") }}</p>
      <RBtn color="primary" :to="{ name: ROUTES.SCAN }">{{
        t("setup.recovery-start-scan")
      }}</RBtn>
    </section>
    <template v-else>
      <RAlert v-if="loginRequired" type="info" role="status">
        {{ t("setup.recovery-login") }}
        <RBtn :to="{ name: ROUTES.LOGIN, query: { next: '/setup' } }">{{
          t("setup.recovery-login-action")
        }}</RBtn>
      </RAlert>
      <RAlert v-if="cause" type="warning" role="alert">
        {{
          t(
            cause.startsWith("root_")
              ? "setup.recovery-root"
              : "setup.recovery-failed",
          )
        }}
        <RBtn :loading="recovery.busy.value" @click="retryRecovery">{{
          t("setup.recovery-retry")
        }}</RBtn>
      </RAlert>
      <header class="r-v2-setup__header">
        <RSteps
          :current="step"
          :total="TOTAL_STEPS"
          :direction="stepDirection"
        />
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
          size="large"
          v-if="!isFirstStep"
          variant="text"
          :disabled="submitting"
          prepend-icon="mdi-chevron-left"
          @click="prev"
          >{{ t("setup.previous") }}</RBtn
        >
        <span />
        <RBtn
          size="large"
          variant="flat"
          color="primary"
          :append-icon="isLastStep ? 'mdi-check' : 'mdi-chevron-right'"
          :loading="submitting"
          :disabled="!canProceed || submitting || loginRequired"
          @click="next"
          >{{ isLastStep ? t("setup.finish") : t("setup.next") }}</RBtn
        >
      </footer>
    </template>
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
