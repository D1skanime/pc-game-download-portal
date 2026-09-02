<script setup lang="ts">
import { RBtn, RImg, RTag } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { DetailedRomSchema, PcComponentSchema } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import { FRONTEND_RESOURCES_PATH, formatBytes } from "@/utils";
import PcDlcFiles from "./PcDlcFiles.vue";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  parent: DetailedRomSchema;
  component: PcComponentSchema;
}>();

const { t } = useI18n();

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
</script>

<template>
  <main class="pc-dlc-detail">
    <RBtn
      class="pc-dlc-detail__back"
      :to="{ name: ROUTES.ROM, params: { rom: parent.id } }"
      variant="text"
    >
      {{ t("rom.pc-dlc-back-to-game", { game: parent.name ?? "" }) }}
    </RBtn>

    <section class="pc-dlc-detail__hero">
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

      <div class="pc-dlc-detail__identity">
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
      </div>
    </section>

    <section
      v-if="media.length > 0"
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

    <PcDlcFiles :component="component" />
  </main>
</template>

<style scoped>
.pc-dlc-detail {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-8);
  padding: var(--r-space-6) var(--r-row-pad);
}

.pc-dlc-detail__back {
  align-self: flex-start;
  min-height: var(--r-touch-target);
}

.pc-dlc-detail__hero {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: var(--r-space-8);
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

html[data-bp~="sm-and-down"] .pc-dlc-detail__hero {
  grid-template-columns: minmax(0, 1fr);
}

html[data-bp~="sm-and-down"] .pc-dlc-detail__cover {
  justify-self: center;
}
</style>
