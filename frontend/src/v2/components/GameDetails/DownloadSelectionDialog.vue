<script setup lang="ts">
import { RBtn, RCheckbox, RCollapsible, RDialog } from "@v2/lib";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { PcComponentSchema } from "@/__generated__";
import { formatBytes } from "@/utils";
import DownloadModeSelector from "./DownloadModeSelector.vue";

export type DownloadArchiveSet = {
  id: number;
  name: string;
  members: Array<{
    component_id: number;
    manifest_member_id: number;
    position: number;
    required: boolean;
  }>;
};
const props = defineProps<{
  modelValue: boolean;
  components: PcComponentSchema[];
  archiveSets?: DownloadArchiveSet[];
}>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (
    e: "start",
    payload: {
      archiveSetId?: number;
      selectedMemberIds: number[];
      componentIds: number[];
      mode: "standard" | "enhanced";
    },
  ): void;
}>();
const { t } = useI18n();
const selectedSet = ref<number | undefined>();
const selectedOptional = ref<number[]>([]);
const selectedMemberIds = ref<number[]>([]);
const expandedComponentIds = ref<number[]>([]);
const mode = ref<"standard" | "enhanced">("standard");
const currentSet = computed(() =>
  props.archiveSets?.find((set) => set.id === selectedSet.value),
);
const selectedMembers = computed(() =>
  currentSet.value
    ? currentSet.value.members
        .filter(
          (member) =>
            member.required ||
            selectedOptional.value.includes(member.manifest_member_id),
        )
        .sort((a, b) => a.position - b.position)
        .map((member) => member.manifest_member_id)
    : selectedMemberIds.value,
);
const selectedComponentIds = computed(() =>
  currentSet.value
    ? [
        ...new Set(
          currentSet.value.members
            .filter((member) =>
              selectedMembers.value.includes(member.manifest_member_id),
            )
            .map((member) => member.component_id),
        ),
      ]
    : props.components
        .filter((component) =>
          component.manifest_members.some((member) =>
            selectedMembers.value.includes(member.id),
          ),
        )
        .map((component) => component.id),
);
const selectedBytes = computed(() =>
  props.components
    .flatMap((component) => component.manifest_members)
    .filter((member) => selectedMembers.value.includes(member.id))
    .reduce((total, member) => total + member.size_bytes, 0),
);
const missing = computed(
  () =>
    currentSet.value?.members.filter(
      (member) =>
        member.required &&
        !props.components.some(
          (component) => component.id === member.component_id,
        ),
    ) ?? [],
);
const selectionInvalid = computed(
  () => missing.value.length > 0 || selectedMembers.value.length === 0,
);
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      selectedSet.value = props.archiveSets?.[0]?.id;
      selectedOptional.value = [];
      expandedComponentIds.value = [];
      selectedMemberIds.value = props.archiveSets?.length
        ? []
        : props.components.flatMap((component) =>
            component.manifest_members.map((member) => member.id),
          );
      mode.value = "standard";
    }
  },
);
function start() {
  if (selectionInvalid.value) return;
  emit("start", {
    archiveSetId: selectedSet.value,
    selectedMemberIds: selectedMembers.value,
    componentIds: selectedComponentIds.value,
    mode: mode.value,
  });
  emit("update:modelValue", false);
}
const componentKindLabels: Record<PcComponentSchema["kind"], string> = {
  base: "rom.pc-base-game",
  update: "rom.pc-updates",
  dlc: "rom.category-dlc",
  hotfix: "rom.pc-hotfixes",
  language_pack: "rom.pc-language-packs",
  extra: "rom.pc-extras",
  unresolved: "rom.pc-needs-classification",
};
function memberComponentLabel(componentId: number) {
  const component = props.components.find((item) => item.id === componentId);
  return component ? t(componentKindLabels[component.kind]) : t("file");
}
function componentFilesExpanded(componentId: number) {
  return expandedComponentIds.value.includes(componentId);
}
function setComponentFilesExpanded(componentId: number, expanded: boolean) {
  expandedComponentIds.value = expanded
    ? [...new Set([...expandedComponentIds.value, componentId])]
    : expandedComponentIds.value.filter((id) => id !== componentId);
}
</script>
<template>
  <RDialog
    :model-value="modelValue"
    icon="mdi-download"
    scroll-content
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>{{ t("rom.download-game") }}</template>
    <template #content>
      <div class="download-selection">
        <DownloadModeSelector v-model="mode" />
        <RCheckbox
          v-for="set in archiveSets"
          :key="set.id"
          :model-value="selectedSet === set.id"
          :label="set.name"
          variant="card"
          @update:model-value="selectedSet = set.id"
        />
        <div v-if="!archiveSets?.length" class="download-selection__files">
          <div
            v-for="component in components"
            :key="component.id"
            class="download-selection__component"
          >
            <RCheckbox
              :model-value="
                component.manifest_members.some((member) =>
                  selectedMemberIds.includes(member.id),
                )
              "
              :label="
                component.kind === 'base'
                  ? t('rom.pc-base-game')
                  : component.relative_path
              "
              variant="card"
              @update:model-value="
                (checked) =>
                  (selectedMemberIds = checked
                    ? [
                        ...new Set([
                          ...selectedMemberIds,
                          ...component.manifest_members.map(
                            (member) => member.id,
                          ),
                        ]),
                      ]
                    : selectedMemberIds.filter(
                        (id) =>
                          !component.manifest_members.some(
                            (member) => member.id === id,
                          ),
                      ))
              "
            />
            <RCollapsible
              v-if="component.manifest_members.length"
              :model-value="componentFilesExpanded(component.id)"
              :title="t('details')"
              attached
              :data-testid="`download-component-files-${component.id}`"
              @update:model-value="
                setComponentFilesExpanded(component.id, $event)
              "
            >
              <div class="download-selection__member-list">
                <RCheckbox
                  v-for="member in component.manifest_members"
                  :key="`file-${member.id}`"
                  :model-value="selectedMemberIds.includes(member.id)"
                  :label="`${member.relative_path} (${formatBytes(member.size_bytes)})`"
                  @update:model-value="
                    (checked) =>
                      (selectedMemberIds = checked
                        ? [...selectedMemberIds, member.id]
                        : selectedMemberIds.filter((id) => id !== member.id))
                  "
                />
              </div>
            </RCollapsible>
          </div>
        </div>
        <p v-if="missing.length" role="alert">
          {{ t("rom.download-required-missing") }}
        </p>
        <RCheckbox
          v-for="member in currentSet?.members.filter(
            (entry) => !entry.required,
          )"
          :key="member.manifest_member_id"
          :model-value="selectedOptional.includes(member.manifest_member_id)"
          :label="`${t('rom.download-optional-file')} ${memberComponentLabel(
            member.component_id,
          )}`"
          @update:model-value="
            (memberValue) =>
              memberValue
                ? selectedOptional.push(member.manifest_member_id)
                : (selectedOptional = selectedOptional.filter(
                    (id) => id !== member.manifest_member_id,
                  ))
          "
        />
      </div>
    </template>
    <template #footer>
      <span
        v-if="!archiveSets?.length"
        class="download-selection__total"
        data-testid="download-selected-total"
        >{{ t("rom.download-selected") }}:
        {{ formatBytes(selectedBytes) }}</span
      >
      <RBtn variant="text" @click="emit('update:modelValue', false)">{{
        t("common.cancel")
      }}</RBtn>
      <RBtn :disabled="selectionInvalid" @click="start">{{
        t("rom.download-start")
      }}</RBtn>
    </template>
  </RDialog>
</template>
<style scoped>
.download-selection {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.download-selection__files,
.download-selection__member-list {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
}

.download-selection__component {
  display: flex;
  flex-direction: column;
}

.download-selection__member-list {
  padding: var(--r-space-3) var(--r-space-4);
}

.download-selection__total {
  margin-right: auto;
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-sm);
}
</style>
