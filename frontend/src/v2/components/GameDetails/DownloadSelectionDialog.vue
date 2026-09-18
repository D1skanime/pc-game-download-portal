<script setup lang="ts">
import { RBtn, RCheckbox, RDialog } from "@v2/lib";
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
          <template v-for="component in components" :key="component.id">
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
          </template>
        </div>
        <p v-if="!archiveSets?.length" data-testid="download-selected-total">
          {{ formatBytes(selectedBytes) }}
        </p>
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
    <template #footer
      ><RBtn variant="text" @click="emit('update:modelValue', false)">{{
        t("common.cancel")
      }}</RBtn
      ><RBtn :disabled="selectionInvalid" @click="start">{{
        t("rom.download-start")
      }}</RBtn></template
    >
  </RDialog>
</template>
