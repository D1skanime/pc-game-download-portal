<script setup lang="ts">
import {
  RBtn,
  RCarousel,
  RDropzone,
  REmptyState,
  RSkeletonBlock,
} from "@v2/lib";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import ScreenshotManagementCard, {
  type ScreenshotManagementAction,
  type ScreenshotManagementItem,
} from "@/v2/components/GameDetails/ScreenshotManagementCard.vue";
import { useResponsiveColumns } from "@/v2/composables/useResponsiveColumns";
import { useScreenshotManagement } from "@/v2/composables/useScreenshotManagement";
import { useWrapGridNav } from "@/v2/composables/useWrapGridNav";
import type { DetailedRom } from "@/v2/data/adapters/legacy/stores/roms";

const props = defineProps<{ rom: DetailedRom }>();
const { t } = useI18n();
const {
  providerScreenshots,
  myScreenshots,
  communityScreenshots,
  canManage,
  canRefresh,
  canUpload,
  refreshing,
  mutatingId,
  togglingId,
  deletingId,
  uploading,
  newlyUploadedIds,
  mediaContentUrl,
  handleMyFiles,
  deleteMyScreenshot,
  deleteProviderScreenshot,
  toggleVisibility,
  togglePlacement,
  refreshProviderScreenshots,
} = useScreenshotManagement(() => props.rom);
const root = ref<HTMLElement | null>(null);
const gallery = ref<HTMLElement | null>(null);
const toolbar = ref<HTMLElement | null>(null);
const myDz = ref<InstanceType<typeof RDropzone> | null>(null);
const { columns } = useResponsiveColumns(gallery, {
  cardWidth: 200,
  gap: () =>
    gallery.value
      ? parseFloat(
          getComputedStyle(gallery.value).getPropertyValue("--r-space-3"),
        ) || 12
      : 12,
});
// Each native control participates so directional input reaches both previews and actions.
useWrapGridNav(root, { cellSelector: "button:not([disabled])" });
type Source = ScreenshotManagementItem["source"];
const groups = computed<
  { source: Source; label: string; items: ScreenshotManagementItem[] }[]
