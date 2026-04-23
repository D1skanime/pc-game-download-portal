<script setup lang="ts">
// ResetForm — username-only form that triggers a password-reset email.
// Emits `done` on success and `cancel` when the user backs out.
import { RBtn, RTextField } from "@v2/lib";
import type { Emitter } from "mitt";
import { inject, ref } from "vue";
import { useI18n } from "vue-i18n";
import identityApi from "@/services/api/identity";
import type { Events } from "@/types/emitter";

defineOptions({ inheritAttrs: false });

const emit = defineEmits<{
  (e: "done"): void;
  (e: "cancel"): void;
}>();

const { t } = useI18n();
const emitter = inject<Emitter<Events>>("emitter");

const forgotUser = ref("");
const sending = ref(false);

async function submit() {
  if (!forgotUser.value) return;
  sending.value = true;
  try {
    await identityApi.requestPasswordReset(forgotUser.value);
    emitter?.emit("snackbarShow", {
      msg: t("login.reset-sent"),
      icon: "mdi-check-circle",
      color: "green",
    });
    forgotUser.value = "";
    emit("done");
  } catch (error) {
    console.error("Error sending reset link: ", error);
    emitter?.emit("snackbarShow", {
      msg: "Could not send reset link",
      icon: "mdi-alert-circle",
      color: "red",
    });
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <form class="r-v2-reset-form" @submit.prevent="submit">
    <RTextField
      v-model="forgotUser"
      :label="t('login.username')"
      type="text"
      variant="underlined"
      prepend-inner-icon="mdi-account"
      :disabled="sending"
    />
    <RBtn
      type="submit"
      variant="flat"
      color="primary"
      block
      prepend-icon="mdi-lock-reset"
      :loading="sending"
      :disabled="sending || !forgotUser"
    >
      {{ t("login.send-reset-link") }}
    </RBtn>
    <RBtn
      variant="text"
      block
      prepend-icon="mdi-chevron-left"
      @click="
        forgotUser = '';
        emit('cancel');
      "
    >
      {{ t("common.cancel") }}
    </RBtn>
  </form>
</template>

<style scoped>
.r-v2-reset-form {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}
</style>
