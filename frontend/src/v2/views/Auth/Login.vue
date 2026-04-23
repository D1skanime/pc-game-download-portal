<script setup lang="ts">
// Login — thin orchestrator. Two mutually exclusive panels gated by
// `forgotMode`, each animated in/out with v-expand-transition (matches
// the v1 behavior). Login + OIDC sit together; the reset form replaces
// them when the user clicks "forgot password".
import { RCard, RDivider, RImg } from "@v2/lib";
import { onMounted, ref } from "vue";
import storeHeartbeat from "@/stores/heartbeat";
import LoginForm from "@/v2/components/Auth/LoginForm.vue";
import OIDCButton from "@/v2/components/Auth/OIDCButton.vue";
import ResetForm from "@/v2/components/Auth/ResetForm.vue";

const heartbeatStore = storeHeartbeat();

const {
  OIDC: {
    ENABLED: oidcEnabled,
    AUTOLOGIN: oidcAutologin,
    PROVIDER: oidcProvider,
  },
  FRONTEND: { DISABLE_USERPASS_LOGIN: loginDisabled },
} = heartbeatStore.value;

const forgotMode = ref(false);
const loginFormRef = ref<InstanceType<typeof LoginForm> | null>(null);
const oidcButtonRef = ref<InstanceType<typeof OIDCButton> | null>(null);

onMounted(() => {
  if (oidcEnabled && oidcAutologin) {
    oidcButtonRef.value?.login();
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

      <!-- Login + OIDC panel -->
      <v-expand-transition>
        <div v-show="!forgotMode" class="r-v2-login__panel">
          <LoginForm
            v-if="!loginDisabled"
            ref="loginFormRef"
            :blocking="oidcButtonRef?.loading ?? false"
            @forgot="forgotMode = true"
          />

          <template v-if="oidcEnabled">
            <RDivider v-if="!loginDisabled" class="r-v2-login__or">
              <span>{{ $t("login.or") }}</span>
            </RDivider>
            <OIDCButton
              ref="oidcButtonRef"
              :provider="oidcProvider"
              :blocking="loginFormRef?.loggingIn ?? false"
            />
          </template>
        </div>
      </v-expand-transition>

      <!-- Forgot-password panel -->
      <v-expand-transition>
        <div v-show="forgotMode && !loginDisabled" class="r-v2-login__panel">
          <ResetForm @done="forgotMode = false" @cancel="forgotMode = false" />
        </div>
      </v-expand-transition>
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

.r-v2-login__panel {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.r-v2-login__or {
  margin: var(--r-space-3) 0;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
</style>
