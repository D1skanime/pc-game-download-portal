<script setup lang="ts">
import { RCollapsible, REmptyState, RTag } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { PcComponentSchema } from "@/__generated__";
import { formatBytes } from "@/utils";
import PcMetadataReview from "./PcMetadataReview.vue";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ components: PcComponentSchema[]; romId: number }>();
const emit = defineEmits<{ (event: "applied"): void }>();
const { t } = useI18n();

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
    <h3 class="pc-components__heading">{{ t("rom.pc-components") }}</h3>

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
          <PcMetadataReview
            v-if="component.kind === 'dlc'"
            :rom-id="romId"
            :component-id="component.id"
            @applied="emit('applied')"
          />
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
