<script setup lang="ts">
import { RBtn, RImg, RMenu, RMenuItem, RTabNav, RTag } from "@v2/lib";
import type { Emitter } from "mitt";
import { computed, inject, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import type { DetailedRomSchema, PcComponentSchema } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import type { Events } from "@/types/emitter";
import { FRONTEND_RESOURCES_PATH, formatBytes } from "@/utils";
import PcDlcFiles from "@/v2/components/GameDetails/PcDlcFiles.vue";
import PcDlcMediaTab from "@/v2/components/GameDetails/PcDlcMediaTab.vue";
import PcDlcNotesTab from "@/v2/components/GameDetails/PcDlcNotesTab.vue";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  parent: DetailedRomSchema;
  component: PcComponentSchema;
}>();
const emit = defineEmits<{ (event: "refresh"): void }>();

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const emitter = inject<Emitter<Events>>("emitter");
const validTabs = ["overview", "files", "media", "notes"] as const;
type DlcTab = (typeof validTabs)[number];
const tab = ref<DlcTab>(
  validTabs.includes(route.query.tab as DlcTab)
    ? (route.query.tab as DlcTab)
    : "overview",
);
const tabs = computed(() => [
  { id: "overview", label: t("rom.tab-overview") },
  { id: "files", label: t("rom.tab-files") },
  { id: "media", label: t("rom.media") },
  { id: "notes", label: t("rom.tab-notes") },
]);

watch(tab, (value) => {
  if (route.query.tab !== value) {
    void router.replace({
      path: route.path,
      query: { ...route.query, tab: value },
    });
  }
});
watch(
  () => route.query.tab,
  (value) => {
    if (typeof value === "string" && validTabs.includes(value as DlcTab)) {
      tab.value = value as DlcTab;
    }
  },
);

const title = computed(
  () =>
    props.component.component_metadata?.name ??
    t("rom.pc-dlc-fallback-title", {
      relativePath: props.component.relative_path,
    }),
);
const summary = computed(() => props.component.component_metadata?.summary);
const cover = computed(() =>
  props.component.local_media?.find((media) => media.role === "cover"),
);
const media = computed(() =>
  (props.component.local_media ?? []).filter(
    (item) => item.role === "background" || item.role === "gallery",
  ),
);
const manifestSize = computed(() =>
  props.component.manifest_members.reduce(
    (total, member) => total + member.size_bytes,
    0,
  ),
);

function ownedMediaUrl(ownedPath: string) {
  return `${FRONTEND_RESOURCES_PATH}/${ownedPath}`;
}

function openMatcher() {
  emitter?.emit("showPcMatchRomDialog", {
    target: {
      kind: "component",
      romId: props.parent.id,
      componentId: props.component.id,
      componentKind: "dlc",
      label: title.value,
    },
    refresh: () => emit("refresh"),
  });
}

function showMedia() {
  tab.value = "media";
}
</script>

<template>
  <main class="r-v2-det pc-dlc-detail">
    <div class="r-v2-det__body">
      <aside class="pc-dlc-detail__cover-column">
        <RBtn
          class="pc-dlc-detail__back"
          :to="{ name: ROUTES.ROM, params: { rom: parent.id } }"
          variant="text"
        >
          {{ t("rom.pc-dlc-back-to-game", { game: parent.name ?? "" }) }}
        </RBtn>
        <RImg
          v-if="cover"
          class="pc-dlc-detail__cover"
          :src="ownedMediaUrl(cover.owned_path)"
          :alt="title"
          width="240"
          height="324"
          cover
        />
        <div
          v-else
          data-testid="pc-dlc-cover-placeholder"
          class="pc-dlc-detail__cover pc-dlc-detail__cover--placeholder"
          role="img"
          :aria-label="title"
        />
      </aside>

      <div class="r-v2-det__info">
        <section class="pc-dlc-detail__hero">
          <RTag :text="t('rom.category-dlc')" tone="brand" />
          <h1 class="pc-dlc-detail__title">{{ title }}</h1>
          <p v-if="summary" class="pc-dlc-detail__summary">{{ summary }}</p>
          <dl class="pc-dlc-detail__facts">
            <div class="pc-dlc-detail__fact">
              <dt>{{ t("rom.file") }}</dt>
              <dd>{{ component.relative_path }}</dd>
            </div>
            <div class="pc-dlc-detail__fact">
              <dt>{{ t("rom.files") }}</dt>
              <dd>{{ component.manifest_members.length }}</dd>
            </div>
            <div class="pc-dlc-detail__fact">
              <dt>{{ t("common.size") }}</dt>
              <dd>{{ formatBytes(manifestSize) }}</dd>
            </div>
          </dl>
        </section>

        <div class="pc-dlc-detail__tab-bar">
          <RTabNav v-model="tab" :items="tabs" class="r-v2-det__tabs" />
          <RMenu location="bottom end">
            <template #activator="{ props: menuProps }">
              <RBtn
                v-bind="menuProps"
                icon="mdi-dots-vertical"
                :aria-label="t('common.actions')"
              />
            </template>
            <RMenuItem
              :label="t('rom.pc-find-metadata')"
              icon="mdi-magnify"
              @click="openMatcher"
            />
            <RMenuItem
              :label="t('rom.artwork')"
              icon="mdi-image-plus-outline"
              @click="showMedia"
            />
            <RMenuItem
              :label="t('rom.download')"
              icon="mdi-download"
              @click="tab = 'files'"
            />
          </RMenu>
        </div>

        <div class="r-v2-det__panel">
          <section
            v-if="tab === 'overview' && media.length > 0"
            data-testid="pc-dlc-media"
            class="pc-dlc-detail__media"
          >
            <RImg
              v-for="item in media"
              :key="item.id"
              :src="ownedMediaUrl(item.owned_path)"
              :alt="title"
              class="pc-dlc-detail__media-image"
              aspect-ratio="16/9"
              cover
            />
          </section>

          <PcDlcFiles
            v-if="tab === 'files'"
            :rom-id="parent.id"
            :component="component"
          />
          <PcDlcMediaTab
            v-if="tab === 'media'"
            :rom-id="parent.id"
            :component="component"
            @refresh="emit('refresh')"
          />
          <PcDlcNotesTab
            v-if="tab === 'notes'"
            :rom-id="parent.id"
            :component="component"
          />
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.pc-dlc-detail {
  height: calc(100vh - var(--r-nav-h));
  display: flex;
  flex-direction: column;
  padding-top: 20px;
}