>(() => [
  {
    source: "provider",
    label: t("rom.screenshots-source-provider"),
    items: providerScreenshots.value.map((media) => ({
      source: "provider",
      key: `provider:${media.id}`,
      media,
      url: mediaContentUrl(media.id),
    })),
  },
  {
    source: "mine",
    label: t("rom.screenshots-section-mine"),
    items: myScreenshots.value.flatMap((shot) =>
      shot.id == null
        ? []
        : [
            {
              source: "mine" as const,
              key: `user:${shot.id}` as const,
              shot,
            },
          ],
    ),
  },
  {
    source: "community",
    label: t("rom.screenshots-section-community"),
    items: communityScreenshots.value.flatMap((shot) =>
      shot.id == null
        ? []
        : [
            {
              source: "community" as const,
              key: `user:${shot.id}` as const,
              shot,
            },
          ],
    ),
  },
]);
const providerBusy = computed(
  () => refreshing.value || mutatingId.value !== null,
);
const personalBusy = computed(
  () => togglingId.value !== null || deletingId.value !== null,
);
function cardUrl(item: ScreenshotManagementItem) {
  return item.source === "provider" ? item.url : item.shot.url;
}
const lightbox = ref<{ source: Source; key: string } | null>(null);
const lightboxItems = computed(
  () =>
    groups.value.find((group) => group.source === lightbox.value?.source)
      ?.items ?? [],
);
const lightboxUrls = computed(() => lightboxItems.value.map(cardUrl));
const lightboxIndex = computed({
  get: () =>
    lightboxItems.value.findIndex((item) => item.key === lightbox.value?.key),
  set: (index: number) => {
    const item = lightboxItems.value[index];
    if (item) lightbox.value = { source: item.source, key: item.key };
  },
});
let invokingKey: string | null = null;
let mounted = true;
let viewGeneration = 0;
onBeforeUnmount(() => {
  mounted = false;
});
function cardElement(key: string) {
  return Array.from(
    root.value?.querySelectorAll<HTMLElement>("[data-shot-key]") ?? [],
  ).find((element) => element.dataset.shotKey === key);
}
async function closeLightbox(restoreInvoker = true) {
  const key = restoreInvoker ? invokingKey : null;
  const romId = props.rom.id;
  const generation = viewGeneration;
  lightbox.value = null;
  invokingKey = null;
  await nextTick();
  if (
    !mounted ||
    romId !== props.rom.id ||
    generation !== viewGeneration ||
    lightbox.value
  )
    return;
  const target =
    (key
      ? cardElement(key)?.querySelector<HTMLElement>("[data-preview]")
      : null) ??
    toolbar.value?.querySelector<HTMLElement>("button:not([disabled])") ??
    root.value?.querySelector<HTMLElement>("[data-preview]");
  target?.focus({ preventScroll: true });
}
watch(
  () => props.rom.id,
  () => {
    viewGeneration++;
    if (lightbox.value) void closeLightbox(false);
  },
  { flush: "sync" },
);
watch(lightboxItems, (items) => {
  if (lightbox.value && !items.some((item) => item.key === lightbox.value?.key))
    void closeLightbox();
});
function dispatch(action: ScreenshotManagementAction) {
  switch (action.type) {
    case "preview":
      invokingKey = action.item.key;
      lightbox.value = { source: action.item.source, key: action.item.key };
      break;
    case "placement":
      void togglePlacement(action.item.media, action.surface);
      break;
    case "remove-provider":
      void deleteProviderScreenshot(action.item.media);
      break;
    case "visibility":
      if (action.item.shot.id != null)
        void toggleVisibility(action.item.shot.id, action.isPublic);
      break;
    case "delete-mine":
      if (action.item.shot.id != null)
        void deleteMyScreenshot(action.item.shot.id);
  }
}
function scrollOwner() {
  if (!root.value) return null;
  return getComputedStyle(root.value).overflowY === "visible"
    ? ((document.scrollingElement as HTMLElement | null) ??
        document.documentElement)
    : root.value;
}
// Only this view measures DOM geometry; the lifecycle owns canonical upload settlement.
async function uploadFiles(files: File[]) {
  if (uploading.value || !canUpload.value || !files.length) return;
  const romId = props.rom.id;
  const generation = viewGeneration;
  const previousUploads = newlyUploadedIds.value;
  const owner = scrollOwner();
  const scrollTop = owner?.scrollTop;
  const inset = toolbar.value?.getBoundingClientRect().bottom ?? 0;
  const bottom =
    owner === root.value
      ? (owner?.getBoundingClientRect().bottom ?? innerHeight)
      : innerHeight;
  const anchor = Array.from(
    root.value?.querySelectorAll<HTMLElement>("[data-shot-key]") ?? [],
  ).find((element) => {
    const rect = element.getBoundingClientRect();
    return rect.bottom > inset && rect.top < bottom;
  });
  const key = anchor?.dataset.shotKey;
  const top = anchor?.getBoundingClientRect().top;
  await handleMyFiles(files);
  await nextTick();
  // A user scroll, breakpoint change or navigation supersedes the saved anchor.
  if (
    !mounted ||
    props.rom.id !== romId ||
    generation !== viewGeneration ||
    previousUploads === newlyUploadedIds.value ||
    !newlyUploadedIds.value.length ||
    !owner ||
    owner !== scrollOwner() ||
    owner.scrollTop !== scrollTop ||
    !key ||
    top === undefined
  )
    return;
  const surviving = cardElement(key);
  if (surviving) owner.scrollTop += surviving.getBoundingClientRect().top - top;
}
</script>

