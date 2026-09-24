<script setup lang="ts">
import { RBtn, RCollapsible, REmptyState, RTag } from "@v2/lib";
import { isAxiosError } from "axios";
import type { Emitter } from "mitt";
import { computed, inject, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import type { PcComponentSchema } from "@/__generated__";
import type { DownloadManifestResponse } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import api from "@/services/api";
import type { Events } from "@/types/emitter";
import { formatBytes } from "@/utils";
import type { PcMatchableComponentKind } from "@/v2/components/MatchRom/types";
import { useBrowserDownloadQueue } from "@/v2/composables/useBrowserDownloadQueue";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import DownloadManager from "./DownloadManager.vue";
import DownloadSelectionDialog, {
  type DownloadArchiveSet,
} from "./DownloadSelectionDialog.vue";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  components: PcComponentSchema[];
  romId: number;
  archiveSets?: DownloadArchiveSet[];
}>();
const emit = defineEmits<{ (event: "applied"): void }>();
const { t } = useI18n();
const snackbar = useSnackbar();
const router = useRouter();
const emitter = inject<Emitter<Events>>("emitter");
const showDownload = ref(false);
const queue = useBrowserDownloadQueue();
const queueItems = computed(() => queue.items.value);
const selectedManifestId = ref<string | null>(null);
const selectedComponentLabels = ref<string[]>([]);
const currentSessionId = computed(() => queue.sessionId.value);

function openComponentMatcher(component: PcComponentSchema) {
  if (component.kind === "unresolved") return;
  emitter?.emit("showPcMatchRomDialog", {
    target: {
      kind: "component",
      romId: props.romId,
      componentId: component.id,
      componentKind: component.kind as PcMatchableComponentKind,
      label: componentLabel(component),
    },
    refresh: () => emit("applied"),
  });
}

function openDlcDetails(componentId: number) {
  void router.push({
    name: ROUTES.PC_DLC,
    params: { rom: props.romId, component: componentId },
  });
}

async function startDownload(payload: {
  archiveSetId?: number;
  selectedMemberIds: number[];
  componentIds: number[];
  mode: "standard" | "enhanced";
}) {
  // The File System Access picker must be opened while the click activation is
  // still alive. Waiting for the manifest request first makes Chromium reject
  // the picker with NotAllowedError.
  const selectedRoot =
    payload.mode === "enhanced" ? await queue.pickEnhancedDirectory() : null;
  if (payload.mode === "enhanced" && !selectedRoot) return;
  const response = await api.post<DownloadManifestResponse>(
    `/roms/${props.romId}/download-manifests`,
    {
      archive_set_id: payload.archiveSetId,
      selected_member_ids: payload.selectedMemberIds,
      component_ids: payload.archiveSetId ? undefined : payload.componentIds,
    },
  );
  selectedManifestId.value = response.data.id;
  selectedComponentLabels.value = response.data.components
    .map((entry) =>
      props.components.find((component) => component.id === entry.component_id),
    )
    .filter((component): component is PcComponentSchema => !!component)
    .map((component) => componentLabel(component));
  if (payload.mode === "enhanced") {
    await queue.startEnhanced(response.data, selectedRoot);
  } else {
    await queue.start(response.data);
  }
}

async function resumeDownload(transferId: string, memberId?: string) {
  try {
    await queue.resumeSession(transferId, memberId);
  } catch (error) {
    console.error("[PcComponents] Could not resume download", error);
    const expired =
      isAxiosError(error) &&
      (error.response?.status === 410 ||
        error.response?.data?.detail?.code === "manifest_expired");
    snackbar.error(
      expired
        ? t("rom.download-expired")
        : t("rom.download-failed-description"),
    );
  }
}

const COMPONENT_LABELS: Record<PcComponentSchema["kind"], string> = {
  base: "rom.pc-base-game",
  update: "rom.pc-updates",
  dlc: "rom.category-dlc",
  hotfix: "rom.pc-hotfixes",
  language_pack: "rom.pc-language-packs",
  extra: "rom.pc-extras",
  unresolved: "rom.pc-needs-classification",
};
function componentLabel(component: PcComponentSchema) {
  return t(COMPONENT_LABELS[component.kind]);
}

