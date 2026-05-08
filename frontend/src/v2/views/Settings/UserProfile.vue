<script setup lang="ts">
// UserProfile — v2-native rewrite. Mirrors the mock layout:
//   • page title
//   • flush identity row (avatar + username + role)
//   • Account Details section (form + apply button row)
//   • RetroAchievements section (own component)
import { RBtn, RIcon, RSelect, RTextField } from "@v2/lib";
import type { Emitter } from "mitt";
import { storeToRefs } from "pinia";
import { computed, inject, onMounted, onUnmounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import userApi from "@/services/api/user";
import storeAuth from "@/stores/auth";
import storeUsers from "@/stores/users";
import type { Events } from "@/types/emitter";
import type { UserItem } from "@/types/user";
import { defaultAvatarPath, getRoleIcon } from "@/utils";
import RetroAchievementsSection from "@/v2/components/Settings/RetroAchievementsSection.vue";
import SettingsSection from "@/v2/components/Settings/SettingsSection.vue";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";
import { useSnackbar } from "@/v2/composables/useSnackbar";

const { t } = useI18n();
const auth = storeAuth();
const { user } = storeToRefs(auth);
const userToEdit = ref<UserItem | null>(null);
const usersStore = storeUsers();
const imagePreviewUrl = ref<string | undefined>("");
const emitter = inject<Emitter<Events>>("emitter");
const snackbar = useSnackbar();
const fileInputRef = ref<HTMLInputElement | null>(null);
const submitting = ref(false);

const roleItems = computed(() =>
  ["viewer", "editor", "admin"].map((role) => ({
    title: role.charAt(0).toUpperCase() + role.slice(1),
    value: role,
  })),
);

const avatarSrc = computed(() => {
  if (imagePreviewUrl.value) return imagePreviewUrl.value;
  if (userToEdit.value?.avatar_path) {
    return `/assets/romm/assets/${userToEdit.value.avatar_path}?ts=${userToEdit.value.updated_at}`;
  }
  return defaultAvatarPath;
});

function triggerFileInput() {
  fileInputRef.value?.click();
}

function previewImage(event: Event) {
  const input = event.target as HTMLInputElement;
  if (!input.files || !input.files[0] || !userToEdit.value) return;

  const file = input.files[0];
  userToEdit.value.avatar = file;

  const reader = new FileReader();
  reader.onload = () => {
    imagePreviewUrl.value = reader.result?.toString();
  };
  reader.readAsDataURL(file);
}

async function editUser() {
  if (!userToEdit.value) return;
  submitting.value = true;
  try {
    const { data } = await userApi.updateUser(userToEdit.value);
    snackbar.success(`User ${data.username} updated successfully`, {
      icon: "mdi-check-bold",
      timeout: 5000,
    });
    usersStore.update(data);
    if (data.id == auth.user?.id) {
      auth.setCurrentUser(data);
    }
    emitter?.emit("refreshDrawer", null);
  } catch (err) {
    const error = err as {
      response?: { data?: { detail?: string }; statusText?: string };
      message?: string;
    };
    snackbar.error(
      `Unable to edit user: ${
        error?.response?.data?.detail ||
        error?.response?.statusText ||
        error?.message
      }`,
      { icon: "mdi-close-circle", timeout: 5000 },
    );
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  userToEdit.value = { ...user.value, password: "", avatar: undefined };
  if (userToEdit.value) {
    document.title = `${userToEdit.value.username} | Profile`;
  }
});

onUnmounted(() => {
  imagePreviewUrl.value = "";
});
</script>

<template>
  <SettingsShell bare>
    <template v-if="userToEdit">
      <h1 class="r-v2-settings__page-title">
        {{ t("common.profile") }}
      </h1>

      <!-- Flush identity row — avatar + username + role. No card. -->
      <div class="r-v2-profile__identity-row">
        <button
          type="button"
          class="r-v2-profile__avatar"
          :aria-label="t('settings.change-avatar', 'Change avatar')"
          @click="triggerFileInput"
        >
          <img :src="avatarSrc" :alt="userToEdit.username" />
          <span class="r-v2-profile__avatar-edit">
            <RIcon icon="mdi-pencil" size="18" />
          </span>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          class="r-v2-profile__file"
          :aria-label="t('settings.change-avatar', 'Change avatar')"
          @change="previewImage"
        />
        <div class="r-v2-profile__identity">
          <span class="r-v2-profile__username">
            {{ userToEdit.username }}
          </span>
          <span class="r-v2-profile__role">
            <RIcon :icon="getRoleIcon(userToEdit.role)" size="12" />
            {{ userToEdit.role }}
          </span>
        </div>
      </div>

      <!-- Account details -->
      <SettingsSection
        :title="t('settings.account-details', 'Account details')"
        icon="mdi-account"
      >
        <div class="r-v2-profile__field">
          <RTextField
            v-model="userToEdit.username"
            variant="outlined"
            :label="t('settings.username')"
            :rules="usersStore.usernameRules"
            required
            clearable
          />
        </div>
        <div class="r-v2-profile__field">
          <RTextField
            v-model="userToEdit.password"
            variant="outlined"
            :label="t('settings.password')"
            type="password"
            clearable
          />
        </div>
        <div class="r-v2-profile__field">
          <RTextField
            v-model="userToEdit.email"
            variant="outlined"
            :label="t('settings.email')"
            :rules="usersStore.emailRules"
            required
            clearable
          />
        </div>
        <div class="r-v2-profile__field">
          <RSelect
            v-model="userToEdit.role"
            variant="outlined"
            :items="roleItems"
            :label="t('settings.role')"
            required
            hide-details
          >
            <template #selection="{ item }">
              <div class="r-v2-profile__role-line">
                <RIcon :icon="getRoleIcon(item.value)" size="16" />
                {{ item.title }}
              </div>
            </template>
            <template #item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps" :title="item.title">
                <template #prepend>
                  <RIcon :icon="getRoleIcon(item.value)" size="16" />
                </template>
              </v-list-item>
            </template>
          </RSelect>
        </div>
        <div class="r-v2-profile__actions">
          <RBtn
            variant="flat"
            color="primary"
            :loading="submitting"
            :disabled="!userToEdit.username"
            prepend-icon="mdi-check"
            @click="editUser"
          >
            {{ t("common.apply") }}
          </RBtn>
        </div>
      </SettingsSection>

      <RetroAchievementsSection />
    </template>
  </SettingsShell>
</template>

<style scoped>
.r-v2-settings__page-title {
  margin: 0 0 20px;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--r-color-fg);
}

