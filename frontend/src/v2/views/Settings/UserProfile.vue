<script setup lang="ts">
// UserProfile — v2-native rewrite. Same contract as v1: hero (avatar +
// username + role), Account details form, and the RetroAchievements
// section (reused as-is from v1 for this wave).
import { RBtn, RIcon, RSelect, RTextField } from "@v2/lib";
import type { Emitter } from "mitt";
import { storeToRefs } from "pinia";
import { computed, inject, onMounted, onUnmounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import RetroAchievements from "@/components/Settings/UserProfile/RetroAchievements.vue";
import userApi from "@/services/api/user";
import storeAuth from "@/stores/auth";
import storeUsers from "@/stores/users";
import type { Events } from "@/types/emitter";
import type { UserItem } from "@/types/user";
import { defaultAvatarPath, getRoleIcon } from "@/utils";
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

function editUser() {
  if (!userToEdit.value) return;

  userApi
    .updateUser(userToEdit.value)
    .then(({ data }) => {
      snackbar.success(`User ${data.username} updated successfully`, {
        icon: "mdi-check-bold",
        timeout: 5000,
      });
      usersStore.update(data);
      if (data.id == auth.user?.id) {
        auth.setCurrentUser(data);
      }
    })
    .catch(({ response, message }) => {
      snackbar.error(
        `Unable to edit user: ${
          response?.data?.detail || response?.statusText || message
        }`,
        { icon: "mdi-close-circle", timeout: 5000 },
      );
    });

  emitter?.emit("refreshDrawer", null);
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
  <SettingsShell
    :title="t('common.user-profile')"
    subtitle="Manage your account details, avatar, and linked services."
    icon="mdi-account-circle"
    bare
  >
    <template v-if="userToEdit">
      <!-- Identity hero -->
      <div class="r-v2-profile__hero">
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
          <h2 class="r-v2-profile__username">
            {{ userToEdit.username }}
          </h2>
          <span class="r-v2-profile__role">
            <RIcon :icon="getRoleIcon(userToEdit.role)" size="14" />
            {{ userToEdit.role }}
          </span>
        </div>
      </div>

      <!-- Account details -->
      <section class="r-v2-profile__section">
        <header class="r-v2-profile__section-head">
          <RIcon icon="mdi-account" size="16" />
          <h2>{{ t("settings.account-details", "Account details") }}</h2>
        </header>
        <div class="r-v2-profile__form">
          <RTextField
            v-model="userToEdit.username"
            variant="outlined"
            :label="t('settings.username')"
            :rules="usersStore.usernameRules"
            required
            clearable
          />
          <RTextField
            v-model="userToEdit.password"
            variant="outlined"
            :label="t('settings.password')"
            type="password"
            clearable
          />
          <RTextField
            v-model="userToEdit.email"
            variant="outlined"
            :label="t('settings.email')"
            :rules="usersStore.emailRules"
            required
            clearable
          />
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
          <div class="r-v2-profile__actions">
            <RBtn
              variant="flat"
              color="primary"
              :disabled="!userToEdit.username"
              prepend-icon="mdi-check"
              @click="editUser"
            >
              {{ t("common.apply") }}
            </RBtn>
          </div>
        </div>
      </section>

      <!-- RetroAchievements (reused v1 primitive). -->
      <section class="r-v2-profile__section r-v2-profile__section--legacy">
        <RetroAchievements />
      </section>
    </template>
  </SettingsShell>
</template>

<style scoped>
.r-v2-profile__hero {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
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
  width: 88px;
  height: 88px;
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
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
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
  gap: 6px;
  min-width: 0;
}

.r-v2-profile__username {
  margin: 0;
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-bold);
}

.r-v2-profile__role {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--r-color-fg-secondary);
  text-transform: capitalize;
}

.r-v2-profile__section {
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.r-v2-profile__section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--r-color-fg);
}
.r-v2-profile__section-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: var(--r-font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.r-v2-profile__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.r-v2-profile__actions {
  display: flex;
  justify-content: flex-start;
  margin-top: 4px;
}

.r-v2-profile__role-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: capitalize;
}

.r-v2-profile__section--legacy {
  padding: 0;
  background: transparent;
  border: 0;
}
</style>
