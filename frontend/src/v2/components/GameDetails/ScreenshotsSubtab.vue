<script setup lang="ts">
import {
  RBtn,
  RCarousel,
  RDropzone,
  REmptyState,
  RSkeletonBlock,
  RTooltip,
} from "@v2/lib";
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import ScreenshotsTab from "@/v2/components/GameDetails/ScreenshotsTab.vue";
import { useScreenshotManagement } from "@/v2/composables/useScreenshotManagement";
import type { DetailedRom } from "@/v2/data/adapters/legacy/stores/roms";

const props = defineProps<{ rom: DetailedRom }>();
const { t } = useI18n();
const {
  providerScreenshots,
  providerUrls,
  myScreenshots,
  communityScreenshots,
  canManage,
  canRefresh,
  refreshing,
  mutatingId,
  togglingId,
  deletingId,
  mediaContentUrl,
  hasPlacement,
  placementPosition,
  handleMyFiles,
  deleteMyScreenshot,
  deleteProviderScreenshot,
  toggleVisibility,
  togglePlacement,
  refreshProviderScreenshots,
} = useScreenshotManagement(() => props.rom);
const providerLightboxOpen = ref(false);
const providerLightboxIndex = ref(0);
const myDz = ref<InstanceType<typeof RDropzone> | null>(null);
</script>

<template>
  <div class="r-v2-shots">
    <section
      class="r-v2-shots__section"
      aria-labelledby="provider-screenshots-heading"
    >
      <header class="r-v2-shots__head">
        <div>
          <h3 id="provider-screenshots-heading" class="r-v2-shots__title">
            {{ t("rom.screenshots") }}
          </h3>
          <p class="r-v2-shots__subtitle">
            {{ t("rom.screenshots-section-rom-desc") }}
            <br />{{ t("rom.provider-screenshot-delete-note") }}
          </p>
        </div>
        <RTooltip :text="t('common.refresh')"
          ><RBtn
            v-if="canRefresh"
            icon="mdi-refresh"
            :loading="refreshing"
            :aria-label="t('common.refresh')"
            @click="refreshProviderScreenshots"
        /></RTooltip>
      </header>
      <div
        v-if="refreshing && providerScreenshots.length === 0"
        class="r-v2-shots__grid"
      >
        <RSkeletonBlock v-for="index in 3" :key="index" height="180" />
      </div>
      <REmptyState
        v-else-if="providerScreenshots.length === 0"
        :title="t('rom.screenshots-empty')"
      />
      <ul v-else class="r-v2-shots__grid">
        <li
          v-for="(item, index) in providerScreenshots"
          :key="item.id"
          class="r-v2-shots__candidate"
        >
          <button
            type="button"
            class="r-v2-shots__preview"
            :aria-label="item.display_label"
            @click="
              providerLightboxIndex = index;
              providerLightboxOpen = true;
            "
          >
            <img :src="mediaContentUrl(item.id)" :alt="item.display_label" />
          </button>
          <p class="r-v2-shots__origin">
            {{ item.provider ?? t("rom.screenshots") }}
          </p>
          <p v-if="hasPlacement(item, 'overview')" class="r-v2-shots__ordinal">
            {{ placementPosition(item, "overview") }}
          </p>
          <div v-if="canManage" class="r-v2-shots__actions">
            <RBtn
              size="small"
              :loading="mutatingId === item.id"
              :aria-label="
                hasPlacement(item, 'overview')
                  ? t('rom.remove-from-overview')
                  : t('rom.add-to-overview')
              "
              @click.stop="togglePlacement(item, 'overview')"
              >{{
                hasPlacement(item, "overview")
                  ? t("rom.remove-from-overview")
                  : t("rom.add-to-overview")
              }}</RBtn
            ><RBtn
              size="small"
              variant="outlined"
              :loading="mutatingId === item.id"
              :aria-label="
                hasPlacement(item, 'background')
                  ? t('rom.remove-as-background')
                  : t('rom.add-as-background')
              "
              @click.stop="togglePlacement(item, 'background')"
              >{{
                hasPlacement(item, "background")
                  ? t("rom.remove-as-background")
                  : t("rom.add-as-background")
              }}</RBtn
            ><RBtn
              v-if="canManage"
              icon="mdi-delete-outline"
              :loading="mutatingId === item.id"
              :aria-label="t('common.delete')"
              @click.stop="deleteProviderScreenshot(item)"
              ><RTooltip activator="parent" :text="t('common.delete')" />
              ></RBtn
            >
          </div>
        </li>
      </ul>
    </section>
    <section class="r-v2-shots__section">
      <header class="r-v2-shots__head">
        <h3 class="r-v2-shots__title">
          {{ t("rom.screenshots-section-mine") }}
        </h3>
        <RBtn
          v-if="myScreenshots.length"
          variant="outlined"
          size="small"
          @click="myDz?.open()"
          >{{ t("common.upload") }}</RBtn
        >
      </header>
      <RDropzone
        v-if="!myScreenshots.length"
        :title="t('rom.screenshots-empty')"
        :hint="t('common.dropzone-hint')"
        :active-title="t('common.dropzone-drag-over')"
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleMyFiles"
      /><RDropzone
        v-else
        ref="myDz"
        overlay
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleMyFiles"
        ><ScreenshotsTab
          :screenshots="myScreenshots"
          deletable
          togglable
          :toggling-id="togglingId"
          :deleting-id="deletingId"
          @delete="deleteMyScreenshot"
          @toggle-visibility="toggleVisibility"
      /></RDropzone>
    </section>
    <section v-if="communityScreenshots.length" class="r-v2-shots__section">
      <h3 class="r-v2-shots__title">
        {{ t("rom.screenshots-section-community") }}
      </h3>
      <ScreenshotsTab :screenshots="communityScreenshots" />
    </section>
  </div>
  <RCarousel
    v-if="providerLightboxOpen"
    v-model="providerLightboxIndex"
    :items="providerUrls"
    fullscreen
    show-thumbnails
    :aria-label="t('rom.screenshots')"
    @close="providerLightboxOpen = false"
    ><template #default="{ item, index }"
      ><img
        :src="item"
        :alt="providerScreenshots[index]?.display_label" /></template
    ><template #thumbnail="{ item, index }"
      ><img
        :src="item"
        :alt="providerScreenshots[index]?.display_label" /></template
  ></RCarousel>
</template>

<style scoped>
.r-v2-shots {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--r-space-6);
  min-height: 0;
  overflow-y: auto;
}
.r-v2-shots__section {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}
.r-v2-shots__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--r-space-4);
}
.r-v2-shots__title {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
}
.r-v2-shots__subtitle,
.r-v2-shots__origin,
.r-v2-shots__ordinal {
  margin: 0;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
}
.r-v2-shots__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--r-space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}
.r-v2-shots__candidate {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  padding: var(--r-space-4);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  background: var(--r-color-bg-elevated);
}
.r-v2-shots__preview {
  width: 100%;
  padding: 0;
  overflow: hidden;
  border: 0;
  border-radius: var(--r-radius-md);
  background: transparent;
  cursor: pointer;
}
.r-v2-shots__preview img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--r-color-cover-placeholder);
}
.r-v2-shots__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--r-space-2);
}
</style>
