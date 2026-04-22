<script setup lang="ts">
import { RAlert, RBtn, RCard, RImg, RTextField } from "@v2/lib";
import type { Emitter } from "mitt";
import { computed, inject, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { refetchCSRFToken } from "@/services/api";
import identityApi from "@/services/api/identity";
import storeAuth from "@/stores/auth";
import type { Events } from "@/types/emitter";

const { t } = useI18n();
const authStore = storeAuth();
const emitter = inject<Emitter<Events>>("emitter");
const route = useRoute();
const router = useRouter();
const token = route.query.token as string;

const newPassword = ref("");
const confirmPassword = ref("");
const visibleNewPassword = ref(false);
const visibleConfirmPassword = ref(false);
const submitting = ref(false);

const passwordsMismatch = computed(
  () =>
    newPassword.value.length > 0 && newPassword.value !== confirmPassword.value,
);

async function resetPassword() {
  if (passwordsMismatch.value || !newPassword.value) return;
  submitting.value = true;
  try {
    await identityApi.resetPassword(token, newPassword.value);
    await refetchCSRFToken();
    try {
      await authStore.fetchCurrentUser();
    } catch (error) {
      console.error("Error setting a new password: ", error);
    }
    const params = new URLSearchParams(window.location.search);
    router.push(params.get("next") ?? "/");
  } catch (err: unknown) {
    const { response, message } = err as {
      response?: {
        data?: { detail?: string };
        statusText?: string;
        status?: number;
      };
      message?: string;
    };
    const errorMessage =
      response?.data?.detail ||
      message ||
      response?.statusText ||
      "Reset failed";
    emitter?.emit("snackbarShow", {
      msg: `Unable to reset password: ${errorMessage}`,
      icon: "mdi-close-circle",
      color: "red",
    });
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <RCard class="r-v2-reset" variant="elevated" elevation="4">
    <div class="r-v2-reset__inner">
      <RImg
        src="/assets/isotipo.svg"
        :width="80"
        class="r-v2-reset__logo"
        alt="RomM"
      />

      <form class="r-v2-reset__form" @submit.prevent="resetPassword">
        <RTextField
          v-model="newPassword"
          :label="t('login.new-password')"
          :type="visibleNewPassword ? 'text' : 'password'"
          variant="underlined"
          prepend-inner-icon="mdi-lock"
          :append-inner-icon="visibleNewPassword ? 'mdi-eye-off' : 'mdi-eye'"
          autocomplete="new-password"
          :disabled="submitting"
          @click:append-inner="visibleNewPassword = !visibleNewPassword"
        />
        <RTextField
          v-model="confirmPassword"
          :label="t('login.confirm-new-password')"
          :type="visibleConfirmPassword ? 'text' : 'password'"
          variant="underlined"
          prepend-inner-icon="mdi-lock-check"
          :append-inner-icon="
            visibleConfirmPassword ? 'mdi-eye-off' : 'mdi-eye'
          "
          autocomplete="new-password"
          :disabled="submitting"
          @click:append-inner="visibleConfirmPassword = !visibleConfirmPassword"
        />

        <RAlert
          v-if="passwordsMismatch"
          type="error"
          density="compact"
          :text="t('login.passwords-do-not-match', 'Passwords do not match')"
        />

        <RBtn
          type="submit"
          variant="flat"
          color="primary"
          block
          prepend-icon="mdi-send"
          :loading="submitting"
          :disabled="
            submitting || passwordsMismatch || !newPassword || !confirmPassword
          "
        >
          {{ t("login.reset-password") }}
        </RBtn>
      </form>

      <div class="r-v2-reset__back">
        <a href="/login">{{ t("login.back-to-login") }}</a>
      </div>
    </div>
  </RCard>
</template>

<style scoped>
.r-v2-reset {
  width: 100%;
  max-width: 440px;
  border-radius: var(--r-radius-lg) !important;
  box-shadow: var(--r-elev-4) !important;
}

.r-v2-reset__inner {
  padding: var(--r-space-8) var(--r-space-6);
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.r-v2-reset__logo {
  margin: 0 auto var(--r-space-2);
}

.r-v2-reset__form {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.r-v2-reset__back {
  text-align: right;
}

.r-v2-reset__back a {
  color: var(--r-color-brand-primary-hover);
  font-size: var(--r-font-size-sm);
  text-decoration: none;
}

.r-v2-reset__back a:hover {
  text-decoration: underline;
}
</style>
