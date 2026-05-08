<script setup lang="ts">
// FolderMappingTypeCell — editable Type cell (alias / variant / auto)
// for the folder mappings table. Pulled out of FolderMappingsSection
// for the same reason as FolderMappingPlatformCell: the RMenu activator
// slot anchors reliably only when it lives at this SFC root, not when
// nested inside RTable's `cell.type` slot scope.
import { RBtn, RMenu, RMenuItem, RMenuPanel, RTag } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";

defineOptions({ inheritAttrs: false });

type RowType = "alias" | "variant" | "auto" | null;

interface Row {
  fsSlug: string;
  slug?: string;
  displayName?: string;
  type: RowType;
}

interface Props {
  row: Row;
  canEdit: boolean;
}
const props = defineProps<Props>();

defineEmits<{
  (e: "select", type: "alias" | "variant"): void;
}>();

const { t } = useI18n();

type RTagTone = "neutral" | "brand" | "success" | "danger" | "warning" | "info";

const tone = computed<RTagTone>(() => {
  if (props.row.type === "alias") return "brand";
  if (props.row.type === "variant") return "info";
  return "success"; // auto
});

const label = computed(() => {
  if (props.row.type === "alias") return t("settings.folder-alias");
  if (props.row.type === "variant") return t("settings.platform-variant");
  return t("settings.auto-detected");
});

const isEditable = computed(
  () => props.canEdit && props.row.slug && props.row.type !== null,
);
</script>

<template>
  <RMenu v-if="isEditable" location="bottom">
    <template #activator="{ props: menuProps }">
      <RBtn
        v-bind="menuProps"
        variant="text"
        size="x-small"
        class="r-v2-fmtc__btn"
        append-icon="mdi-chevron-down"
      >
        <RTag :tone="tone" :text="label" size="x-small" />
      </RBtn>
    </template>
    <RMenuPanel width="200px">
      <RMenuItem
        :label="t('settings.folder-alias')"
        icon="mdi-label-variant"
        @click="$emit('select', 'alias')"
      />
      <RMenuItem
        :label="t('settings.platform-variant')"
        icon="mdi-source-branch"
        @click="$emit('select', 'variant')"
      />
    </RMenuPanel>
  </RMenu>
  <RTag v-else-if="row.type" :tone="tone" :text="label" size="x-small" />
</template>

<style scoped>
.r-v2-fmtc__btn {
  text-transform: none !important;
  letter-spacing: 0 !important;
}
.r-v2-fmtc__btn :deep(.v-btn__content) {
  gap: 6px;
}
</style>