<template>
  <div ref="root" class="za-shots" data-shot-scroll>
    <RDropzone
      ref="myDz"
      class="za-shots__dropzone"
      overlay
      accept="image/*"
      multiple
      :disabled="uploading || !canUpload"
      :input-label="t('rom.upload-screenshots')"
      :release-label="t('common.dropzone-drag-over')"
      @files="uploadFiles"
    >
      <header
        ref="toolbar"
        class="za-shots__toolbar d-flex flex-wrap align-center"
      >
        <RBtn
          v-if="canUpload"
          prepend-icon="mdi-cloud-upload-outline"
          color="primary"
          :loading="uploading"
          :disabled="uploading"
          :aria-label="t('rom.upload-screenshots')"
          @click="myDz?.open()"
          >{{ t("rom.upload-screenshots") }}</RBtn
        >
        <p class="za-shots__hint">{{ t("rom.screenshots-upload-hint") }}</p>
      </header>
      <div
        ref="gallery"
        class="za-shots__gallery d-flex flex-column"
        :style="{ '--za-shot-columns': columns }"
      >
        <template v-for="group in groups" :key="group.source">
          <section
            v-if="group.source !== 'community' || group.items.length"
            class="za-shots__section d-flex flex-column"
            :aria-labelledby="`shots-${group.source}`"
          >
            <header
              class="za-shots__head d-flex align-center justify-space-between"
            >
              <h3 :id="`shots-${group.source}`" class="za-shots__title">
                {{ group.label }}
              </h3>
              <RBtn
                v-if="group.source === 'provider' && canRefresh"
                icon="mdi-refresh"
                :loading="refreshing"
                :disabled="providerBusy"
                :aria-label="t('common.refresh')"
                :tooltip="t('common.refresh')"
                @click="refreshProviderScreenshots"
              >
              </RBtn>
            </header>
            <p v-if="group.source === 'provider'" class="za-shots__hint">
              {{ t("rom.provider-screenshot-delete-note") }}
            </p>
            <div
              v-if="
                group.source === 'provider' && refreshing && !group.items.length
              "
              class="za-shots__grid"
            >
              <RSkeletonBlock v-for="index in 3" :key="index" height="180" />
            </div>
            <REmptyState
              v-else-if="!group.items.length"
              :title="t('rom.screenshots-empty')"
            />
            <ul v-else class="za-shots__grid">
              <li
                v-for="item in group.items"
                :key="item.key"
                :data-shot-key="item.key"
                :data-focus-key="item.key"
              >
                <ScreenshotManagementCard
                  :item="item"
                  :can-manage="canManage"
                  :busy="
                    item.source === 'provider' ? providerBusy : personalBusy
                  "
                  :provider-loading="
                    item.source === 'provider' && mutatingId === item.media.id
                  "
                  :visibility-loading="
                    item.source === 'mine' && togglingId === item.shot.id
                  "
                  :deletion-loading="
                    item.source === 'mine' && deletingId === item.shot.id
                  "
                  :newly-uploaded="
                    item.source === 'mine' &&
                    item.shot.id != null &&
                    newlyUploadedIds.includes(item.shot.id)
                  "
                  @action="dispatch"
                />
              </li>
            </ul>
          </section>
        </template>
      </div>
    </RDropzone>
  </div>
  <RCarousel
    v-if="lightbox"
    v-model="lightboxIndex"
    :items="lightboxUrls"
    fullscreen
    show-thumbnails
    :aria-label="t('rom.screenshots')"
    :close-label="t('common.close')"
    @close="closeLightbox()"
  >
    <template #default="{ item, index }">
      <img :src="item" :alt="t('rom.screenshot-num', { n: index + 1 })" />
    </template>
    <template #thumbnail="{ item, index }">
      <img :src="item" :alt="t('rom.screenshot-num-thumb', { n: index + 1 })" />
    </template>
  </RCarousel>
</template>

<style scoped>
.za-shots {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow-y: auto;
  overflow-anchor: none;
}
.za-shots__dropzone {
  height: auto;
  min-height: 100%;
}
.za-shots__toolbar {
  position: sticky;
  top: 0;
  z-index: 2;
  gap: var(--r-space-3);
  padding: var(--r-space-3);
  background: var(--r-color-panel);
  border-bottom: 1px solid var(--r-color-panel-border);
}
.za-shots__gallery {
  gap: var(--r-space-6);
  padding-top: var(--r-space-4);
}
.za-shots__section {
  min-width: 0;
  gap: var(--r-space-3);
}
.za-shots__head {
  gap: var(--r-space-3);
}
.za-shots__title {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
  line-height: var(--r-line-height-normal);
}
.za-shots__hint {
  margin: 0;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-md);
  line-height: var(--r-line-height-normal);
}
.za-shots__grid {
  display: grid;
  grid-template-columns: repeat(var(--za-shot-columns, 1), minmax(0, 1fr));
  gap: var(--r-space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}
.za-shots__grid > li {
  min-width: 0;
  scroll-margin-top: calc(var(--r-touch-target) + var(--r-space-6));
}
html[data-bp~="sm-and-down"] .za-shots {
  flex: none;
  overflow: visible;
  height: auto;
}
html[data-bp~="sm-and-down"] .za-shots__dropzone {
  height: auto;
  min-height: 0;
}
html[data-bp~="sm-and-down"] .za-shots__toolbar {
  top: var(--r-nav-h);
}
html[data-bp~="sm-and-down"] .za-shots__grid > li {
  scroll-margin-top: calc(
    var(--r-nav-h) + var(--r-touch-target) + var(--r-space-6)
  );
}
html[data-bp~="xs"] .za-shots__toolbar :deep(button),
html[data-input="touch"] .za-shots__toolbar :deep(button),
html[data-input="pad"] .za-shots__toolbar :deep(button) {
  min-height: var(--r-touch-target);
}
</style>
