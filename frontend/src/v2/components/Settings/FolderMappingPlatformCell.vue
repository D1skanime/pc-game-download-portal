<script setup lang="ts">
// FolderMappingPlatformCell — editable Platform cell for the folder
// mappings table. Pulled out of FolderMappingsSection so the RMenu's
// activator slot lives at the SFC root (not nested inside RTable's
// `cell.platform` slot), which is what makes the activator's ref
// chain reach VMenu reliably; nested-slot scoping was leaving the
// menu without an anchor and silently swallowing the click.
import { RBtn, RMenu, RMenuItem, RMenuPanel } from "@v2/lib";
import { useI18n } from "vue-i18n";
import PlatformIcon from "@/components/common/Platform/PlatformIcon.vue";
import type { Platform } from "@/stores/platforms";

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
  supportedPlatforms: Platform[];
  canEdit: boolean;
}
defineProps<Props>();

defineEmits<{
  /** New platform slug (or undefined to clear the mapping). */
  (e: "select", slug: string | undefined): void;
}>();

const { t } = useI18n();
</script>

<template>
  <RMenu v-if="canEdit">
    <template #activator="{ props: menuProps }">
      <RBtn
        v-bind="menuProps"
        variant="text"
        size="small"
        class="r-v2-fmpc__btn"
        append-icon="mdi-chevron-down"
      >
        <PlatformIcon
          v-if="row.slug"
          :slug="row.slug"
          :size="20"
          class="r-v2-fmpc__icon"
        />
        <span v-if="row.slug">{{ row.displayName }}</span>
        <span v-else class="r-v2-fmpc__placeholder">—</span>
      </RBtn>
    </template>
    <RMenuPanel width="280px" max-height="320px">
      <RMenuItem
        v-for="platform in supportedPlatforms"
        :key="platform.slug"
        :label="platform.display_name"
        @click="$emit('select', platform.slug)"
      >
        <template #icon>
          <PlatformIcon :slug="platform.slug" :size="18" />
        </template>
      </RMenuItem>
      <RMenuItem
        v-if="row.slug && row.type !== 'auto'"
        icon="mdi-delete"
        variant="danger"
        :label="t('common.delete')"
        @click="$emit('select', undefined)"
      />
    </RMenuPanel>
  </RMenu>
  <span v-else class="r-v2-fmpc__readonly">
    <PlatformIcon
      v-if="row.slug"
      :slug="row.slug"
      :size="20"
      class="r-v2-fmpc__icon"
    />
    <span v-if="row.slug">{{ row.displayName }}</span>
    <span v-else class="r-v2-fmpc__placeholder">—</span>
  </span>
</template>

<style scoped>
.r-v2-fmpc__btn {
  text-transform: none !important;
  letter-spacing: 0 !important;
  font-weight: var(--r-font-weight-regular) !important;
  font-size: 13px !important;
  color: var(--r-color-fg) !important;
}
.r-v2-fmpc__btn :deep(.v-btn__content) {
  gap: 8px;
}
.r-v2-fmpc__icon {
  flex-shrink: 0;
}
.r-v2-fmpc__readonly {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--r-color-fg);
}
.r-v2-fmpc__placeholder {
  color: var(--r-color-fg-faint);
}
</style>
