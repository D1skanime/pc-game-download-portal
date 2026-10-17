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
            data-testid="pc-automation-select"
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
          <div
            class="r-v2-pc-automation__details"
            data-testid="pc-automation-content"
          >
            <div class="r-v2-pc-automation__identity">
              <h3 data-testid="pc-automation-title">
                {{ targetTitle(item) }}
              </h3>
              <p
                v-if="proposedTitle(item) !== null"
                class="r-v2-pc-automation__candidate-title"
              >
                {{ proposedTitle(item) }}
              </p>
            </div>
            <div
              class="r-v2-pc-automation__source-details"
              data-testid="pc-automation-source-details"
            >
              <div
                v-for="field in [
                  {
                    label: t('settings.pc-automation.source-name'),
                    value: item.source_name,
                  },
                  {
                    label: t('settings.pc-automation.source-path'),
                    value: item.source_path,
                  },
                  {
                    label: t('settings.pc-automation.main-game'),
                    value: item.main_game_label,
                  },
                ]"
                :key="field.label"
                class="r-v2-pc-automation__source-field"
                data-testid="pc-automation-source-field"
              >
                <span class="r-v2-pc-automation__source-label">
                  {{ field.label }}:
                </span>
                <span>{{ field.value }}</span>
              </div>
            </div>
            <details
              class="r-v2-pc-automation__reason"
              data-testid="pc-automation-reason"
            >
              <summary>
                {{ t("settings.pc-automation.review-required") }}
              </summary>
              <p>
                {{ item.reason ?? t("settings.pc-automation.review-required") }}
              </p>
            </details>
            <div
              class="r-v2-pc-automation__tags"
              data-testid="pc-automation-tags"
            >
              <RChip size="small">{{ item.target_kind }}</RChip>
              <RChip v-if="item.component_kind" size="small">{{
                item.component_kind
              }}</RChip>
              <RChip v-if="item.provider" size="small">{{
                item.provider
              }}</RChip>
            </div>
          </div>
          <div
            class="r-v2-pc-automation__actions"
            data-testid="pc-automation-actions"
          >
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
.r-v2-pc-automation__actions,
.r-v2-pc-automation__tags {
  display: flex;
  align-items: center;
}

.r-v2-pc-automation__summary {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  padding: 12px var(--r-row-pad);
}

.r-v2-pc-automation__batch {
  justify-content: space-between;
  gap: 12px;
  padding: 10px var(--r-row-pad);
  border-top: 1px solid var(--r-color-border);
}

.r-v2-pc-automation__row {
  display: grid;
  grid-template-columns: auto 48px minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
  padding: 12px var(--r-row-pad);
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
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--r-color-fg-muted);
}

.r-v2-pc-automation__identity {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.r-v2-pc-automation__identity h3 {
  margin: 0;
  color: var(--r-color-fg);
  font-size: 1.05rem;
  line-height: 1.3;
}

.r-v2-pc-automation__candidate-title {
  margin: 0;
}

.r-v2-pc-automation__source-details {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--r-color-border);
}

.r-v2-pc-automation__source-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: var(--r-font-size-sm);
}

.r-v2-pc-automation__source-label {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.r-v2-pc-automation__reason {
  font-size: var(--r-font-size-sm);
}

.r-v2-pc-automation__reason summary {
  width: fit-content;
  color: var(--r-color-fg-secondary);
  cursor: pointer;
  font-weight: var(--r-font-weight-semibold);
}

.r-v2-pc-automation__reason p {
  margin: 8px 0 0;
}

.r-v2-pc-automation__tags {
  flex-wrap: wrap;
  gap: 4px;
}

.r-v2-pc-automation__actions {
  align-self: center;
  justify-content: flex-end;
  gap: 6px;
  padding-left: 8px;
}

.r-v2-pc-automation__load-more,
.r-v2-pc-automation__empty {
  padding: 16px var(--r-row-pad);
  text-align: center;
}

html[data-bp~="xs"] .r-v2-pc-automation__row {
  grid-template-columns: auto 48px minmax(0, 1fr);
}

html[data-bp~="xs"] .r-v2-pc-automation__source-details {
  grid-template-columns: 1fr;
  gap: 8px;
}
html[data-bp~="xs"] .r-v2-pc-automation__actions {
  grid-column: 3 / -1;
  grid-row: auto;
  justify-content: flex-start;
  flex-wrap: wrap;
  padding-left: 0;
}
</style>
