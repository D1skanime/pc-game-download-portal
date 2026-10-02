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
import storePcAutomation from "@/stores/pcAutomation";
import type { Events } from "@/types/emitter";
import type {
  PcMatchTarget,
  PcMatchableComponentKind,
} from "@/v2/components/MatchRom/types";
import SettingsSection from "@/v2/components/Settings/SettingsSection.vue";
import { useCan } from "@/v2/composables/useCan";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const queue = storePcAutomation();
const snackbar = useSnackbar();
const emitter = inject<Emitter<Events>>("emitter");
const canReview = useCan("rom.edit");

const selectedCount = computed(() => queue.selection.size);
const selectedGroupIsSafe = computed(() => queue.selectedGroupIsSafe);

function queueError(error: unknown) {
  return (
    (error as { response?: { data?: { detail?: string } } })?.response?.data
      ?.detail ?? t("pc-automation.request-failed")
  );
}

function componentTarget(
  item: PcAutomationQueueItemSchema,
): PcMatchTarget | null {
  if (item.target_kind === "parent") {
    return {
      kind: "rom",
      romId: item.rom_id,
      label: item.candidate_title ?? t("pc-automation.unnamed-candidate"),
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
      label: item.candidate_title ?? t("pc-automation.unnamed-candidate"),
    };
  }

  return {
    kind: "component",
    romId: item.rom_id,
    componentId: item.component_id,
    componentKind: item.component_kind as PcMatchableComponentKind,
    label: item.candidate_title ?? t("pc-automation.unnamed-candidate"),
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
    snackbar.success(t("pc-automation.accepted"), { icon: "mdi-check-bold" });
  } catch (error) {
    snackbar.error(queueError(error), { icon: "mdi-close-circle" });
  }
}

async function skip(item: PcAutomationQueueItemSchema) {
  try {
    await queue.skip(item);
    snackbar.success(t("pc-automation.skipped"), { icon: "mdi-check-bold" });
  } catch (error) {
    snackbar.error(queueError(error), { icon: "mdi-close-circle" });
  }
}

async function batchAccept() {
  if (!selectedGroupIsSafe.value) return;
  try {
    await queue.batchAccept();
    snackbar.success(t("pc-automation.batch-accepted"), {
      icon: "mdi-check-bold",
    });
  } catch (error) {
    snackbar.error(queueError(error), { icon: "mdi-close-circle" });
  }
}

function correct(item: PcAutomationQueueItemSchema) {
  const target = componentTarget(item);
  if (!target) {
    snackbar.error(t("pc-automation.correction-unavailable"), {
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
    :title="t('pc-automation.title')"
    icon="mdi-robot-outline"
  >
    <div class="r-v2-pc-automation__summary">
      <span>{{
        t("pc-automation.outstanding", { count: queue.outstandingCount })
      }}</span>
      <RProgressLinear
        :model-value="queue.progress"
        :aria-label="t('pc-automation.progress')"
      />
    </div>

    <div v-if="queue.loading && queue.items.length === 0" class="pa-4">
      <RSkeletonBlock height="96" />
    </div>

    <div
      v-else-if="queue.error && queue.items.length === 0"
      class="r-v2-pc-automation__empty"
    >
      <p>{{ t("pc-automation.load-failed") }}</p>
      <RBtn variant="outlined" @click="loadQueue(true)">
        {{ t("common.retry") }}
      </RBtn>
    </div>

    <div v-else-if="queue.items.length === 0" class="r-v2-pc-automation__empty">
      {{ t("pc-automation.empty") }}
    </div>

    <template v-else>
      <div class="r-v2-pc-automation__batch">
        <span>{{ t("pc-automation.selected", { count: selectedCount }) }}</span>
        <RBtn
          :disabled="!selectedGroupIsSafe"
          :loading="queue.batchLoading"
          prepend-icon="mdi-check-all"
          @click="batchAccept"
        >
          {{ t("pc-automation.accept-selected") }}
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
              t('pc-automation.select-row', { title: item.candidate_title })
            "
            bare
            @update:model-value="queue.toggleSelection(item.id)"
          />
          <RImg
            class="r-v2-pc-automation__cover"
            :src="item.candidate_cover_url ?? undefined"
            :alt="item.candidate_title ?? t('pc-automation.unnamed-candidate')"
          />
          <div class="r-v2-pc-automation__details">
            <strong>{{
              item.candidate_title ?? t("pc-automation.unnamed-candidate")
            }}</strong>
            <span>{{ item.reason ?? t("pc-automation.review-required") }}</span>
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
                t('pc-automation.accept', { title: item.candidate_title })
              "
              :tooltip="
                t('pc-automation.accept', { title: item.candidate_title })
              "
              @click="accept(item)"
            />
            <RBtn
              icon="mdi-magnify"
              :disabled="componentTarget(item) === null"
              :aria-label="
                t('pc-automation.correct', { title: item.candidate_title })
              "
              :tooltip="
                t('pc-automation.correct', { title: item.candidate_title })
              "
              @click="correct(item)"
            />
            <RBtn
              icon="mdi-skip-next"
              :loading="queue.actionLoadingIds.has(item.id)"
              :aria-label="
                t('pc-automation.skip', { title: item.candidate_title })
              "
              :tooltip="
                t('pc-automation.skip', { title: item.candidate_title })
              "
              @click="skip(item)"
            />
          </div>
        </article>
      </div>

      <div v-if="queue.hasMore" class="r-v2-pc-automation__load-more">
        <RBtn :loading="queue.loading" variant="outlined" @click="loadQueue()">
          {{ t("pc-automation.load-more") }}
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
