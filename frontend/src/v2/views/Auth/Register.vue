<script setup lang="ts">
import { RBtn, RCard, RImg, RTextField } from "@v2/lib";
import type { Emitter } from "mitt";
import { inject, onBeforeMount, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import userApi from "@/services/api/user";
import storeUsers from "@/stores/users";
import type { Events } from "@/types/emitter";

const { t } = useI18n();
const emitter = inject<Emitter<Events>>("emitter");
const route = useRoute();
const router = useRouter();
const usersStore = storeUsers();
const token = route.query.token as string;

const username = ref("");
const email = ref("");
const password = ref("");
const visiblePassword = ref(false);
const submitting = ref(false);

async function register() {
  if (!username.value || !email.value || !password.value) return;
  submitting.value = true;
  try {
    await userApi.registerUser(
      username.value,
      email.value,
      password.value,
      token,
    );
    emitter?.emit("snackbarShow", {
      msg: "User registered successfully",
      icon: "mdi-check-circle",
      color: "green",
      timeout: 5000,
    });
    router.push("/login");
  } catch (error: unknown) {
    const { response, message } = error as {
      response?: { data?: { detail?: string } };
      message?: string;
    };
    emitter?.emit("snackbarShow", {
      msg: `Unable to register user: ${response?.data?.detail || message}`,
      icon: "mdi-close-circle",
      color: "red",
      timeout: 5000,
    });
  } finally {
    submitting.value = false;
  }
}

// Redirect if no invite token is present.
onBeforeMount(() => {
  if (!token) router.push("/");
});
</script>

<template>
  <RCard class="r-v2-register" variant="elevated" elevation="4">
    <div class="r-v2-register__inner">
      <RImg
        src="/assets/isotipo.svg"
        :width="80"
        class="r-v2-register__logo"
        alt="RomM"
      />

      <form class="r-v2-register__form" @submit.prevent="register">
        <RTextField
          v-model="username"
          :label="t('settings.username')"
          type="text"
          variant="underlined"
          prepend-inner-icon="mdi-account"
          :rules="usersStore.usernameRules"
          autocomplete="username"
          :disabled="submitting"
        />
        <RTextField
          v-model="email"
          :label="t('settings.email')"
          type="email"
          variant="underlined"
          prepend-inner-icon="mdi-email"
          :rules="usersStore.emailRules"
          autocomplete="email"
          :disabled="submitting"
        />
        <RTextField
          v-model="password"
          :label="t('settings.password')"
          :type="visiblePassword ? 'text' : 'password'"
          variant="underlined"
          prepend-inner-icon="mdi-lock"
          :append-inner-icon="visiblePassword ? 'mdi-eye-off' : 'mdi-eye'"
          :rules="usersStore.passwordRules"
          autocomplete="new-password"
          :disabled="submitting"
          @click:append-inner="visiblePassword = !visiblePassword"
        />
        <RBtn
          type="submit"
          variant="flat"
          color="primary"
          block
          prepend-icon="mdi-account-check"
          :loading="submitting"
          :disabled="submitting || !username || !email || !password"
        >
          {{ t("common.create") }}
        </RBtn>
      </form>

      <div class="r-v2-register__back">
        <a href="/login">{{ t("login.back-to-login") }}</a>
      </div>
    </div>
  </RCard>
</template>

<style scoped>
.r-v2-register {
  width: 100%;
  max-width: 440px;
  border-radius: var(--r-radius-lg) !important;
  box-shadow: var(--r-elev-4) !important;
}

.r-v2-register__inner {
  padding: var(--r-space-8) var(--r-space-6);
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.r-v2-register__logo {
  margin: 0 auto var(--r-space-2);
}

.r-v2-register__form {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.r-v2-register__back {
  text-align: right;
}

.r-v2-register__back a {
  color: var(--r-color-brand-primary-hover);
  font-size: var(--r-font-size-sm);
  text-decoration: none;
}

.r-v2-register__back a:hover {
  text-decoration: underline;
}
</style>