.pc-dlc-detail .r-v2-det__body {
  flex: 1;
  display: flex;
  align-items: stretch;
  padding: 0 var(--r-row-pad) 32px;
  gap: 52px;
  min-height: 0;
  max-width: var(--r-page-max-w);
  width: 100%;
  margin: 0 auto;
}

.pc-dlc-detail .r-v2-det__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.pc-dlc-detail .r-v2-det__tabs {
  margin: 14px 0 16px;
}

.pc-dlc-detail .r-v2-det__panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--r-color-border-strong) transparent;
  margin-top: 10px;
  padding-right: 6px;
}

.pc-dlc-detail__cover-column {
  width: 240px;
  flex-shrink: 0;
  align-self: flex-start;
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.pc-dlc-detail__back {
  align-self: flex-start;
  min-height: var(--r-touch-target);
}

.pc-dlc-detail__tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--r-space-3);
}

.pc-dlc-detail__hero {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--r-space-4);
}

.pc-dlc-detail__cover {
  width: 240px;
  height: 324px;
  border-radius: var(--r-radius-lg);
}

.pc-dlc-detail__cover--placeholder {
  background: var(--r-color-cover-placeholder);
  border: 1px solid var(--r-color-border);
}

.pc-dlc-detail__identity {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--r-space-4);
  min-width: 0;
}

.pc-dlc-detail__title {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-3xl);
  font-weight: var(--r-font-weight-semibold);
  line-height: var(--r-line-height-tight);
  overflow-wrap: anywhere;
}

.pc-dlc-detail__summary {
  margin: 0;
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-md);
  line-height: var(--r-line-height-normal);
}

.pc-dlc-detail__facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--r-space-6);
  margin: 0;
}

.pc-dlc-detail__fact {
  min-width: 0;
}

.pc-dlc-detail__fact dt {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-semibold);
}

.pc-dlc-detail__fact dd {
  margin: var(--r-space-1) 0 0;
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-md);
  overflow-wrap: anywhere;
}

.pc-dlc-detail__media {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: var(--r-space-4);
}

.pc-dlc-detail__media-image {
  width: 100%;
  border-radius: var(--r-radius-md);
}

html[data-bp~="sm-and-down"] .pc-dlc-detail {
  height: auto;
  padding-top: 8px;
}

html[data-bp~="sm-and-down"] .pc-dlc-detail .r-v2-det__body {
  flex: none;
  flex-direction: column;
  gap: 14px;
  padding: 8px var(--r-row-pad) 16px;
}

html[data-bp~="sm-and-down"] .pc-dlc-detail .r-v2-det__info,
html[data-bp~="sm-and-down"] .pc-dlc-detail .r-v2-det__panel {
  flex: none;
  min-height: 0;
}

html[data-bp~="sm-and-down"] .pc-dlc-detail .r-v2-det__panel {
  overflow: visible;
  padding-right: 0;
}

html[data-bp~="sm-and-down"] .pc-dlc-detail__cover-column {
  align-self: center;
}
</style>
