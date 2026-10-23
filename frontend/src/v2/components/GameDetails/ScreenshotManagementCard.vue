<script setup lang="ts">
import { RAvatar, RBtn, RIcon } from "@v2/lib";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { RomOwnedMediaSchema } from "@/__generated__";
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
const failed = ref(false);
const url = computed(() =>
  props.item.source === "provider" ? props.item.url : props.item.shot.url,
);
watch(url, () => {
  failed.value = false;
});
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
  <article class="za-shot" :class="{ 'za-shot--new': newlyUploaded }">
    <button
      type="button"
      class="za-shot__preview"
      data-preview
      :aria-label="
        item.source === 'provider'
          ? item.media.display_label
          : t('rom.screenshots')
      "
      @click="emit('action', { type: 'preview', item })"
    >
      <span v-if="failed" class="za-shot__fallback">{{
        t("rom.screenshots-preview-unavailable")
      }}</span>
      <img
        v-else
        :src="url"
        :alt="
          item.source === 'provider'
            ? item.media.display_label
            : t('rom.screenshots')
        "
        loading="lazy"
        @error="failed = true"
      />
    </button>
    <div class="za-shot__body d-flex flex-column">
      <span class="za-shot__source" :title="sourceLabel">{{
        sourceLabel
      }}</span>
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
        <RBtn
          v-for="surface in surfaces"
          :key="surface"
          size="small"
          class="za-shot__action"
          :style="{
            '--za-action-accent':
              surface === 'overview'
                ? 'var(--r-color-brand-primary)'
                : 'var(--r-color-info)',
          }"
          :class="{
            'za-shot__action--selected': position(surface) !== undefined,
          }"
          :loading="providerLoading"
          variant="translucent"
          border
          :color="
            surface === 'overview'
              ? 'var(--r-color-brand-primary)'
              : 'var(--r-color-info)'
          "
          :aria-pressed="position(surface) !== undefined"
          :aria-label="placementLabel(surface)"
          :tooltip="placementLabel(surface)"
          :disabled="busy"
          @click="emit('action', { type: 'placement', item, surface })"
        >
          <span class="za-shot__action-content">
            <span class="za-shot__identity">
              <RIcon
                :icon="
                  surface === 'overview'
                    ? 'mdi-crown-outline'
                    : 'mdi-image-outline'
                "
                size="18"
              />
              <RIcon
                v-if="position(surface) !== undefined"
                class="za-shot__check"
                icon="mdi-check"
                size="10"
                aria-hidden="true"
              />
            </span>
            <span>{{ t(`rom.screenshots-action-${surface}`) }}</span>
          </span>
        </RBtn>
        <RBtn
          size="small"
          class="za-shot__action za-shot__action--danger"
          variant="outlined"
          color="var(--r-color-danger)"
          :disabled="busy"
          :aria-label="t('rom.provider-screenshot-remove-title')"
          :tooltip="t('rom.provider-screenshot-remove-title')"
          :loading="providerLoading"
          @click="emit('action', { type: 'remove-provider', item })"
        >
          <span class="za-shot__action-content">
            <RIcon icon="mdi-delete-outline" size="18" />
            <span>{{ t("common.delete") }}</span>
          </span>
        </RBtn>
      </div>
      <div
        v-else-if="item.source === 'mine' && item.shot.id != null"
        class="za-shot__actions d-flex flex-wrap ga-1"
      >
        <RBtn
          size="small"
          class="za-shot__action"
          variant="translucent"
          border
          :disabled="busy"
          :aria-label="visibilityLabel"
          :tooltip="visibilityLabel"
          :loading="visibilityLoading"
          :aria-pressed="Boolean(item.shot.isPublic)"
          @click="
            emit('action', {
              type: 'visibility',
              item,
              isPublic: !item.shot.isPublic,
            })
          "
        >
          <span class="za-shot__action-content">
            <RIcon
              :icon="item.shot.isPublic ? 'mdi-lock-open-variant' : 'mdi-lock'"
              size="18"
            />
            <span>{{
              t(item.shot.isPublic ? "rom.screenshot-public" : "rom.private")
            }}</span>
          </span>
        </RBtn>
        <RBtn
          size="small"
          class="za-shot__action za-shot__action--danger"
          variant="outlined"
          color="var(--r-color-danger)"
          :disabled="busy"
          :aria-label="t('common.delete')"
          :tooltip="t('common.delete')"
          :loading="deletionLoading"
          @click="emit('action', { type: 'delete-mine', item })"
        >
          <span class="za-shot__action-content">
            <RIcon icon="mdi-delete-outline" size="18" />
            <span>{{ t("common.delete") }}</span>
          </span>
        </RBtn>
      </div>
    </div>
  </article>
</template>

<style scoped>
.za-shot {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-card);
  background: var(--r-color-bg-elevated);
  backdrop-filter: blur(var(--r-space-2));
  font-size: var(--r-font-size-md);
  line-height: var(--r-line-height-normal);
}
.za-shot--new {
  border-color: var(--r-color-brand-primary);
}
.za-shot__preview {
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 16 / 9;
  padding: 0;
  border: 0;
  border-radius: var(--r-radius-art);
  background: var(--r-color-cover-placeholder);
  color: var(--r-color-fg);
  cursor: pointer;
}
.za-shot__preview img {
  display: block;
  width: 100%;
  height: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}
.za-shot__fallback {
  padding: var(--r-space-2);
}
.za-shot__body {
  min-width: 0;
  gap: var(--r-space-2);
  padding: var(--r-space-2);
}
.za-shot__source {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--r-color-fg-muted);
}
.za-shot__badge {
  padding: 0 var(--r-space-1);
  border-radius: var(--r-radius-md);
}
.za-shot__badge--overview,
.za-shot__new {
  color: var(--r-color-brand-primary);
  background: color-mix(in srgb, var(--r-color-brand-primary) 12%, transparent);
}
.za-shot__badge--background {
  color: var(--r-color-info);
  background: color-mix(in srgb, var(--r-color-info) 12%, transparent);
}
.za-shot__actions {
  min-width: 0;
}
/* Touch compatibility mouse events must not shrink action hit targets. */
.za-shot__actions :deep(button) {
  min-width: var(--r-touch-target);
  min-height: var(--r-touch-target);
}
.za-shot__action.r-btn {
  --za-action-accent: var(--r-color-brand-primary);
  flex: 1 1 auto;
  min-width: var(--r-touch-target);
  height: auto;
  padding: var(--r-space-2) var(--r-space-1);
  color: var(--za-action-accent);
  background: color-mix(in srgb, var(--za-action-accent) 6%, transparent);
  border: 1px solid
    color-mix(in srgb, var(--za-action-accent) 22%, var(--r-color-border));
  border-radius: var(--r-radius-md);
  font-size: var(--r-font-size-xs);
  letter-spacing: normal;
}
.za-shot__action-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--r-space-1);
  min-width: 0;
  line-height: var(--r-line-height-tight);
  white-space: normal;
  overflow-wrap: normal;
}
.za-shot__action.r-btn.za-shot__action--selected:not(:disabled) {
  background: color-mix(
    in srgb,
    var(--za-action-accent) 18%,
    var(--r-color-surface)
  );
  border-color: color-mix(
    in srgb,
    var(--za-action-accent) 70%,
    var(--r-color-border)
  );
}
.za-shot__identity {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 18px;
}
.za-shot__check {
  position: absolute;
  right: -3px;
  bottom: -2px;
}
.za-shot__action.r-btn.za-shot__action--danger {
  --za-action-accent: var(--r-color-danger);
}
</style>
