<script setup lang="ts">
import { RBtn, RCard, RDivider, RIcon, RImg, RTextField } from "@v2/lib";
import type { Emitter } from "mitt";
import { inject, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { refetchCSRFToken } from "@/services/api";
import identityApi from "@/services/api/identity";
import storeAuth from "@/stores/auth";
import storeHeartbeat from "@/stores/heartbeat";
import type { Events } from "@/types/emitter";

const { t } = useI18n();
const heartbeatStore = storeHeartbeat();
const authStore = storeAuth();
const emitter = inject<Emitter<Events>>("emitter");
const router = useRouter();

const username = ref("");
const password = ref("");
const visiblePassword = ref(false);
const loggingIn = ref(false);
const loggingInOIDC = ref(false);
const forgotMode = ref(false);
const forgotUser = ref("");
const sendingReset = ref(false);

const {
  OIDC: {
    ENABLED: oidcEnabled,
    AUTOLOGIN: oidcAutologin,
    PROVIDER: oidcProvider,
  },
  FRONTEND: { DISABLE_USERPASS_LOGIN: loginDisabled },
} = heartbeatStore.value;

async function login() {
  if (!username.value || !password.value) return;
  loggingIn.value = true;
  try {
    await identityApi.login(username.value, password.value);
    await refetchCSRFToken();
    try {
      await authStore.fetchCurrentUser();
    } catch (userError) {
      console.error("Error loading user: ", userError);
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
      "Login failed";
    emitter?.emit("snackbarShow", {
      msg: `Unable to login: ${errorMessage}`,
      icon: "mdi-close-circle",
      color: "red",
    });
    console.error(
      `[${response?.status} ${response?.statusText}] ${errorMessage}`,
    );
  } finally {
    loggingIn.value = false;
  }
}

async function sendReset() {
  if (!forgotUser.value) return;
  sendingReset.value = true;
  try {
    await identityApi.requestPasswordReset(forgotUser.value);
    emitter?.emit("snackbarShow", {
      msg: t("login.reset-sent"),
      icon: "mdi-check-circle",
      color: "green",
    });
    forgotMode.value = false;
    forgotUser.value = "";
  } catch (error) {
    console.error("Error sending reset link: ", error);
    emitter?.emit("snackbarShow", {
      msg: "Could not send reset link",
      icon: "mdi-alert-circle",
      color: "red",
    });
  } finally {
    sendingReset.value = false;
  }
}

function loginOIDC() {
  if (loggingInOIDC.value) return;
  loggingInOIDC.value = true;
  window.open("/api/login/openid", "_self");
}

onMounted(() => {
  if (oidcEnabled && oidcAutologin) {
    loginOIDC();
  }
});
</script>

<template>
  <RCard class="r-v2-login" variant="elevated" elevation="4">
    <div class="r-v2-login__inner">
      <RImg
        src="/assets/isotipo.svg"
        :width="80"
        class="r-v2-login__logo"
        alt="RomM"
      />

      <!-- Login form -->
      <form
        v-if="!forgotMode && !loginDisabled"
        class="r-v2-login__form"
        @submit.prevent="login"
      >
        <RTextField
          v-model="username"
          :label="t('login.username')"
          type="text"
          variant="underlined"
          autocomplete="username"
          name="username"
          prepend-inner-icon="mdi-account"
          :disabled="loggingIn"
        />
        <RTextField
          v-model="password"
          :label="t('login.password')"
          :type="visiblePassword ? 'text' : 'password'"
          variant="underlined"
          autocomplete="current-password"
          name="password"
          prepend-inner-icon="mdi-lock"
          :append-inner-icon="visiblePassword ? 'mdi-eye-off' : 'mdi-eye'"
          :disabled="loggingIn"
          @click:append-inner="visiblePassword = !visiblePassword"
        />
        <RBtn
          type="submit"
          variant="flat"
          color="primary"
          block
          prepend-icon="mdi-login"
          :loading="loggingIn"
          :disabled="loggingIn || loggingInOIDC || !username || !password"
        >
          {{ t("login.login") }}
        </RBtn>
      </form>

      <!-- OIDC -->
      <template v-if="oidcEnabled">
        <RDivider v-if="!loginDisabled" class="r-v2-login__or">
          <span>{{ t("login.or") }}</span>
        </RDivider>
        <RBtn
          variant="outlined"
          block
          :disabled="loggingInOIDC || loggingIn"
          :loading="loggingInOIDC"
          @click="loginOIDC"
        >
          <template v-if="oidcProvider" #prepend>
            <RIcon size="20">
              <RImg
                :src="`/assets/dashboard-icons/${oidcProvider
                  .toLowerCase()
                  .replace(/ /g, '-')}.png`"
              >
                <template #error>
                  <RIcon icon="mdi-key" size="20" />
                </template>
              </RImg>
            </RIcon>
          </template>
          {{ t("login.login-oidc", { oidc: oidcProvider || "OIDC" }) }}
        </RBtn>
      </template>

      <!-- Forgot-password link -->
      <div v-if="!forgotMode && !loginDisabled" class="r-v2-login__forgot">
        <a href="#" @click.prevent="forgotMode = true">
          {{ t("login.forgot-password") }}
        </a>
      </div>

      <!-- Reset form -->
      <form
        v-if="forgotMode && !loginDisabled"
        class="r-v2-login__form"
        @submit.prevent="sendReset"
      >
        <RTextField
          v-model="forgotUser"
          :label="t('login.username')"
          type="text"
          variant="underlined"
          prepend-inner-icon="mdi-account"
          :disabled="sendingReset"
        />
        <RBtn
          type="submit"
          variant="flat"
          color="primary"
          block
          prepend-icon="mdi-lock-reset"
          :loading="sendingReset"
          :disabled="sendingReset || !forgotUser"
        >
          {{ t("login.send-reset-link") }}
        </RBtn>
        <RBtn
          variant="text"
          block
          prepend-icon="mdi-chevron-left"
          @click="
            forgotMode = false;
            forgotUser = '';
          "
        >
          {{ t("common.cancel") }}
        </RBtn>
      </form>
    </div>
  </RCard>
</template>

<style scoped>
.r-v2-login {
  width: 100%;
  max-width: 440px;
  border-radius: var(--r-radius-lg) !important;
  box-shadow: var(--r-elev-4) !important;
}

.r-v2-login__inner {
  padding: var(--r-space-8) var(--r-space-6);
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.r-v2-login__logo {
  margin: 0 auto var(--r-space-2);
  filter: drop-shadow(0 0 16px rgba(139, 116, 232, 0.3));
}

.r-v2-login__form {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.r-v2-login__or {
  margin: var(--r-space-3) 0;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.r-v2-login__forgot {
  text-align: right;
  margin-top: var(--r-space-2);
}

.r-v2-login__forgot a {
  color: var(--r-color-brand-primary-hover);
  font-size: var(--r-font-size-sm);
  text-decoration: none;
  border-radius: var(--r-radius-sm);
}

.r-v2-login__forgot a:hover {
  text-decoration: underline;
}
</style>