const GROUPS: Array<{ kind: PcComponentSchema["kind"]; label: string }> = [
  { kind: "base", label: "rom.pc-base-game" },
  { kind: "update", label: "rom.pc-updates" },
  { kind: "dlc", label: "rom.category-dlc" },
  { kind: "hotfix", label: "rom.pc-hotfixes" },
  { kind: "language_pack", label: "rom.pc-language-packs" },
  { kind: "extra", label: "rom.pc-extras" },
  { kind: "unresolved", label: "rom.pc-needs-classification" },
];

const groupedComponents = computed(() =>
  GROUPS.flatMap((group) => {
    const components = props.components.filter(
      (component) => component.kind === group.kind,
    );
    return components.length > 0
      ? [{ ...group, label: t(group.label), components }]
      : [];
  }),
);
</script>

<template>
  <section class="pc-components">
    <h3 class="pc-components__heading">{{ t("rom.game-downloads") }}</h3>
    <RBtn
      class="align-self-start"
      data-testid="download-components"
      prepend-icon="mdi-download"
      @click="showDownload = true"
      >{{ t("rom.download-game") }}</RBtn
    >
    <DownloadSelectionDialog
      v-model="showDownload"
      :components="components"
      :archive-sets="archiveSets"
      @start="startDownload"
    />
    <DownloadManager
      :rom-id="romId"
      :items="queueItems"
      :selected-manifest-id="selectedManifestId"
      :session-id="currentSessionId"
      :component-labels="selectedComponentLabels"
      @pause="queue.pause"
      @cancel="queue.cancel"
      @resume="queue.resume"
      @resume-session="resumeDownload"
      @clear-terminal="queue.clearTerminal"
    />

    <REmptyState
      v-if="groupedComponents.length === 0"
      icon="mdi-package-variant-closed"
      :title="t('rom.pc-no-components')"
    />

    <section
      v-for="group in groupedComponents"
      :key="group.kind"
      class="pc-components__group"
      data-testid="pc-component-group"
    >
      <h4 class="pc-components__group-heading">{{ group.label }}</h4>
      <RCollapsible
        v-for="component in group.components"
        :key="component.relative_path"
        :data-testid="`pc-component-${component.relative_path}`"
        :title="
          component.kind === 'base' ? group.label : component.relative_path
        "
        icon="mdi-folder-outline"
      >
        <div class="pc-components__manifest">
          <RBtn
            v-if="component.kind === 'dlc'"
            data-testid="open-pc-dlc-details"
            size="small"
            variant="text"
            @click="openDlcDetails(component.id)"
          >
            {{ t("common.details") }}
          </RBtn>
          <RBtn
            v-if="component.kind !== 'unresolved'"
            :data-testid="`find-pc-component-metadata-${component.id}`"
            size="small"
            variant="text"
            prepend-icon="mdi-magnify"
            @click="openComponentMatcher(component)"
          >
            {{ t("rom.pc-find-metadata") }}
          </RBtn>
          <div
            v-for="member in component.manifest_members"
            :key="member.relative_path"
            class="pc-components__member"
          >
            <span class="pc-components__path">{{ member.relative_path }}</span>
            <span class="pc-components__size">{{
              formatBytes(member.size_bytes)
            }}</span>
            <RTag label="SHA-256" :text="member.sha256" mono />
          </div>
        </div>
      </RCollapsible>
    </section>
  </section>
</template>

<style scoped>
.pc-components {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-6);
}

.pc-components__heading,
.pc-components__group-heading {
  margin: 0;
  color: var(--r-color-fg);
}

.pc-components__heading {
  font-size: var(--r-font-size-md);
  font-weight: var(--r-font-weight-semibold);
}

.pc-components__group {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.pc-components__group-heading {
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg-secondary);
}

.pc-components__manifest {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  padding: var(--r-space-4) var(--r-space-5);
}

.pc-components__member {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--r-space-3);
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-sm);
}

.pc-components__path {
  flex: 1 1 14rem;
  overflow-wrap: anywhere;
}

.pc-components__size {
  color: var(--r-color-fg-muted);
}
</style>
