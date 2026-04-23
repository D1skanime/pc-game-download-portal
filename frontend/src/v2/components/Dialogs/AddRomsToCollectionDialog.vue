<script setup lang="ts">
// AddRomsToCollectionDialog — emits `showAddToCollectionDialog` with a
// batch of ROMs; user picks a collection from their owned list and
// commits. Reuses the v1 `RAvatar` collection avatar primitive for cover
// rendering (virtual/smart/favorite branches + procedural fallbacks).
import { RBtn, RDialog, RIcon } from "@v2/lib";
import type { Emitter } from "mitt";
import { inject, onBeforeUnmount, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useDisplay } from "vuetify";
import type { CollectionSchema } from "@/__generated__";
import RAvatarCollection from "@/components/common/Collection/RAvatar.vue";
import collectionApi from "@/services/api/collection";
import storeCollections from "@/stores/collections";
import storeRoms, { type SimpleRom } from "@/stores/roms";
import type { Events } from "@/types/emitter";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const { mdAndUp } = useDisplay();
const show = ref(false);
const saving = ref(false);
const romsStore = storeRoms();
const collectionsStore = storeCollections();
const selectedCollection = ref<CollectionSchema | undefined>(undefined);
const roms = ref<SimpleRom[]>([]);
const emitter = inject<Emitter<Events>>("emitter");

const openHandler = (romsToAdd: SimpleRom[]) => {
  roms.value = romsToAdd;
  show.value = true;
};
emitter?.on("showAddToCollectionDialog", openHandler);
onBeforeUnmount(() => emitter?.off("showAddToCollectionDialog", openHandler));

function coverFor(rom: SimpleRom): string | null {
  return rom.path_cover_small ?? rom.url_cover ?? null;
}

async function addRomsToCollection() {
  if (!selectedCollection.value || saving.value) return;
  saving.value = true;
  const romIds = roms.value.map((r) => r.id);
  try {
    const { data } = await collectionApi.addRomsToCollection(
      selectedCollection.value.id,
      romIds,
    );
    emitter?.emit("snackbarShow", {
      msg: `Roms added to ${selectedCollection.value.name} successfully!`,
      icon: "mdi-check-bold",
      color: "green",
      timeout: 2000,
    });
    emitter?.emit("refreshDrawer", null);
    collectionsStore.updateCollection(data);
  } catch (error: unknown) {
    console.error(error);
    const axiosErr = error as { response?: { data?: { detail?: string } } };
    emitter?.emit("snackbarShow", {
      msg: axiosErr.response?.data?.detail ?? "Failed to add to collection",
      icon: "mdi-close-circle",
      color: "red",
    });
  } finally {
    emitter?.emit("showLoadingDialog", { loading: false, scrim: false });
    romsStore.resetSelection();
    saving.value = false;
    closeDialog();
  }
}

function closeDialog() {
  roms.value = [];
  show.value = false;
  selectedCollection.value = undefined;
}
</script>

<template>
  <RDialog
    v-model="show"
    icon="mdi-bookmark-plus-outline"
    scroll-content
    :width="mdAndUp ? 520 : '95vw'"
    @close="closeDialog"
  >
    <template #header>
      <span>{{ t("rom.adding-to-collection", roms.length) }}</span>
    </template>
    <template #prepend>
      <div class="r-v2-add-coll__picker">
        <v-autocomplete
          v-model="selectedCollection"
          density="comfortable"
          variant="outlined"
          :label="t('common.collection')"
          item-title="name"
          :items="collectionsStore.ownedCollections"
          hide-details
          return-object
          clearable
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :title="item.raw.name">
              <template #prepend>
                <RAvatarCollection :collection="item.raw" :size="28" />
              </template>
            </v-list-item>
          </template>
          <template #chip="{ item }">
            <v-chip>
              <RAvatarCollection
                :collection="item.raw"
                :size="22"
                class="mr-2"
              />
              {{ item.raw.name }}
            </v-chip>
          </template>
        </v-autocomplete>
      </div>
    </template>
    <template #content>
      <ul class="r-v2-add-coll__list">
        <li v-for="rom in roms" :key="rom.id" class="r-v2-add-coll__row">
          <div class="r-v2-add-coll__cover">
            <img
              v-if="coverFor(rom)"
              :src="coverFor(rom)!"
              :alt="rom.name ?? ''"
            />
            <div v-else class="r-v2-add-coll__cover-placeholder">
              <RIcon icon="mdi-disc" size="18" />
            </div>
          </div>
          <div class="r-v2-add-coll__meta">
            <p class="r-v2-add-coll__name" :title="rom.name ?? undefined">
              {{ rom.name || rom.fs_name }}
            </p>
            <p class="r-v2-add-coll__file" :title="rom.fs_name">
              {{ rom.fs_name }}
            </p>
          </div>
        </li>
      </ul>
    </template>
    <template #footer>
      <RBtn variant="text" :disabled="saving" @click="closeDialog">
        {{ t("common.cancel") }}
      </RBtn>
      <div style="flex: 1" />
      <RBtn
        variant="tonal"
        color="primary"
        prepend-icon="mdi-bookmark-plus"
        :disabled="!selectedCollection || saving"
        :loading="saving"
        @click="addRomsToCollection"
      >
        {{ t("common.confirm") }}
      </RBtn>
    </template>
  </RDialog>
</template>

<style scoped>
.r-v2-add-coll__picker {
  padding: 14px 14px 0;
}

.r-v2-add-coll__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 300px;
  overflow-y: auto;
}

.r-v2-add-coll__row {
  display: grid;
  grid-template-columns: 32px 1fr;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--r-radius-md);
}

.r-v2-add-coll__cover {
  width: 32px;
  aspect-ratio: 3 / 4;
  border-radius: var(--r-radius-sm);
  overflow: hidden;
  background: #1a1a2e;
  display: grid;
  place-items: center;
}
.r-v2-add-coll__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.r-v2-add-coll__cover-placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.r-v2-add-coll__meta {
  min-width: 0;
}
.r-v2-add-coll__name {
  margin: 0;
  font-size: 12.5px;
  font-weight: var(--r-font-weight-medium);
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.r-v2-add-coll__file {
  margin: 1px 0 0;
  font-size: 10.5px;
  font-family: var(--r-font-family-mono, monospace);
  color: rgba(255, 255, 255, 0.45);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
