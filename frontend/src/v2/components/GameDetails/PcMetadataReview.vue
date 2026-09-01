<script setup lang="ts">
import { RAlert, RBtn, RDialog, REmptyState, RImg, RTag } from "@v2/lib";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import type {
  PcMetadataCandidateSchema,
  PcMetadataCandidatesResponse,
} from "@/__generated__";
import romApi from "@/services/api/rom";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ romId: number }>();
const emit = defineEmits<{ (event: "applied"): void }>();

const { t } = useI18n();
const snackbar = useSnackbar();
const dialogOpen = ref(false);
const loading = ref(false);
const applying = ref(false);
const response = ref<PcMetadataCandidatesResponse | null>(null);
const selectedCandidateId = ref<string | null>(null);
const appliedCandidate = ref<PcMetadataCandidateSchema | null>(null);

const candidates = computed(() =>
  Object.values(response.value?.providers ?? {}).flatMap(
    (provider) => provider.candidates,
  ),
);
const providerFailures = computed(() =>
  Object.values(response.value?.providers ?? {}).filter(
    (provider) => !provider.available,
  ),
);
const selectedCandidate = computed(
  () =>
    candidates.value.find(
      (candidate) => candidate.id === selectedCandidateId.value,
    ) ?? null,
);
const selectedLaunchboxMedia = computed(() =>
  appliedCandidate.value?.provider === "launchbox"
    ? (appliedCandidate.value.media[0] ?? null)
    : null,
);

async function findMetadata() {
  dialogOpen.value = true;
  loading.value = true;
  response.value = null;
  selectedCandidateId.value = null;
  appliedCandidate.value = null;
  try {
    const { data } = await romApi.getPcMetadataCandidates({
      romId: props.romId,
    });
    response.value = data;
  } catch (error) {
    console.error(error);
    snackbar.error(t("rom.pc-metadata-source-unavailable"));
  } finally {
    loading.value = false;
  }
}

async function applySelection() {
  if (!selectedCandidate.value || !response.value) return;
  applying.value = true;
  try {
    await romApi.selectPcMetadataCandidate({
      romId: props.romId,
      selection: {
        candidate_id: selectedCandidate.value.id,
        expected_version: response.value.expected_version,
      },
    });
    appliedCandidate.value = selectedCandidate.value;
    emit("applied");
  } catch (error) {
    console.error(error);
    snackbar.error(t("rom.pc-metadata-source-unavailable"));
  } finally {
    applying.value = false;
  }
}
</script>

<template>
  <div class="pc-metadata-review">
    <RBtn
      data-testid="find-pc-metadata"
      prepend-icon="mdi-magnify"
      @click="findMetadata"
    >
      {{ t("rom.pc-find-metadata") }}
    </RBtn>

    <RDialog v-model="dialogOpen">
      <template #header>{{ t("rom.pc-find-metadata") }}</template>
      <template #content>
        <div class="pc-metadata-review__body">
          <RAlert
            v-for="provider in providerFailures"
            :key="provider.provider"
            tone="warning"
          >
            {{ t("rom.pc-metadata-source-unavailable") }}
          </RAlert>

          <REmptyState
            v-if="!loading && candidates.length === 0"
            icon="mdi-database-search-outline"
            :title="t('rom.pc-no-metadata-matches')"
          />

          <div v-else class="pc-metadata-review__candidates">
            <button
              v-for="candidate in candidates"
              :key="candidate.id"
              :data-testid="`pc-candidate-${candidate.id}`"
              class="pc-metadata-review__candidate"
              :class="{
                'pc-metadata-review__candidate--selected':
                  candidate.id === selectedCandidateId,
              }"
              type="button"
              @click="selectedCandidateId = candidate.id"
            >
              <span>{{ candidate.title }}</span>
              <RTag :text="candidate.provider" />
            </button>
          </div>

          <div v-if="selectedLaunchboxMedia" class="pc-metadata-review__media">
            <RImg
              :src="selectedLaunchboxMedia.url"
              :alt="appliedCandidate?.title"
            />
            <RTag text="LaunchBox" />
          </div>

          <RBtn
            data-testid="apply-pc-metadata"
            :disabled="!selectedCandidate || applying"
            :loading="applying"
            @click="applySelection"
          >
            {{ t("rom.pc-apply-selected-metadata") }}
          </RBtn>
        </div>
      </template>
    </RDialog>
  </div>
</template>

<style scoped>
.pc-metadata-review__body,
.pc-metadata-review__candidates {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.pc-metadata-review__candidate {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--r-space-4);
  width: 100%;
  min-height: var(--r-touch-target);
  padding: var(--r-space-4);
  color: var(--r-color-fg);
  text-align: left;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}

.pc-metadata-review__candidate:hover,
.pc-metadata-review__candidate--selected {
  background: color-mix(in srgb, var(--r-color-brand-primary) 14%, transparent);
  border-color: var(--r-color-brand-primary);
}

.pc-metadata-review__media {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
}

.pc-metadata-review__media :deep(.r-img) {
  width: 10rem;
  border-radius: var(--r-radius-md);
}
</style>
