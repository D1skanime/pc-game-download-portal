<script setup lang="ts">
import { RBtn, RDialog, REmptyState, RImg, RTag } from "@v2/lib";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import type {
  PcLocalMediaCandidatesResponse,
  RomComponentLocalMediaRole,
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
const response = ref<PcLocalMediaCandidatesResponse | null>(null);
const selectedCandidate = ref<
  PcLocalMediaCandidatesResponse["candidates"][number] | null
>(null);
const selectedRole = ref<RomComponentLocalMediaRole | null>(null);

const canApply = computed(
  () => selectedCandidate.value !== null && selectedRole.value !== null,
);

function roleLabel(role: RomComponentLocalMediaRole) {
  if (role === "cover") return t("collection.cover");
  if (role === "gallery") return t("settings.gallery");
  return t("play.background-color");
}

async function openReview() {
  dialogOpen.value = true;
  loading.value = true;
  response.value = null;
  selectedCandidate.value = null;
  selectedRole.value = null;
  try {
    const { data } = await romApi.getPcLocalMediaCandidates({
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
  if (!selectedCandidate.value || !selectedRole.value || !response.value)
    return;
  applying.value = true;
  try {
    await romApi.selectPcLocalMedia({
      romId: props.romId,
      selection: {
        component_id: selectedCandidate.value.component_id,
        member_id: selectedCandidate.value.member_id,
        role: selectedRole.value,
        expected_version: response.value.expected_version,
      },
    });
    dialogOpen.value = false;
    snackbar.success(t("common.apply"));
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
  <RBtn
    data-testid="select-local-artwork"
    prepend-icon="mdi-image-plus-outline"
    @click="openReview"
  >
    {{ t("rom.artwork") }}
  </RBtn>

  <RDialog v-model="dialogOpen">
    <template #header>{{ t("rom.artwork") }}</template>
    <template #content>
      <div class="pc-local-media-review">
        <REmptyState
          v-if="!loading && response?.candidates.length === 0"
          icon="mdi-image-off-outline"
          :title="t('rom.pc-no-components')"
        />

        <div v-else class="pc-local-media-review__candidates">
          <button
            v-for="candidate in response?.candidates ?? []"
            :key="candidate.member_id"
            :data-testid="`local-art-candidate-${candidate.component_id}-${candidate.member_id}`"
            class="pc-local-media-review__candidate"
            :class="{
              'pc-local-media-review__candidate--selected':
                selectedCandidate?.member_id === candidate.member_id,
            }"
            type="button"
            :aria-pressed="selectedCandidate?.member_id === candidate.member_id"
            @click="selectedCandidate = candidate"
          >
            <RImg
              class="pc-local-media-review__preview"
              :src="candidate.preview_url"
              :alt="candidate.relative_path"
            />
            <span class="pc-local-media-review__evidence">
              {{ candidate.relative_path }}
            </span>
            <RTag :text="candidate.image_type.toUpperCase()" />
          </button>
        </div>

        <div class="pc-local-media-review__roles">
          <RBtn
            v-for="role in [
              'cover',
              'background',
              'gallery',
            ] as RomComponentLocalMediaRole[]"
            :key="role"
            :data-testid="`local-art-role-${role}`"
            :variant="selectedRole === role ? 'flat' : 'outlined'"
            :disabled="!selectedCandidate"
            @click="selectedRole = role"
          >
            {{ roleLabel(role) }}
          </RBtn>
        </div>

        <RBtn
          data-testid="apply-local-artwork"
          :disabled="!canApply || applying"
          :loading="applying"
          @click="applySelection"
        >
          {{ t("common.apply") }}
        </RBtn>
      </div>
    </template>
  </RDialog>
</template>

<style scoped>
.pc-local-media-review,
.pc-local-media-review__candidates,
.pc-local-media-review__roles {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.pc-local-media-review__candidate {
  display: grid;
  grid-template-columns: 8rem 1fr auto;
  gap: var(--r-space-3);
  align-items: center;
  width: 100%;
  min-height: var(--r-touch-target);
  padding: var(--r-space-3);
  color: var(--r-color-fg);
  text-align: left;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}

.pc-local-media-review__candidate:hover,
.pc-local-media-review__candidate--selected {
  border-color: var(--r-color-brand-primary);
  background: color-mix(in srgb, var(--r-color-brand-primary) 14%, transparent);
}

.pc-local-media-review__preview {
  width: 8rem;
  height: 5rem;
  object-fit: contain;
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-sm);
}

.pc-local-media-review__evidence {
  overflow-wrap: anywhere;
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-sm);
}

.pc-local-media-review__roles {
  flex-direction: row;
  flex-wrap: wrap;
}

html[data-bp~="xs"] .pc-local-media-review__candidate {
  grid-template-columns: 1fr auto;
}

html[data-bp~="xs"] .pc-local-media-review__preview {
  grid-column: 1 / -1;
  width: 100%;
  height: 10rem;
}
</style>