/* Flush identity row — avatar + username + role. No card chrome. */
.r-v2-profile__identity-row {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 28px;
}

.r-v2-profile__avatar {
  position: relative;
  appearance: none;
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}
.r-v2-profile__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.r-v2-profile__avatar-edit {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, black 50%, transparent);
  color: var(--r-color-overlay-fg);
  opacity: 0;
  transition: opacity var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-profile__avatar:hover .r-v2-profile__avatar-edit,
.r-v2-profile__avatar:focus-visible .r-v2-profile__avatar-edit {
  opacity: 1;
}

.r-v2-profile__file {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.r-v2-profile__identity {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.r-v2-profile__username {
  font-size: 18px;
  font-weight: var(--r-font-weight-bold);
  color: var(--r-color-fg);
  line-height: 1.2;
}

.r-v2-profile__role {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--r-color-fg-muted);
  text-transform: capitalize;
}

/* Field rows inside the section body — hairline-divided, padding mirrors
   the mock's settings-field. */
.r-v2-profile__field {
  padding: 14px 16px;
  border-bottom: 1px solid var(--r-color-border);
}
.r-v2-profile__field:last-of-type {
  border-bottom: none;
}

.r-v2-profile__actions {
  display: flex;
  justify-content: flex-start;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--r-color-border);
}

.r-v2-profile__role-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: capitalize;
}
</style>
