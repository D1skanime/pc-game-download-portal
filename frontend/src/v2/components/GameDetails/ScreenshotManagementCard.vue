<script setup lang="ts">
import { RAvatar } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { RomOwnedMediaSchema } from "@/__generated__";
import MediaManagementAction from "@/v2/components/GameDetails/MediaManagementAction.vue";
import MediaManagementCard from "@/v2/components/GameDetails/MediaManagementCard.vue";
import type { ScreenshotItem } from "@/v2/components/GameDetails/ScreenshotsTab.vue";
import { userAvatarUrl } from "@/v2/utils/userAvatar";

type ProviderItem = {
  source: "provider";
  key: `provider:${number}`;
  media: RomOwnedMediaSchema;
  url: string;
};
type PersonalItem = {
  source: "mine";
  key: `user:${number}`;
  shot: ScreenshotItem;
};
type CommunityItem = {
  source: "community";
  key: `user:${number}`;
  shot: ScreenshotItem;
};
export type ScreenshotManagementItem =
  ProviderItem | PersonalItem | CommunityItem;
export type ScreenshotManagementAction =
  | { type: "preview"; item: ScreenshotManagementItem }
  | {
      type: "placement";
      item: ProviderItem;
      surface: "overview" | "background";
    }
  | { type: "remove-provider"; item: ProviderItem }
  | { type: "visibility"; item: PersonalItem; isPublic: boolean }
  | { type: "delete-mine"; item: PersonalItem };

// Source discrimination prevents personal gallery IDs from becoming placement IDs.
const props = defineProps<{
  item: ScreenshotManagementItem;
  canManage?: boolean;
  busy?: boolean;
  providerLoading?: boolean;
  visibilityLoading?: boolean;
  deletionLoading?: boolean;
  newlyUploaded?: boolean;
}>();
const emit = defineEmits<{ action: [action: ScreenshotManagementAction] }>();
const { t } = useI18n();
const url = computed(() =>
  props.item.source === "provider" ? props.item.url : props.item.shot.url,
);
const sourceLabel = computed(() =>
  props.item.source === "provider"
    ? (props.item.media.provider ?? t("rom.screenshots-source-provider"))
    : t(
        props.item.source === "mine"
          ? "rom.screenshots-section-mine"
          : "rom.screenshots-section-community",
      ),
);
const surfaces = ["overview", "background"] as const;
function position(surface: "overview" | "background") {
  const stored =
    props.item.source === "provider"
      ? props.item.media.placements?.find(
          (placement) => placement.surface === surface,
        )?.position
      : undefined;
  return stored === undefined ? undefined : stored + 1;
}
function placementLabel(surface: "overview" | "background") {
  return t(
    surface === "overview"
      ? position(surface) !== undefined
        ? "rom.remove-from-overview"
        : "rom.add-to-overview"
      : position(surface) !== undefined
        ? "rom.remove-as-background"
        : "rom.add-as-background",
  );
}
const visibilityLabel = computed(() =>
  t(
    props.item.source === "mine" && props.item.shot.isPublic
      ? "rom.screenshot-make-private"
      : "rom.screenshot-make-public",
  ),
);
</script>

<template>
  <MediaManagementCard
    :url="url"
    :label="
      item.source === 'provider'
        ? item.media.display_label
        : t('rom.screenshots')
    "
    :newly-uploaded="newlyUploaded"
    @preview="emit('action', { type: 'preview', item })"
  >
    <span class="za-shot__source" :title="sourceLabel">{{ sourceLabel }}</span>
    <div
      v-if="item.source === 'community' && item.shot.username"
      class="d-flex align-center ga-1"
    >
      <RAvatar
        :image="
          userAvatarUrl({
            userId: item.shot.userId,
            avatarPath: item.shot.userAvatarPath,
            updatedAt: item.shot.userUpdatedAt,
          })
        "
        size="16"
      />
      <span class="za-shot__source" :title="item.shot.username">{{
        item.shot.username
      }}</span>
    </div>
    <span v-if="item.source === 'mine'">{{
      t(item.shot.isPublic ? "rom.screenshot-public" : "rom.private")
    }}</span>
    <span v-if="newlyUploaded" class="za-shot__new" role="status">{{
      t("common.uploaded-n", { n: 1 })
    }}</span>
    <div
      v-if="item.source === 'provider'"
      class="za-shot__badges d-flex flex-wrap ga-1"
    >
      <template v-for="surface in surfaces" :key="surface">
        <span
          v-if="position(surface) !== undefined"
          class="za-shot__badge"
          :class="`za-shot__badge--${surface}`"
        >
          {{
            t(`rom.screenshots-${surface}-position`, {
              position: position(surface),
            })
          }}
        </span>
      </template>
    </div>
    <div
      v-if="item.source === 'provider' && canManage"
      class="za-shot__actions d-flex flex-wrap ga-1"
    >
      <MediaManagementAction
        v-for="surface in surfaces"
        :key="surface"
        :icon="
          surface === 'overview' ? 'mdi-crown-outline' : 'mdi-image-outline'
        "
        :tone="surface === 'overview' ? 'brand' : 'info'"
        :selected="position(surface) !== undefined"
        :caption="t(`rom.screenshots-action-${surface}`)"
        :label="placementLabel(surface)"
        :loading="providerLoading"
        :disabled="busy"
        @click="emit('action', { type: 'placement', item, surface })"
      />
      <MediaManagementAction
        icon="mdi-delete-outline"
        tone="danger"
        :caption="t('common.delete')"
        :label="t('rom.provider-screenshot-remove-title')"
        :disabled="busy"
        :loading="providerLoading"
        @click="emit('action', { type: 'remove-provider', item })"
      />
    </div>
    <div
      v-else-if="item.source === 'mine' && item.shot.id != null"
      class="za-shot__actions d-flex flex-wrap ga-1"
    >
      <MediaManagementAction
        :icon="item.shot.isPublic ? 'mdi-lock-open-variant' : 'mdi-lock'"
        :caption="
          t(item.shot.isPublic ? 'rom.screenshot-public' : 'rom.private')
        "
        :label="visibilityLabel"
        :pressed="Boolean(item.shot.isPublic)"
        :disabled="busy"
        :loading="visibilityLoading"
        @click="
          emit('action', {
            type: 'visibility',
            item,
            isPublic: !item.shot.isPublic,
          })
        "
      />
      <MediaManagementAction
        icon="mdi-delete-outline"
        tone="danger"
        :caption="t('common.delete')"
        :label="t('common.delete')"
        :disabled="busy"
        :loading="deletionLoading"
        @click="emit('action', { type: 'delete-mine', item })"
      />
    </div>
  </MediaManagementCard>
</template>

<style scoped src="./mediaManagementCard.css" />
