<script setup lang="ts">
import {
  RBtn,
  RCheckbox,
  RChip,
  RImg,
  RProgressLinear,
  RSkeletonBlock,
} from "@v2/lib";
import type { Emitter } from "mitt";
import { computed, inject, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import type { PcAutomationQueueItemSchema } from "@/__generated__";
import type { Events } from "@/types/emitter";
import type {
  PcMatchTarget,
  PcMatchableComponentKind,
} from "@/v2/components/MatchRom/types";
import SettingsSection from "@/v2/components/Settings/SettingsSection.vue";
import { useCan } from "@/v2/composables/useCan";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import storePcAutomation from "@/v2/data/adapters/legacy/stores/pcAutomation";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const queue = storePcAutomation();
const snackbar = useSnackbar();
const emitter = inject<Emitter<Events>>("emitter");
const canReview = useCan("rom.edit");

const selectedCount = computed(() => queue.selection.size);
const selectedGroupIsSafe = computed(() => queue.selectedGroupIsSafe);

function targetTitle(item: PcAutomationQueueItemSchema) {
  return (
    item.target_title?.trim() ||
    item.candidate_title?.trim() ||
    t("settings.pc-automation.unnamed-candidate")
  );
}

function proposedTitle(item: PcAutomationQueueItemSchema) {
  return item.candidate_title?.trim() ?? null;
}

function queueError(error: unknown) {
  return (
    (error as { response?: { data?: { detail?: string } } })?.response?.data
      ?.detail ?? t("settings.pc-automation.request-failed")
  );
}

function componentTarget(
  item: PcAutomationQueueItemSchema,
): PcMatchTarget | null {
  if (item.target_kind === "parent") {
    return {
      kind: "rom",
      romId: item.rom_id,
      label: targetTitle(item),
    };
  }

  if (
    item.component_id === null ||
    item.component_kind === null ||
    item.component_kind === "unresolved"
  ) {
    return null;
  }

  if (item.component_kind === "base") {
    return {
      kind: "rom",
      romId: item.rom_id,
      label: targetTitle(item),
    };
  }

  return {
    kind: "component",
    romId: item.rom_id,
    componentId: item.component_id,
    componentKind: item.component_kind as PcMatchableComponentKind,
    label: targetTitle(item),
  };
}

async function loadQueue(reset = false) {
  try {
    await queue.fetchQueue({ reset });
  } catch (error) {
    snackbar.error(queueError(error), { icon: "mdi-close-circle" });
  }
}

async function accept(item: PcAutomationQueueItemSchema) {
  try {
    await queue.accept(item);
    snackbar.success(t("settings.pc-automation.accepted"), {
      icon: "mdi-check-bold",
    });
  } catch (error) {
    snackbar.error(queueError(error), { icon: "mdi-close-circle" });
  }
}

async function skip(item: PcAutomationQueueItemSchema) {
  try {
    await queue.skip(item);
    snackbar.success(t("settings.pc-automation.skipped"), {
      icon: "mdi-check-bold",
    });
  } catch (error) {
    snackbar.error(queueError(error), { icon: "mdi-close-circle" });
  }
}

async function batchAccept() {
  if (!selectedGroupIsSafe.value) return;
  try {
    await queue.batchAccept();
    snackbar.success(t("settings.pc-automation.batch-accepted"), {
      icon: "mdi-check-bold",
    });
  } catch (error) {
    snackbar.error(queueError(error), { icon: "mdi-close-circle" });
  }
}

function correct(item: PcAutomationQueueItemSchema) {
  const target = componentTarget(item);
  if (!target) {
    snackbar.error(t("settings.pc-automation.correction-unavailable"), {
      icon: "mdi-close-circle",
    });
    return;
  }
  emitter?.emit("showPcMatchRomDialog", {
    target,
    refresh: () => loadQueue(true),
  });
}

onMounted(() => {
  void loadQueue(true);
});
</script>

<template>
  <SettingsSection
    v-if="canReview"
    data-testid="pc-automation-queue"
    :title="t('settings.pc-automation.title')"
    icon="mdi-robot-outline"
  >
    <div class="r-v2-pc-automation__summary">
      <span>{{
        t("settings.pc-automation.outstanding", {
          count: queue.outstandingCount,
        })
      }}</span>
      <RProgressLinear
        :model-value="queue.progress"
        :aria-label="t('settings.pc-automation.progress')"
      />
    </div>

    <div v-if="queue.loading && queue.items.length === 0" class="pa-4">
      <RSkeletonBlock height="96" />
    </div>

    <div
      v-else-if="queue.error && queue.items.length === 0"
      class="r-v2-pc-automation__empty"
    >
      <p>{{ t("settings.pc-automation.load-failed") }}</p>
      <RBtn variant="outlined" @click="loadQueue(true)">
        {{ t("common.retry") }}
      </RBtn>
    </div>

    <div v-else-if="queue.items.length === 0" class="r-v2-pc-automation__empty">
      {{ t("settings.pc-automation.empty") }}
    </div>

    <template v-else>
      <div class="r-v2-pc-automation__batch">
        <span>{{
          t("settings.pc-automation.selected", { count: selectedCount })
        }}</span>
        <RBtn
          :disabled="!selectedGroupIsSafe"
          :loading="queue.batchLoading"
          prepend-icon="mdi-check-all"
          @click="batchAccept"
        >
          {{ t("settings.pc-automation.accept-selected") }}
        </RBtn>
      </div>

      <div class="r-v2-pc-automation__rows">
        <article
          v-for="item in queue.items"
          :key="item.id"
          class="r-v2-pc-automation__row"
          :data-testid="`pc-automation-row-${item.id}`"
        >
          <RCheckbox
            :model-value="queue.selection.has(item.id)"
            :aria-label="
              t('settings.pc-automation.select-row', {
                title: targetTitle(item),
              })
            "
            bare
            @update:model-value="queue.toggleSelection(item.id)"
          />
          <RImg
            class="r-v2-pc-automation__cover"
            :src="item.candidate_cover_url ?? undefined"
            :alt="targetTitle(item)"
          />
          <div class="r-v2-pc-automation__details">
            <strong>{{ targetTitle(item) }}</strong>
            <span v-if="proposedTitle(item) !== null">
              {{ proposedTitle(item) }}
            </span>
            <span>{{
              item.reason ?? t("settings.pc-automation.review-required")
            }}</span>
            <div class="r-v2-pc-automation__tags">
              <RChip size="small">{{ item.target_kind }}</RChip>
              <RChip v-if="item.component_kind" size="small">{{
                item.component_kind
              }}</RChip>
              <RChip v-if="item.provider" size="small">{{
                item.provider
              }}</RChip>
            </div>
          </div>
          <div class="r-v2-pc-automation__actions">
            <RBtn
              icon="mdi-check"
              color="success"
              :loading="queue.actionLoadingIds.has(item.id)"
              :aria-label="
                t('settings.pc-automation.accept', {
                  title: targetTitle(item),
                })
              "
              :tooltip="
                t('settings.pc-automation.accept', {
                  title: targetTitle(item),
                })
              "
              @click="accept(item)"
            />
            <RBtn
              icon="mdi-magnify"
              :disabled="componentTarget(item) === null"
              :aria-label="
                t('settings.pc-automation.correct', {
                  title: targetTitle(item),
                })
              "
              :tooltip="
                t('settings.pc-automation.correct', {
                  title: targetTitle(item),
                })
              "
              @click="correct(item)"
            />
            <RBtn
              icon="mdi-skip-next"
              :loading="queue.actionLoadingIds.has(item.id)"
              :aria-label="
                t('settings.pc-automation.skip', {
                  title: targetTitle(item),
                })
              "
              :tooltip="
                t('settings.pc-automation.skip', {
                  title: targetTitle(item),
                })
              "
              @click="skip(item)"
            />
          </div>
        </article>
      </div>

      <div v-if="queue.hasMore" class="r-v2-pc-automation__load-more">
        <RBtn :loading="queue.loading" variant="outlined" @click="loadQueue()">
          {{ t("settings.pc-automation.load-more") }}
        </RBtn>
      </div>
    </template>
  </SettingsSection>
</template>

<style scoped>
.r-v2-pc-automation__summary,
.r-v2-pc-automation__batch,
.r-v2-pc-automation__row,
.r-v2-pc-automation__actions,
.r-v2-pc-automation__tags {
  display: flex;
  align-items: center;
}

.r-v2-pc-automation__summary {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  padding: 12px 16px;
}

.r-v2-pc-automation__batch {
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--r-color-border);
}

.r-v2-pc-automation__row {
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--r-color-border);
}

.r-v2-pc-automation__cover {
  width: 48px;
  height: 64px;
  flex: 0 0 auto;
  border-radius: var(--r-radius-sm);
  object-fit: cover;
}

.r-v2-pc-automation__details {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--r-color-fg-muted);
}

.r-v2-pc-automation__details strong {
  color: var(--r-color-fg);
}

.r-v2-pc-automation__tags,
.r-v2-pc-automation__actions {
  gap: 6px;
}

.r-v2-pc-automation__load-more,
.r-v2-pc-automation__empty {
  padding: 16px;
  text-align: center;
}

html[data-bp~="xs"] .r-v2-pc-automation__row {
  align-items: flex-start;
}

html[data-bp~="xs"] .r-v2-pc-automation__actions {
  flex-wrap: wrap;
}
</style>
